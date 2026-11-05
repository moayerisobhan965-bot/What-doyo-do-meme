# 🚀 Quick Start Guide (Deutsch)

## Was Meme Backend - Schnellstart

### 📦 Was du brauchst:

1. **Server** (Hetzner VPS ~5€/Monat)
   - 2 vCPU, 4 GB RAM, 40 GB SSD
   - Ubuntu 22.04 LTS

2. **Domain** (Namecheap/INWX)
   - whatmeme.de oder was-du-möchtest.de

3. **Resend API Key** (kostenlos)
   - Registriere dich auf resend.com
   - Erstelle API Key

---

## 🛠️ Installation in 10 Minuten

### Schritt 1: Server einrichten

```bash
# SSH in deinen Server
ssh root@dein-server-ip

# Update
apt update && apt upgrade -y

# Firewall
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
```

### Schritt 3: Projekt klonen

```bash
cd ~
git clone https://github.com/your-username/whatmeme-backend.git
cd whatmeme-backend
```

### Schritt 4: Setup Script ausführen

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Schritt 5: .env konfigurieren

```bash
nano .env
```

**WICHTIG:**

```env
# JWT Secret Key generieren
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Ergebnis kopieren und einfügen:
JWT_SECRET_KEY=DEIN_GENERIERTER_STRING_HIER

# SMTP Einstellungen
SMTP_PASSWORD=DEINE_RESEND_API_KEY_HIER
SMTP_FROM=noreply@dein-domain.de

# Domain
CORS_ORIGINS=https://dein-domain.de,http://localhost:3000
ENABLE_SSL=true
```

### Schritt 6: SSL einrichten

```bash
certbot --nginx -d dein-domain.de -d www.dein-domain.de
```

### Schritt 7: Docker Compose starten

```bash
docker compose restart
```

---

## ✅ Testen

### Health Check
```bash
curl http://localhost:8000/health
```

**Erwartetes Ergebnis:**
```json
{
  "status": "healthy",
  "app": "What Meme",
  "version": "1.0.0",
  "env": "production",
  "database": "connected",
  "redis": "connected"
}
```

### Swagger Docs
```
http://localhost:8000/docs
```

---

## 🎮 Spiel starten

### 1. Registrierung
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "deine@email.de",
    "username": "dein-username",
    "password": "dein-passwort"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "deine@email.de",
    "password": "dein-passwort"
  }'
```

### 3. Raum erstellen
```bash
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer DEIN_ACCESS_TOKEN" \
  -d '{
    "max_players": 10
  }'
```

---

## 📚 Dokumentation

- **README.md** - Vollständige Dokumentation
- **SETUP_SUMMARY.md** - Zusammenfassung
- **CHECKLIST.md** - Checkliste
- **/docs** - Swagger API Docs

---

## 🐛 Probleme?

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

---

## 📊 Services

| Service | Port | Status |
|---------|------|--------|
| App | 8000 | ✅ |
| PostgreSQL | 5432 | ✅ |
| Redis | 6379 | ✅ |
| nginx | 80/443 | ✅ |

---

## 🎉 Fertig!

Dein Backend läuft! 🚀

**Nächste Schritte:**
1. Meme-Download starten: `python scripts/download_memes.py`
2. Spiele mit Freunden testen
3. Backup einrichten
4. Monitoring aktivieren

---

## 📞 Hilfe

- [GitHub Issues](https://github.com/your-username/whatmeme-backend/issues)
- [Resend Docs](https://resend.com/docs)
- [Hetzner Support](https://docs.hetzner.com)

---

Viel Spaß beim Spielen! 🎮
