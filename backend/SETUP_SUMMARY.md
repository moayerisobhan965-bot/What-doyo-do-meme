# 🎉 Was Meme Backend - Vollständige Installation

## 📦 Was wurde erstellt?

Ein komplettes, production-ready Backend für das Multiplayer-Meme-Spiel "What Meme"!

### ✅ Erstellte Dateien & Struktur:

```
what-meme-backend/
├── app/
│   ├── main.py                    # FastAPI App + REST API + Socket.io
│   ├── config.py                  # Konfiguration
│   ├── database.py                # DB Connection (PostgreSQL)
│   ├── models.py                  # SQLAlchemy Models
│   ├── schemas.py                 # Pydantic Schemas
│   ├── auth/
│   │   ├── password.py            # bcrypt Hashing
│   │   └── jwt.py                 # JWT Token Management
│   ├── email/
│   │   ├── service.py             # E-Mail Versand (Resend)
│   │   └── templates/
│   │       ├── verify_email.html  # Verifizierungs-Template
│   │       └── reset_password.html # Reset-Template
│   ├── game/
│   │   ├── game_logic.py          # Spiel-Logik (N Spieler)
│   │   ├── redis_client.py        # Redis Client
│   │   └── socket_handlers.py     # Socket.io Handlers
│   └── static/
│       └── memes/                 # Speicherort für Memes
├── scripts/
│   ├── download_memes.py          # Meme Downloader
│   └── setup.sh                   # Auto-Setup Script
├── data/
│   └── captions.py                # 500 lustige Textkarten
├── migrations/
│   ├── env.py                     # Alembic Environment
│   └── script.py.mako             # Migration Template
├── tests/
│   ├── test_api.py                # API Tests
│   └── __init__.py
├── nginx/
│   └── nginx.conf                 # Reverse Proxy + SSL
├── docker-compose.yml             # Alle Services
├── Dockerfile                     # App Container
├── requirements.txt               # Python Dependencies
├── .env.example                   # Konfigurations-Template
├── .gitignore                     # Git Ignore
├── alembic.ini                    # Alembic Config
├── README.md                      # Doku
└── SETUP_SUMMARY.md               # Diese Datei
```

---

## 🚀 Schnellstart

### Auf deinem Server (Ubuntu 22.04):

```bash
# 1. Repository klonen
cd ~
git clone https://github.com/your-username/whatmeme-backend.git
cd whatmeme-backend

# 2. Setup Script ausführen
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. .env konfigurieren
nano .env

# 4. SSL einrichten
certbot --nginx -d dein-domain.de -d www.dein-domain.de

# 5. Docker Compose neu starten
docker compose restart
```

---

## ⚙️ WICHTIGE KONFIGURATION

### 1. JWT Secret Key generieren

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Ergebnis kopieren und in `.env` einfügen:**

```env
JWT_SECRET_KEY=DEIN_GENERIERTER_STRING_HIER
```

### 2. SMTP Einstellungen

**Resend (Empfohlen - kostenlos):**
1. Registriere dich auf [resend.com](https://resend.com)
2. Erstelle API Key
3. Kopiere Key und füge in `.env` ein:

```env
SMTP_PASSWORD=RESEND_API_KEY_HIER
SMTP_FROM=noreply@dein-domain.de
```

**Brevo (Alternative):**
1. Registriere dich auf [brevo.com](https://www.brevo.com)
2. Erstelle API Key
3. Füge ein:

```env
SMTP_PASSWORD=BREVO_API_KEY_HIER
SMTP_FROM=noreply@dein-domain.de
```

### 3. Domain einrichten

**DNS Records:**
```
A  whatmeme.de       dein-server-ip
A  www.whatmeme.de   dein-server-ip
```

**SSL einrichten:**
```bash
certbot --nginx -d whatmeme.de -d www.whatmeme.de
```

---

## 📊 SERVICES & PORTS

| Service | Port | Beschreibung |
|---------|------|-------------|
| App | 8000 | FastAPI Application |
| PostgreSQL | 5432 | Datenbank |
| Redis | 6379 | Cache + Pub/Sub |
| nginx | 80/443 | Reverse Proxy + SSL |

**Nur öffnen:** 80, 443, 22 (SSH)

---

## 🧪 Testen

### Health Check
```bash
curl http://localhost:8000/health
```

### Swagger Docs
```
http://localhost:8000/docs
```

### API Endpoints

**Auth:**
- `POST /api/auth/register` - Registrierung
- `POST /api/auth/login` - Login
- `POST /api/auth/verify-email` - Verifizieren
- `POST /api/auth/forgot-password` - Passwort vergessen
- `POST /api/auth/reset-password` - Passwort zurücksetzen

**User:**
- `GET /api/users/me` - Eigene Daten
- `PATCH /api/users/me` - Profil ändern
- `GET /api/users/me/stats` - Statistiken

**Game:**
- `GET /api/memes` - Alle Memes
- `GET /api/captions` - Alle Textkarten
- `POST /api/rooms` - Raum erstellen

---

## 🐛 Troubleshooting

### Container starten nicht?
```bash
docker compose logs -f app
```

### Datenbank-Verbindung fehlgeschlagen?
```bash
docker compose logs postgres
docker compose exec postgres psql -U postgres -d whatmeme
```

### SSL-Probleme?
```bash
certbot --nginx -d dein-domain.de -d www.dein-domain.de --force-renewal
```

### Port schon in Verwendung?
```bash
netstat -tulpn | grep 8000
fuser -k 8000/tcp
```

---

## 📈 Skalierung

### Auf 10k Nutzer skalieren:

1. **Mehr App-Server:**
   - 3-5 Server mit docker-compose
   - Load Balancer (Nginx/HAProxy)

2. **Datenbank-Scaling:**
   - PostgreSQL Read Replicas
   - Connection Pooling

3. **Redis-Scaling:**
   - Redis Cluster Mode

4. **Monitoring:**
   - Prometheus + Grafana
   - ELK Stack

---

## 🎮 Spiel-Features

### Was funktioniert schon?

✅ **Auth-System:**
- Registrierung
- Login
- E-Mail-Verifizierung
- Passwort-Reset
- JWT-Token
- Gast-Modus

✅ **Spiel-Logik:**
- Räume erstellen/beitreten
- 2-10+ Spieler
- Socket.io Echtzeit
- Computer zieht Textkarten
- Spieler wählen Memes
- Alle stimmen ab
- Gewinner bekommt Punkte
- 5 Punkte = Sieg
- Tracking gespielter Memes

✅ **Tech-Stack:**
- FastAPI (Python 3.11+)
- PostgreSQL (Nutzer-DB)
- Redis (Room-States)
- Socket.io (Echtzeit)
- Docker
- nginx + SSL

---

## 📚 Dokumentation

- **README.md** - Komplette Installation
- **.env.example** - Konfigurations-Template
- **/docs** - Swagger API Docs (nach Start)

---

## 🎉 Fertig!

Das Backend ist jetzt bereit!

**Nächste Schritte:**
1. Server einrichten (Hetzner VPS ~5€/Monat)
2. Domain kaufen (Namecheap/INWX)
3. DNS einrichten
4. SSL mit Certbot einrichten
5. .env konfigurieren
6. Docker Compose starten
7. Meme-Download starten
8. Testen!

**Viel Spaß beim Spielen!** 🚀
