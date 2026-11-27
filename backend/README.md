# 🎮 What Meme - Backend

Multiplayer-Meme-Spiel Backend - **alles in einer Datei**: `backend.py`
(FastAPI + PostgreSQL + Redis + WebSockets)

## ✨ Features

### 🔐 Nutzer-Konten
- ✅ Registrierung mit E-Mail + Passwort
- ✅ E-Mail-Verifizierung mit 6-stelligem Code (wie GitHub/Google)
- ✅ Login mit JWT-Token
- ✅ Passwort-Reset per E-Mail-Code
- ✅ Profil + Statistiken (Spiele, Siege, Siegquote)
- ✅ Passwort-Hashing mit bcrypt
- ✅ **Gast-Modus**: `POST /api/auth/guest` erstellt sofort ein spielbereites Konto
  (`GastXXXXXX@guest.local`, verifiziert, kein Passwort nötig)

### 🎮 Spiel-Features (kompletter Spielfluss)
- ✅ Räume erstellen/beitreten (4-stelliger Code)
- ✅ 2-10 Spieler pro Raum
- ✅ Echtzeit-Kommunikation (WebSockets)
- ✅ Runden: Richter zieht Caption → Spieler wählen Meme → Voting → Punkte
- ✅ 5 Punkte = Sieg (konfigurierbar über `WIN_SCORE`)
- ✅ Automatischer Rundenfortschritt
- ✅ Spielhistorie wird gespeichert
- ✅ Meme-Bilder werden **vom Backend selbst generiert** (kein externer Dienst!)

### 🛠️ Tech-Stack
- ✅ FastAPI (Python 3.11+)
- ✅ PostgreSQL (Nutzer-DB, asyncpg)
- ✅ Redis (Raum-States)
- ✅ WebSockets (FastAPI nativ, kein Socket.io)
- ✅ Docker / docker-compose
- ✅ nginx (Reverse Proxy + SSL, optional)

## 🚀 Schnellstart

```bash
# 1. Abhängigkeiten (oder Docker)
pip install -r requirements.txt

# 2. PostgreSQL + Redis starten
docker compose up -d postgres redis

# 3. Backend starten
DATABASE_URL="postgresql+asyncpg://postgres:postgrespassword@localhost:5432/whatmeme" \
REDIS_URL="redis://localhost:6379/0" \
JWT_SECRET_KEY="dein-langer-random-string" \
SMTP_PASSWORD="dein_resend_api_key" \
python3 -m uvicorn backend:app --host 0.0.0.0 --port 8000
```

Oder komplett mit Docker: `docker compose up -d` (Port 80/443 über nginx).

## ⚙️ Konfiguration (Umgebungsvariablen)

| Variable | Beschreibung | Standard |
|---|---|---|
| `DATABASE_URL` | PostgreSQL-URL | `postgresql+asyncpg://postgres:postgrespassword@localhost:5432/whatmeme` |
| `REDIS_URL` | Redis-URL | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | JWT-Geheimnis | `change_this...` (ändern!) |
| `SMTP_PASSWORD` | Resend API-Key | leer = Entwicklungsmodus (Codes ins Log) |
| `SMTP_FROM` | Absender-E-Mail | `noreply@whatmeme.de` |
| `WIN_SCORE` | Punkte zum Sieg | `5` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token-Gültigkeit | `720` |
| `DEV_CODE_RETURN` | `1` = Codes in API-Antwort (nur Tests!) | `0` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client-ID | leer = Mock-Modus |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client-Secret | leer = Mock-Modus |

> ⚠️ Ohne `SMTP_PASSWORD` werden E-Mail-Codes nur ins Server-Log geschrieben
> (Entwicklungsmodus). Mit Resend-Key werden echte E-Mails versendet.

## 🔌 API

### REST
```
GET  /health
POST /api/auth/register        {email, username, password}
POST /api/auth/login           {email, password}
POST /api/auth/guest           {} → sofort spielbereites Gast-Konto (Version 3)
POST /api/auth/verify-email    {token}
POST /api/auth/forgot-password {email}
POST /api/auth/reset-password  {token, new_password}
GET  /api/auth/google/url?port=8123      Google-Login starten
POST /api/auth/google/callback  {code, state, port}
GET  /api/users/me             (Bearer-Token)
GET  /api/users/me/stats       (Bearer-Token)
POST /api/rooms                {max_players: 2-10, rounds_limit: 0|5|10|20} → 4-stelliger Code
GET  /api/rooms/{code}
GET  /api/memes                Meme-Liste (mit Namen)
GET  /api/captions             Textkarten
GET  /meme-images/{id}.png     Meme-Bilder (generiert)
```

### 🔵 Google-Login (Ablauf)

1. Client ruft `GET /api/auth/google/url?port=8123` → bekommt URL + State
2. Client startet lokalen Mini-Server auf `127.0.0.1:8123` und öffnet die URL im Browser
3. Google leitet den Browser auf `http://127.0.0.1:8123/?code=...&state=...` um
4. Client fängt den Redirect ab und schickt `POST /api/auth/google/callback`
5. Backend tauscht den Code gegen Google-Tokens (Server-seitig, sicher),
   verifiziert das ID-Token mit Googles Zertifikaten → Login oder Konto-Erstellung

Ohne `GOOGLE_CLIENT_ID/SECRET` läuft der **Mock-Modus** (der "Code" = E-Mail, nur für Tests).

### WebSocket: `/ws/{room_code}/{player_id}?token=JWT`

Client → Server:
```json
{"event": "join_room"}
{"event": "leave_room"}
{"event": "start_game"}                        (nur Host)
{"event": "submit_meme", "meme_id": 42}
{"event": "vote", "target_player_id": "7"}
{"event": "next_round"}                        (Ergebnis überspringen)
```

Server → Client:
```json
{"event": "room_state", "room": {...}}
{"event": "room_joined", "room": {...}}
{"event": "player_left", "player_id": "...", "room": {...}}
{"event": "game_started", "room": {...}}
{"event": "round_started", "round": 1, "caption": "...", "memes": [...], "judge_id": "...", "room": {...}}
{"event": "voting_started", "submissions": [...], "room": {...}}
{"event": "round_result", "winner_id": "...", "winner_name": "...", "scores": {...}, "room": {...}}
{"event": "game_over", "winner_id": "...", "winner_name": "...", "scores": {...}, "room": {...}}
{"event": "error", "message": "..."}
```

## 🧪 Tests

```bash
# Backend läuft auf Port 8001 (Testmodus):
DATABASE_URL="...localhost:5432..." REDIS_URL="redis://localhost:6379/0" \
WIN_SCORE=2 DEV_CODE_RETURN=1 python3 -m uvicorn backend:app --port 8001

# Godot E2E-Test (im godot-client Ordner, inkl. Gast-Login):
WM_API_BASE=http://localhost:8001 godot --headless -s res://tests/test_e2e.gd

# Gast-Modus E2E-Test (3 Gäste spielen ein komplettes Spiel):
WM_API_BASE=http://localhost:8001 python3 tests/test_guest_e2e.py
```

Der E2E-Test spielt ein komplettes Spiel mit 3 Spielern durch
(Registrierung → Verifizierung → Login → Gast-Login → Raum → Runden → Spielende).

## 🎮 Spielablauf (Server-Logik)

1. **Lobby**: Host erstellt Raum (REST, mit `max_players` 2-10 und `rounds_limit`)
2. **Runde**: Richter rotiert, zieht zufällige Caption, 6 zufällige Memes
3. **Einsendung**: Alle außer Richter wählen ein Meme
4. **Voting**: Alle stimmen ab (nicht für sich selbst)
5. **Ergebnis**: Sieger bekommt 1 Punkt → nächste Runde nach 6s
6. **Spielende**:
   - `rounds_limit > 0`: nach N Runden gewinnt die höchste Punktzahl
   - `rounds_limit = 0` (unbegrenzt): der erste mit `WIN_SCORE` (5) Punkten gewinnt
7. **Game-Over**: Sieger + Endstand + Spielhistorie wird gespeichert

> ⚠️ Wichtig: Alle Raum-Änderungen laufen über per-Raum-`asyncio.Lock`s
> (verhindert Lost-Update-Races bei gleichzeitigem Beitreten).
