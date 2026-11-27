"""E2E-Test: Gast-Modus - 3 Gast-Spieler spielen ein komplettes Spiel gegen das Backend.

Ausführen (Backend muss laufen):
    WM_API_BASE=http://localhost:8000 python3 tests/test_guest_e2e.py

Ohne WM_API_BASE wird http://localhost:8000 verwendet.
"""
import asyncio
import json
import os
import random
import sys

import aiohttp

BASE = os.getenv("WM_API_BASE", "http://localhost:8000").rstrip("/")
WS_BASE = BASE.replace("https://", "wss://").replace("http://", "ws://")
ROUNDS_LIMIT = 2

results = {"ok": [], "fail": []}


def check(name: str, cond: bool, extra: str = ""):
    if cond:
        results["ok"].append(name)
        print(f"  ✅ {name} {extra}")
    else:
        results["fail"].append(name)
        print(f"  ❌ {name} {extra}")


async def guest_login(session: aiohttp.ClientSession, idx: int) -> dict:
    async with session.post(f"{BASE}/api/auth/guest", json={}) as r:
        data = await r.json()
        assert r.status == 200, f"Gast-Login {idx} fehlgeschlagen: {r.status} {data}"
        return data


async def ws_recv_until(ws, events: set, timeout: float = 20.0) -> dict:
    """Liest Nachrichten bis eines der gewünschten Events kommt."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        remaining = deadline - loop.time()
        try:
            raw = await asyncio.wait_for(ws.receive(), timeout=remaining)
        except asyncio.TimeoutError:
            return {"event": "__timeout__"}
        if raw.type == aiohttp.WSMsgType.TEXT:
            msg = json.loads(raw.data)
            if msg.get("event") in events:
                return msg
    return {"event": "__timeout__"}


async def player_task(name: str, code: str, pid: str, token: str, role: str,
                      log, players_expected: int) -> dict:
    """Ein Gast-Spieler: WS verbinden, beitreten, dann automatisierte Spielzüge."""
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(
            f"{WS_BASE}/ws/{code}/{pid}?token={token}", timeout=10
        ) as ws:
            await ws.send_json({"event": "join_room"})
            msg = await ws_recv_until(ws, {"room_joined", "room_state", "error"})
            log(f"{name} join: {msg.get('event')}")
            if msg.get("event") == "error":
                return {"name": name, "joined": False, "error": msg.get("message")}

            if role == "host":
                # Warten bis alle Spieler im Raum sind, dann starten
                log(f"{name} wartet auf {players_expected} Spieler...")
                joined_ids = {str(p["id"]) for p in msg.get("room", {}).get("players", [])}
                while len(joined_ids) < players_expected:
                    m = await ws_recv_until(ws, {
                        "room_joined", "room_state", "player_left", "error",
                        "round_started", "game_started", "__timeout__",
                    }, timeout=30)
                    if m.get("event") == "__timeout__":
                        return {"name": name, "joined": True,
                                "error": "timeout beim Warten auf Spieler"}
                    if m.get("event") == "error":
                        return {"name": name, "joined": True, "error": m.get("message")}
                    room = m.get("room", {})
                    joined_ids = {str(p["id"]) for p in room.get("players", [])}
                    log(f"{name} sieht {len(joined_ids)}/{players_expected} Spieler")
                await ws.send_json({"event": "start_game"})
                log(f"{name} startet das Spiel!")

            played = 0
            submitted = 0
            voted = 0
            last_event = ""
            while True:
                msg = await ws_recv_until(ws, {
                    "round_started", "voting_started", "round_result",
                    "game_over", "game_started", "error", "__timeout__",
                }, timeout=30)
                ev = msg.get("event")
                if ev == "__timeout__":
                    log(f"{name} TIMEOUT nach {last_event}")
                    return {"name": name, "joined": True, "error": "timeout",
                            "played": played, "submitted": submitted, "voted": voted}
                if ev == "error":
                    log(f"{name} error: {msg.get('message')}")
                    return {"name": name, "joined": True, "error": msg.get("message")}
                if ev == "game_over":
                    log(f"{name} game_over, score={msg.get('scores', {}).get(pid)}")
                    return {"name": name, "joined": True, "error": None,
                            "played": played, "submitted": submitted, "voted": voted,
                            "winner": msg.get("winner_id"), "scores": msg.get("scores", {})}
                if ev == "round_started":
                    played += 1
                    last_event = ev
                    room = msg.get("room", {})
                    judge_id = str(msg.get("judge_id", ""))
                    memes = msg.get("memes", [])
                    if judge_id != pid and memes:
                        mid = random.choice(memes)["id"]
                        await ws.send_json({"event": "submit_meme", "meme_id": mid})
                        submitted += 1
                        log(f"{name} Runde {played}: Meme {mid} eingereicht (Richter={judge_id})")
                elif ev == "voting_started":
                    last_event = ev
                    subs = msg.get("submissions", [])
                    targets = [s["player_id"] for s in subs if str(s["player_id"]) != pid]
                    if targets:
                        t = random.choice(targets)
                        await ws.send_json({"event": "vote", "target_player_id": str(t)})
                        voted += 1
                        log(f"{name} stimmt für {t}")
                elif ev == "round_result":
                    last_event = ev
                    log(f"{name} Runde {msg.get('round')}: Gewinner {msg.get('winner_name')}")


async def main():
    print("=== E2E Gast-Modus Test (3 Gäste, 2 Runden) ===")
    print(f"Backend: {BASE}\n")

    def log(s):
        print(f"  [{s}]")

    async with aiohttp.ClientSession() as session:
        print("\n1) Gast-Login für 3 Spieler...")
        users = []
        for i in range(3):
            data = await guest_login(session, i + 1)
            u = data["user"]
            users.append({"token": data["access_token"], "id": str(u["id"]),
                          "name": u["username"]})
            check(f"Gast-Login {i+1} ({u['username']})", data.get("access_token") != "")
        check("Alle 3 Gast-Konten erstellt", len(users) == 3)
        check("Gast-Konten sind verifiziert", all(u["name"].startswith("Gast") for u in users))

        print("\n2) Host (Gast) erstellt Raum...")
        headers = {"Authorization": f"Bearer {users[0]['token']}"}
        async with session.post(f"{BASE}/api/rooms",
                                json={"max_players": 4, "rounds_limit": ROUNDS_LIMIT},
                                headers=headers) as r:
            room = await r.json()
            check("Raum erstellen (HTTP 200)", r.status == 200, str(r.status))
            code = room.get("code", "")
            check("4-stelliger Code vorhanden", len(code) == 4, code)
            check("Host ist als Gast markiert",
                  room.get("players", [{}])[0].get("is_guest") is True)

        print(f"\n3) 3 Gast-Spieler verbinden sich mit Raum {code} ...")
        tasks = [
            player_task("A (Host)", code, users[0]["id"], users[0]["token"], "host", log, 3),
            player_task("B", code, users[1]["id"], users[1]["token"], "player", log, 3),
            player_task("C", code, users[2]["id"], users[2]["token"], "player", log, 3),
        ]
        outcomes = await asyncio.gather(*tasks)

        print("\n=== ERGEBNIS ===")
        for o in outcomes:
            check(f"{o['name']}: Raum beigetreten", o.get("joined", False))
            check(f"{o['name']}: keine Fehler", o.get("error") is None,
                  f"(error={o.get('error')})")
            if o.get("error") is None:
                check(f"{o['name']}: 2 Runden gespielt", o.get("played", 0) == ROUNDS_LIMIT,
                      f"({o.get('played')})")
                check(f"{o['name']}: Memes eingereicht", o.get("submitted", 0) >= 1)
                check(f"{o['name']}: abgestimmt", o.get("voted", 0) >= 1)

        scores = outcomes[0].get("scores", {})
        check("Game over mit Punktestand", len(scores) == 3, str(scores))

        print(f"\n✅ Erfolgreich: {len(results['ok'])}  ❌ Fehlgeschlagen: {len(results['fail'])}")
        if results["fail"]:
            print("FEHLER:", ", ".join(results["fail"]))
            sys.exit(1)
        print("\n🎉 GAST-MODUS FUNKTIONIERT KOMPLETT MIT DEM BACKEND!")


if __name__ == "__main__":
    asyncio.run(main())
