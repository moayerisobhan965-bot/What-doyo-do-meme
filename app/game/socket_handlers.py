"""
Socket.io Handlers
Echtzeit-Kommunikation für das Spiel
"""
import json
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

from app.game.game_logic import game_logic
from app.game.redis_client import redis_client
from app.schemas import (
    Player, RoomState, Caption, Meme,
    RoundResult, GameOver
)


class ConnectionManager:
    """Verwaltet WebSocket-Verbindungen"""

    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, room_code: str, player_id: str, websocket: WebSocket):
        """Verbindet einen Client"""
        await websocket.accept()
        if room_code not in self.active_connections:
            self.active_connections[room_code] = {}
        self.active_connections[room_code][player_id] = websocket

    async def disconnect(self, room_code: str, player_id: str):
        """Trennt eine Verbindung"""
        if room_code in self.active_connections and player_id in self.active_connections[room_code]:
            await self.active_connections[room_code][player_id].close()
            del self.active_connections[room_code][player_id]

        # Raum löschen wenn leer
        if room_code in self.active_connections and not self.active_connections[room_code]:
            del self.active_connections[room_code]

    async def send_to_room(self, room_code: str, message: Dict[str, Any]):
        """Sendet Nachricht an alle im Raum"""
        if room_code in self.active_connections:
            for connection in self.active_connections[room_code].values():
                try:
                    await connection.send_json(message)
                except:
                    pass

    async def send_to_player(self, room_code: str, player_id: str, message: Dict[str, Any]):
        """Sendet Nachricht an einen spezifischen Spieler"""
        if room_code in self.active_connections and player_id in self.active_connections[room_code]:
            try:
                await self.active_connections[room_code][player_id].send_json(message)
            except:
                pass

    async def broadcast_to_all_except(self, room_code: str, exclude_id: str, message: Dict[str, Any]):
        """Sendet Nachricht an alle außer einem Spieler"""
        if room_code in self.active_connections:
            for player_id, connection in self.active_connections[room_code].items():
                if player_id != exclude_id:
                    try:
                        await connection.send_json(message)
                    except:
                        pass


manager = ConnectionManager()


async def handle_socket_events(websocket: WebSocket, room_code: str, player_id: str, user_data: Dict = None):
    """Verarbeitet Socket.io Events"""

    try:
        # Verbinden
        await manager.connect(room_code, player_id, websocket)

        # Nachricht empfangen
        while True:
            data = await websocket.receive_json()

            event = data.get("event")

            if event == "create_room":
                # Raum erstellen
                max_players = data.get("max_players", 10)
                host_name = user_data.get("username") if user_data else data.get("guest_name", "Gast")
                is_guest = user_data is None

                room = await game_logic.create_room(
                    room_code=room_code,
                    host_id=player_id,
                    host_name=host_name,
                    max_players=max_players,
                    avatar_url=user_data.get("avatar_url") if user_data else None
                )

                await manager.send_to_room(room_code, {
                    "event": "room_created",
                    "room": room
                })

            elif event == "join_room":
                # Raum beitreten
                guest_name = data.get("guest_name", "Gast")
                is_guest = user_data is None

                room = await game_logic.join_room(
                    room_code=room_code,
                    player_id=player_id,
                    player_name=guest_name,
                    is_guest=is_guest,
                    avatar_url=user_data.get("avatar_url") if user_data else None
                )

                await manager.send_to_room(room_code, {
                    "event": "room_joined",
                    "room": room
                })

                # Nachricht an den neuen Spieler
                await manager.send_to_player(room_code, player_id, {
                    "event": "joined_room",
                    "room": room
                })

            elif event == "start_game":
                # Spiel starten
                room = await game_logic.start_game(room_code)
                await manager.send_to_room(room_code, {
                    "event": "game_started",
                    "room": room
                })

            elif event == "submit_meme":
                # Meme einreichen
                meme_id = data.get("meme_id")
                room = await game_logic.submit_meme(room_code, player_id, meme_id)

                await manager.send_to_room(room_code, {
                    "event": "meme_submitted",
                    "room": room
                })

                # Nur aktuellen Spieler informieren
                await manager.send_to_player(room_code, player_id, {
                    "event": "turn_changed",
                    "current_player": room["players"][room["current_player_index"]]
                })

            elif event == "vote_meme":
                # Stimme abgeben
                meme_id = data.get("meme_id")
                room = await game_logic.vote_meme(room_code, player_id, meme_id)

                if room["state"] == "result":
                    # Ergebnis senden
                    round_result = {
                        "winner_id": room["winner_id"],
                        "winner_name": room["winner_name"],
                        "meme_id": room["winner_meme_id"],
                        "votes": room["round_result"]["votes"],
                        "vote_counts": room["round_result"]["vote_counts"],
                    }

                    await manager.send_to_room(room_code, {
                        "event": "round_result",
                        "round_result": round_result,
                        "room": room
                    })

                    # Game Over?
                    if room["game_over"]:
                        await manager.send_to_room(room_code, {
                            "event": "game_over",
                            "game_over": room
                        })

            elif event == "leave_room":
                # Raum verlassen
                room = await game_logic.leave_room(room_code, player_id)

                if room:
                    await manager.send_to_room(room_code, {
                        "event": "player_left",
                        "player_id": player_id,
                        "room": room
                    })
                else:
                    # Raum gelöscht
                    await manager.send_to_player(room_code, player_id, {
                        "event": "room_deleted"
                    })

            elif event == "get_room_state":
                # Room-Status abfragen
                room = game_logic.get_room_state(room_code)
                await manager.send_to_player(room_code, player_id, {
                    "event": "room_state",
                    "room": room
                })

    except WebSocketDisconnect:
        # Verbindung getrennt
        await game_logic.leave_room(room_code, player_id)
        await manager.disconnect(room_code, player_id)
