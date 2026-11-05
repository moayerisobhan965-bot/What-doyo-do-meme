#!/bin/bash

# What Meme Backend Setup Script
# Führt die ersten Schritte aus

set -e

echo "🚀 What Meme Backend Setup"
echo "=========================="
echo ""

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Docker prüfen
echo -e "${BLUE}[1/6]${NC} Prüfe Docker Installation..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker nicht gefunden! Installiere Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    echo -e "${GREEN}✅ Docker installiert${NC}"
else
    echo -e "${GREEN}✅ Docker ist installiert${NC}"
fi

# Docker Compose prüfen
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose nicht gefunden! Installiere Docker Compose...${NC}"
    apt install docker-compose-plugin -y
    echo -e "${GREEN}✅ Docker Compose installiert${NC}"
else
    echo -e "${GREEN}✅ Docker Compose ist installiert${NC}"
fi

echo ""

# 2. .env Datei erstellen
echo -e "${BLUE}[2/6]${NC} Konfiguriere .env Datei..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ .env Datei erstellt${NC}"
else
    echo -e "${GREEN}✅ .env Datei existiert bereits${NC}"
fi

echo ""

# 3. Docker Compose starten
echo -e "${BLUE}[3/6]${NC} Starte Docker Compose..."
docker compose down 2>/dev/null || true
docker compose up -d
echo -e "${GREEN}✅ Docker Compose gestartet${NC}"

echo ""

# 4. Warten auf Datenbank
echo -e "${BLUE}[4/6]${NC} Warte auf Datenbank..."
sleep 10

# 5. Migrationen durchführen
echo -e "${BLUE}[5/6]${NC} Führe Database Migrationen aus..."
docker compose exec app alembic upgrade head
echo -e "${GREEN}✅ Migrationen erfolgreich${NC}"

echo ""

# 6. Meme-Download starten
echo -e "${BLUE}[6/6]${NC} Starte Meme-Download..."
echo -e "${YELLOW}⚠️  Meme-Download wird im Hintergrund gestartet${NC}"
python scripts/download_memes.py &
MEME_DOWNLOAD_PID=$!

echo ""
echo -e "${GREEN}=========================="
echo -e "✅ Setup abgeschlossen!"
echo -e "=========================="
echo ""
echo -e "${BLUE}Nächste Schritte:${NC}"
echo "1. Konfiguriere .env Datei:"
echo "   nano .env"
echo ""
echo "2. WICHTIG: Generiere einen JWT Secret Key:"
echo "   python3 -c \"import secrets; print(secrets.token_urlsafe(64))\""
echo ""
echo "3. WICHTIG: Setze SMTP Einstellungen (Resend/Brevo):"
echo "   SMTP_PASSWORD=dein_api_key"
echo ""
echo "4. SSL einrichten:"
echo "   certbot --nginx -d dein-domain.de -d www.dein-domain.de"
echo ""
echo "5. Logs anzeigen:"
echo "   docker compose logs -f app"
echo ""
echo "6. Health Check:"
echo "   curl http://localhost:8000/health"
echo ""
echo "7. Swagger Docs:"
echo "   open http://localhost:8000/docs"
echo ""

# Meme Download PID speichern
echo $MEME_DOWNLOAD_PID > .meme_download.pid

# Cleanup bei Exit
trap "kill $MEME_DOWNLOAD_PID 2>/dev/null || true" EXIT
