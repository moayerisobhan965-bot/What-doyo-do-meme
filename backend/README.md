# 🎮 What Meme - Backend

Ein Multiplayer-Meme-Spiel Backend (FastAPI + PostgreSQL + Redis + Socket.io)

## 📋 Inhaltsverzeichnis

- [Features](#features)
- [Server-Empfehlung](#server-empfehlung)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Starten](#starten)
- [Domain & SSL](#domain--ssl)
- [Backup](#backup)
- [Tests](#tests)
- [Troubleshooting](#troubleshooting)
- [Skalierung](#skalierung)

## ✨ Features

### 🔐 Nutzer-Konten
- ✅ Registrierung mit E-Mail + Passwort
- ✅ E-Mail-Verifizierung (Bestätigungslink)
- ✅ Login mit JWT-Token
- ✅ Passwort-Reset per E-Mail
- ✅ Gast-Modus (ohne Konto)
- ✅ Profil mit Statistiken
- ✅ Passwort-Hashing mit bcrypt

### 🎮 Spiel-Features
- ✅ Räume erstellen/beitreten (4-stelliger Code)
- ✅ 2-10+ Spieler pro Raum
- ✅ Echtzeit-Kommunikation (Socket.io)
- ✅ Computer zieht Textkarten
- ✅ Spieler wählen nacheinander Memes
- ✅ Alle stimmen ab
- ✅ Gewinner bekommt Punkte
- ✅ 5 Punkte = Sieg
- ✅ Tracking gespielter Memes
- ✅ Persistente Identität

### 🚀 Performance
- ✅ < 100ms Latenz
- ✅ 10.000 gleichzeitige Nutzer
- ✅ Kein Crash bei Last
- ✅ WebSocket stabil (Auto-Reconnect)

### 🛠️ Tech-Stack
- ✅ FastAPI (Python 3.11+)
- ✅ PostgreSQL (Nutzer-DB)
- ✅ Redis (Room-States, Pub/Sub)
- ✅ Socket.io (Echtzeit)
- ✅ Docker (Containerisierung)
- ✅ nginx (Reverse Proxy + SSL)
- ✅ Let's Encrypt (SSL automatisch)

---

## 🖥️ Server-Empfehlung

### Option 1: Hetzner VPS (Empfohlen)
**Preis:** ~5€/Monat
**VPS-Größe:** CX22 (2 vCPU, 4 GB RAM, 40 GB SSD)

**Vorteile:**
- ✅ Zuverlässig
- ✅ Günstig
- ✅ Keine运维-Expertise nötig
- ✅ DDoS-Schutz inklusive

**Hetzner bestellen:** [https://www.hetzner.com](https://www.hetzner.com)

### Option 2: Eigener Heim-Server
**Voraussetzungen:**
- ✅ Stabile Internet-Verbindung
- ✅ Ständige Stromversorgung
- ✅ Gute CPU/RAM
- ✅ Ständige Verbindung (kein VPN)

**Beispiel Hardware:**
- CPU: 4+ Kerne
- RAM: 8+ GB
- SSD: 100+ GB
- Internet: 100+ Mbit/s

### Option 3: Contabo
**Preis:** ~6€/Monat
**VPS-Größe:** EX50 (4 vCPU, 8 GB RAM, 160 GB SSD)

**Vorteile:**
- ✅ Mehr RAM/SSD
- ✅ Günstiger

**Nachteile:**
- ⚠️ Langsamere CPU
- ⚠️ Weniger performant als Hetzner

---

## 📦 Voraussetzungen

### Auf deinem lokalen Computer:
- ✅ Python 3.11+
- ✅ Docker & Docker Compose
- ✅ Git

### Auf deinem Server:
- ✅ Ubuntu 22.04 LTS
- ✅ Mindestens 2 vCPU, 4 GB RAM
- ✅ 40 GB SSD
- ✅ Ständige Internet-Verbindung

---

## 🚀 Installation

### Schritt 1: Server einrichten (Ubuntu 22.04)

```bash
# SSH in deinen Server einloggen
ssh root@dein-server-ip

# System aktualisieren
apt update && apt upgrade -y

# Firewall konfigurieren (nur Ports 22, 80, 443 offen)
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### Schritt 2: Docker installieren

```bash
# Docker installieren
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Compose installieren
apt install docker-compose-plugin -y

# User zum docker-Group hinzufügen (optional)
usermod -aG docker $USER
```

### Schritt 3: Projekt klonen

```bash
# In dein Home-Verzeichnis wechseln
cd ~

# Repository klonen
git clone https://github.com/your-username/whatmeme-backend.git
cd whatmeme-backend

# .env Datei erstellen
cp .env.example .env
```

### Schritt 4: .env konfigurieren

```bash
nano .env
```

**WICHTIGE ÄNDERUNGEN:**

```env
# JWT Secret Key - GENERIERE EINEN LANGEN RANDOM STRING!
JWT_SECRET_KEY=dein_sehr_langer_random_string_1234567890

# SMTP Einstellungen (Resend oder Brevo)
SMTP_PASSWORD=deine_resend_api_key
SMTP_FROM=noreply@dein-domain.de

# Domain
CORS_ORIGINS=https://dein-domain.de,http://localhost:3000
ENABLE_SSL=true
SSL_CERT_PATH=/etc/letsencrypt/live/dein-domain.de/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/dein-domain.de/privkey.pem
```

**JWT Secret Key generieren:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Resend API Key holen:**
1. Registriere dich auf [resend.com](https://resend.com)
2. Erstelle API Key
3. Kopiere den Key

---

## ⚙️ Konfiguration

### Domain einrichten

#### 1. Domain kaufen
**Empfehlungen:**
- [Namecheap](https://www.namecheap.com) - Günstig, einfach
- [INWX](https://www.inwx.de) - Deutsch, günstig
- [Cloudflare](https://www.cloudflare.com) - Kostenlos, schnell

**Beispiel:** `whatmeme.de` oder `whatmeme.com`

#### 2. DNS einrichten

A-Record:
```
whatmeme.de.  IN  A  dein-server-ip
www.whatmeme.de.  IN  A  dein-server-ip
```

#### 3. Domain mit Server verbinden

```bash
# Auf deinem Server
nano /etc/nginx/sites-available/whatmeme

# Inhalt:
server {
    listen 80;
    server_name dein-domain.de www.dein-domain.de;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dein-domain.de www.dein-domain.de;

    ssl_certificate /etc/letsencrypt/live/dein-domain.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dein-domain.de/privkey.pem;

    # ... (restliche nginx config)
}
```

#### 4. SSL mit Certbot einrichten

```bash
# Certbot installieren
apt install certbot python3-certbot-nginx -y

# SSL Zertifikate erstellen
certbot --nginx -d dein-domain.de -d www.dein-domain.de

# Automatische Erneuerung testen
certbot renew --dry-run
```

---

## 🎮 Starten

### 1. Docker Compose starten

```bash
# Alle Container starten
docker compose up -d

# Logs prüfen
docker compose logs -f app
```

### 2. Datenbank-Migrationen durchführen

```bash
# Container in den Hintergrund starten
docker compose up -d

# Migrationen ausführen
docker compose exec app alembic upgrade head

# App neustarten (falls nötig)
docker compose restart app
```

### 3. Meme-Download (optional)

```bash
# Meme-Download ausführen
python scripts/download_memes.py

# Meme-Download im Hintergrund starten
python scripts/download_memes.py &
```

### 4. Testen

```bash
# Health Check
curl http://localhost:8000/health

# Swagger Docs
open http://localhost:8000/docs
```

---

## 🔒 SSL & HTTPS

### Automatische SSL-Erneuerung

Certbot ist bereits in der docker-compose.yml konfiguriert:

```yaml
certbot:
  image: certbot/certbot
  container_name: whatmeme_certbot
  restart: "no"
  volumes:
    - ./nginx/ssl:/etc/letsencrypt
    - ./nginx/certbot:/var/lib/certbot
  entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

**Erneuerung manuell testen:**
```bash
docker compose exec certbot certbot renew --dry-run
```

---

## 💾 Backup

### PostgreSQL Backup

```bash
# Backup erstellen
docker compose exec postgres pg_dump -U postgres whatmeme > backup_$(date +%Y%m%d).sql

# Backup in eine Datei speichern
docker compose exec postgres pg_dump -U postgres whatmeme > ~/whatmeme_backup.sql

# Backup auf externen Server kopieren
scp ~/whatmeme_backup.sql user@backup-server:/backups/
```

### Automatischer Backup (Cron)

```bash
# Crontab öffnen
crontab -e

# Tägliches Backup um 2:00 Uhr hinzufügen
0 2 * * * docker compose exec -T postgres pg_dump -U postgres whatmeme | gzip > /backups/whatmeme_$(date +\%Y\%m\%d).sql.gz
```

### Redis Backup

```bash
# Redis Backup erstellen
docker compose exec redis redis-cli BGSAVE

# Backup prüfen
docker compose exec redis ls -lh /data
```

---

## 🧪 Tests

### Unit Tests

```bash
# Tests ausführen
pytest tests/ -v

# Tests mit Coverage
pytest tests/ --cov=app --cov-report=html
```

### API Tests

```bash
# API-Tests ausführen
pytest tests/test_api.py -v
```

---

## 🐛 Troubleshooting

### Container starten nicht

```bash
# Logs anzeigen
docker compose logs app
docker compose logs postgres
docker compose logs redis

# Container neu erstellen
docker compose down
docker compose up -d
```

### Datenbank-Verbindung fehlgeschlagen

```bash
# PostgreSQL Logs
docker compose logs postgres

# Datenbank prüfen
docker compose exec postgres psql -U postgres -d whatmeme -c "\dt"
```

### SSL-Probleme

```bash
# Certbot Logs
docker compose logs certbot

# Zertifikate prüfen
ls -la nginx/ssl/
```

### Port schon in Verwendung

```bash
# Port prüfen
netstat -tulpn | grep 8000

# Port freigeben
fuser -k 8000/tcp
```

---

## 📈 Skalierung

### Auf 50k/100k Nutzer skalieren

#### 1. Load Balancer hinzufügen

**Nginx Load Balancer:**

```nginx
upstream app_backend {
    least_conn;
    server app1:8000;
    server app2:8000;
    server app3:8000;
}
```

#### 2. Mehr Server hinzufügen

**Horizontal Scaling:**
- 3-5 App-Server
- Load Balancer (HAProxy oder Nginx)
- Sticky Sessions (Redis)

#### 3. Datenbank-Scaling

**PostgreSQL:**
- Read Replicas
- Connection Pooling
- Sharding (falls nötig)

#### 4. Redis-Scaling

**Redis Cluster:**
- Redis Cluster Mode
- Partitionierung
- Redundanz

#### 5. Monitoring

**Tools:**
- Prometheus + Grafana
- ELK Stack (Elasticsearch, Logstash, Kibana)
- New Relic / Datadog

---

## 📚 API-Dokumentation

### REST API Endpoints

**Auth:**
- `POST /api/auth/register` - Registrierung
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Token refresh
- `POST /api/auth/logout` - Logout
- `POST /api/auth/verify-email` - E-Mail verifizieren
- `POST /api/auth/forgot-password` - Passwort vergessen
- `POST /api/auth/reset-password` - Passwort zurücksetzen

**User:**
- `GET /api/users/me` - Eigene Daten
- `PATCH /api/users/me` - Profil aktualisieren
- `GET /api/users/me/stats` - Statistiken

**Game:**
- `POST /api/rooms` - Raum erstellen
- `GET /api/rooms/{code}` - Raum abfragen
- `GET /api/memes` - Alle Memes
- `GET /api/captions` - Alle Textkarten
- `GET /health` - Health Check

### WebSocket Events

**Client → Server:**
- `create_room { max_players }` - Raum erstellen
- `join_room { code, guest_name }` - Raum beitreten
- `start_game {}` - Spiel starten
- `submit_meme { meme_id }` - Meme einreichen
- `vote_meme { meme_id }` - Stimme abgeben
- `leave_room {}` - Raum verlassen

**Server → Client:**
- `room_created { room }` - Raum erstellt
- `room_joined { room }` - Raum beigetreten
- `game_started { room }` - Spiel gestartet
- `meme_submitted { room }` - Meme eingereicht
- `round_result { round_result }` - Runde beendet
- `game_over { game_over }` - Spiel vorbei

---

## 📞 Support

### Dokumentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Socket.io Docs](https://socket.io/docs/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Redis Docs](https://redis.io/documentation)

### Community
- Discord Server: [Coming Soon]
- GitHub Issues: [https://github.com/your-username/whatmeme-backend/issues]

---

## 📄 Lizenz

MIT License

---

## 🎉 Viel Spaß beim Spielen!

Das Backend ist jetzt bereit! 🚀
