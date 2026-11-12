"""
Game Logic
Spiel-Logik für Multiple Player
"""
import random
from typing import Dict, List, Optional, Tuple
from enum import Enum

from app.game.redis_client import redis_client
from app.schemas import (
    Player, RoomState, Caption, Meme,
    RoundResult, GameOver,
    GameState as SchemaState
)


class GameState(Enum):
    """Spiel-Zustände"""
    LOBBY = "lobby"
    PLAYING = "playing"
    VOTING = "voting"
    RESULT = "result"
    GAME_OVER = "game_over"


class GameLogic:
    """Game Logic Manager"""

    # Spiel-Config
    MAX_CAPTIONS_PER_ROUND = 5
    WIN_SCORE = 5

    def __init__(self):
        self.current_room: Optional[Dict] = None

    async def create_room(
        self,
        room_code: str,
        host_id: str,
        host_name: str,
        max_players: int = 10,
        avatar_url: Optional[str] = None
    ) -> Dict:
        """Erstellt einen neuen Raum"""
        self.current_room = {
            "code": room_code,
            "state": GameState.LOBBY.value,
            "host_id": host_id,
            "players": [
                Player(
                    id=host_id,
                    name=host_name,
                    is_host=True,
                    is_guest=False,
                    is_ready=True,
                    avatar_url=avatar_url,
                    score=0
                )
            ],
            "current_round": 0,
            "current_player_index": 0,
            "drawn_caption": None,
            "submissions": {},
            "votes": {},
            "winner_id": None,
            "game_over": False,
            "winner_score": None,
        }

        # Speichern in Redis
        await redis_client.set_room_state(room_code, self.current_room, ttl=86400)  # 24h

        return self.current_room

    async def join_room(
        self,
        room_code: str,
        player_id: str,
        player_name: str,
        is_guest: bool = False,
        avatar_url: Optional[str] = None
    ) -> Dict:
        """Spieler tritt einem Raum bei"""
        room = await redis_client.get_room_state(room_code)
        if not room:
            raise ValueError("Raum nicht gefunden")

        # Spieler hinzufügen
        new_player = Player(
            id=player_id,
            name=player_name,
            is_host=False,
            is_guest=is_guest,
            is_ready=True,
            avatar_url=avatar_url,
            score=0
        )

        room["players"].append(new_player)
        room["state"] = GameState.LOBBY.value

        # Speichern
        await redis_client.set_room_state(room_code, room)

        return room

    async def leave_room(
        self,
        room_code: str,
        player_id: str
    ) -> Optional[Dict]:
        """Spieler verlässt den Raum"""
        room = await redis_client.get_room_state(room_code)
        if not room:
            return None

        # Spieler entfernen
        room["players"] = [p for p in room["players"] if p.id != player_id]

        # Host wechseln, wenn der alte Host geht
        if room["host_id"] == player_id and room["players"]:
            room["host_id"] = room["players"][0].id
            room["players"][0].is_host = True

        # Raum löschen, wenn leer
        if not room["players"]:
            await redis_client.delete_room_state(room_code)
            return None

        # Speichern
        await redis_client.set_room_state(room_code, room)

        return room

    async def start_game(self, room_code: str) -> Dict:
        """Startet das Spiel"""
        room = await redis_client.get_room_state(room_code)
        if not room:
            raise ValueError("Raum nicht gefunden")

        if len(room["players"]) < 2:
            raise ValueError("Mindestens 2 Spieler erforderlich")

        # Spiel starten
        room["state"] = GameState.PLAYING.value
        room["current_round"] = 1
        room["current_player_index"] = 0

        # Speichern
        await redis_client.set_room_state(room_code, room)

        return room

    def draw_caption(self, captions: List[Caption]) -> str:
        """Zieht eine zufällige Textkarte"""
        return random.choice(captions).text

    def get_next_player(self, room: Dict) -> Optional[str]:
        """Gibt den nächsten Spieler zurück"""
        if not room["players"]:
            return None

        # Starte bei aktuellem Spieler + 1
        next_idx = (room["current_player_index"] + 1) % len(room["players"])
        return room["players"][next_idx].id

    def get_player_by_id(self, room: Dict, player_id: str) -> Optional[Player]:
        """Gibt Spieler anhand ID zurück"""
        for player in room["players"]:
            if player.id == player_id:
                return player
        return None

    def get_player_index(self, room: Dict, player_id: str) -> Optional[int]:
        """Gibt den Index eines Spielers zurück"""
        for idx, player in enumerate(room["players"]):
            if player.id == player_id:
                return idx
        return None

    async def submit_meme(
        self,
        room_code: str,
        player_id: str,
        meme_id: int
    ) -> Dict:
        """Spieler reicht ein Meme ein"""
        room = await redis_client.get_room_state(room_code)
        if not room:
            raise ValueError("Raum nicht gefunden")

        # Prüfen ob Spieler an der Reihe ist
        current_player = room["players"][room["current_player_index"]]
        if current_player.id != player_id:
            raise ValueError("Nicht an der Reihe")

        # Meme speichern
        room["submissions"][player_id] = meme_id

        # Prüfen ob alle gesubmitted haben
        if len(room["submissions"]) >= len(room["players"]):
            # Alle haben gesubmitted -> Voting starten
            room["state"] = GameState.VOTING.value
            room["votes"] = {p.id: 0 for p in room["players"]}
        else:
            # Nächster Spieler
            next_player_id = self.get_next_player(room)
            if next_player_id:
                room["current_player_index"] = self.get_player_index(room, next_player_id)

        # Speichern
        await redis_client.set_room_state(room_code, room)

        return room

    async def vote_meme(
        self,
        room_code: str,
        voter_id: str,
        meme_id: int
    ) -> Dict:
        """Spieler stimmt ab"""
        room = await redis_client.get_room_state(room_code)
        if not room:
            raise ValueError("Raum nicht gefunden")

        if room["state"] != GameState.VOTING.value:
            raise ValueError("Nicht im Voting-Modus")

        # Stimme speichern
        room["votes"][voter_id] = meme_id

        # Prüfen ob alle abgestimmt haben
        if len(room["votes"]) >= len(room["players"]):
            # Ergebnis berechnen
            await self._calculate_round_result(room_code)
        else:
            # Speichern (ohne Ergebnis)
            await redis_client.set_room_state(room_code, room)

        return room

    async def _calculate_round_result(self, room_code: str):
        """Berechnet das Ergebnis einer Runde"""
        room = await redis_client.get_room_state(room_code)
        if not room:
            raise ValueError("Raum nicht gefunden")

        # Stimmen zählen
        vote_counts: Dict[int, int] = {}
        for vote in room["votes"].values():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1

        # Gewinner finden (meiste Stimmen)
        if vote_counts:
            max_votes = max(vote_counts.values())
            winners = [meme_id for meme_id, count in vote_counts.items() if count == max_votes]
            winner_meme_id = random.choice(winners)
        else:
            # Keine Stimmen -> zufälliger Gewinner
            meme_ids = list(room["submissions"].values())
            winner_meme_id = random.choice(meme_ids) if meme_ids else None

        # Gewinner Spieler finden
        winner_player_id = None
        winner_player_name = "Unbekannt"
        if winner_meme_id:
            for player_id, meme_submitted in room["submissions"].items():
                if meme_submitted == winner_meme_id:
                    winner_player_id = player_id
                    player = self.get_player_by_id(room, player_id)
                    if player:
                        winner_player_name = player.name
                    break

        # Punkte vergeben
        if winner_player_id:
            for player in room["players"]:
                if player.id == winner_player_id:
                    player.score += 1

        # Runde als Ergebnis speichern
        room["state"] = GameState.RESULT.value
        room["winner_id"] = winner_player_id
        room["winner_name"] = winner_player_name
        room["winner_meme_id"] = winner_meme_id
        room["round_result"] = {
            "votes": room["votes"],
            "vote_counts": vote_counts,
            "winner_id": winner_player_id,
            "winner_name": winner_player_name,
        }

        # Prüfen ob jemand gewonnen hat (5 Punkte)
        game_over = False
        winner_score = None
        for player in room["players"]:
            if player.score >= self.WIN_SCORE:
                game_over = True
                winner_score = player.score
                room["game_over"] = True
                room["winner_score"] = winner_score
                break

        # Speichern
        await redis_client.set_room_state(room_code, room)

        # Wenn Game Over, Raum löschen
        if game_over:
            await redis_client.delete_room_state(room_code)
        else:
            # Nächste Runde vorbereiten
            room["current_round"] += 1
            room["current_player_index"] = 0
            room["submissions"] = {}
            room["votes"] = {}
            room["drawn_caption"] = None
            room["state"] = GameState.PLAYING.value
            await redis_client.set_room_state(room_code, room)

    async def check_game_over(self, room_code: str) -> bool:
        """Prüft ob Spiel vorbei ist"""
        room = await redis_client.get_room_state(room_code)
        if not room:
            return True
        return room["game_over"]

    def get_room_state(self, room_code: str) -> Optional[Dict]:
        """Lädt Room-Status"""
        return redis_client.get_room_state(room_code)

    def get_players(self, room: Dict) -> List[Player]:
        """Gibt Spieler-Liste zurück"""
        return room.get("players", [])

    def get_current_player(self, room: Dict) -> Optional[Player]:
        """Gibt aktuellen Spieler zurück"""
        idx = room.get("current_player_index", 0)
        players = self.get_players(room)
        return players[idx] if idx < len(players) else None


# Singleton Instance
game_logic = GameLogic()
