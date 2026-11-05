# ✅ Setup Checklist - What Meme Backend

## 📋 Server-Setup

- [ ] Server gekauft (Hetzner VPS oder eigener PC)
- [ ] Ubuntu 22.04 LTS installiert
- [ ] SSH Zugriff konfiguriert
- [ ] Firewall eingerichtet (nur 22, 80, 443 offen)
- [ ] Docker installiert
- [ ] Docker Compose installiert

## 📦 Projekt-Setup

- [ ] Repository geklont
- [ ] Docker Compose gestartet (`docker compose up -d`)
- [ ] Database Migrationen durchgeführt (`docker compose exec app alembic upgrade head`)
- [ ] .env Datei erstellt
- [ ] .env Datei konfiguriert

## ⚙️ Konfiguration

### JWT Secret Key
- [ ] JWT Secret Key generiert (`python3 -c "import secrets; print(secrets.token_urlsafe(64))"`)
- [ ] JWT Secret Key in .env eingetragen

### SMTP Einstellungen
- [ ] Resend/Brevo Account erstellt
- [ ] API Key generiert
- [ ] SMTP_PASSWORD in .env eingetragen
- [ ] SMTP_FROM in .env eingetragen

### Domain
- [ ] Domain gekauft (Namecheap/INWX)
- [ ] DNS A-Records eingerichtet (whatmeme.de, www.whatmeme.de)
- [ ] Domain mit Server verknüpft

### SSL (Let's Encrypt)
- [ ] Certbot installiert
- [ ] SSL Zertifikate erstellt (`certbot --nginx -d dein-domain.de -d www.dein-domain.de`)
- [ ] Automatische Erneuerung getestet (`certbot renew --dry-run`)

### CORS
- [ ] CORS_ORIGINS in .env eingetragen
- [ ] ENABLE_SSL auf true gesetzt

## 🚀 Starten

- [ ] Docker Compose neu gestartet (`docker compose restart`)
- [ ] Logs geprüft (`docker compose logs -f app`)
- [ ] Health Check durchgeführt (`curl http://localhost:8000/health`)
- [ ] Swagger Docs geöffnet (`http://localhost:8000/docs`)

## 🎮 Spiel-Features

### Memes
- [ ] Meme-Download gestartet (`python scripts/download_memes.py`)
- [ ] Memes geladen (100+ Memes)

### Textkarten
- [ ] Textkarten geladen (500+ Karten)

### Auth
- [ ] Registrierung getestet
- [ ] Login getestet
- [ ] E-Mail-Verifizierung getestet
- [ ] Passwort-Reset getestet

### Spiel
- [ ] Raum erstellen getestet
- [ ] Raum beitreten getestet
- [ ] Spiel starten getestet
- [ ] Meme einreichen getestet
- [ ] Abstimmen getestet
- [ ] Runde beenden getestet

## 📊 Monitoring

- [ ] Logs regelmäßig geprüft
- [ ] Health Check regelmäßig geprüft
- [ ] Backup eingerichtet (PostgreSQL)

## 🔒 Sicherheit

- [ ] Firewall aktiviert
- [ ] SSH Port geändert (optional)
- [ ] Fail2ban eingerichtet (optional)
- [ ] Updates regelmäßig durchgeführt

## 📚 Dokumentation

- [ ] README.md gelesen
- [ ] SETUP_SUMMARY.md gelesen
- [ ] API Docs geprüft

## 🎉 Fertig!

- [ ] Alle Punkte erfüllt
- [ ] Spiel kann gestartet werden
- [ ] Backend läuft stabil
- [ ] SSL aktiviert
- [ ] Backup konfiguriert

---

## 🚀 Erster Test

```bash
# 1. Health Check
curl http://localhost:8000/health

# 2. Swagger Docs
open http://localhost:8000/docs

# 3. Meme-Download
python scripts/download_memes.py

# 4. Logs
docker compose logs -f app
```

---

## 📞 Support

- [GitHub Issues](https://github.com/your-username/whatmeme-backend/issues)
- [Resend Docs](https://resend.com/docs)
- [Hetzner Docs](https://docs.hetzner.com)
