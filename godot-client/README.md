# 🎮 What Meme - Godot Client (Godot 4.7)

Multiplayer-Meme-Spiel für **Android & Desktop** - verbindet sich mit dem What-Meme-Backend.

## 🚀 Schnellstart

1. **Godot 4.7** installieren (godotengine.org)
2. Diesen Ordner in Godot öffnen (`project.godot` importieren)
3. Server-Adresse anpassen (siehe unten)
4. Backend starten → Projekt starten (F5)

## 🌐 Server-Adresse anpassen

In `scripts/global.gd` oben:

```gdscript
const DEFAULT_API_BASE := "http://10.0.2.2:8000"
```

| Wo läuft die App?              | Adresse                          |
|--------------------------------|----------------------------------|
| Android **Emulator** (PC)      | `http://10.0.2.2:8000`           |
| Echtes Handy (gleiches WLAN)   | `http://192.168.1.50:8000` (IP des PCs) |
| Produktion (Domain + HTTPS)    | `https://whatmeme.de`            |

> 💡 Tipp: Der PC und das Handy müssen im selben WLAN sein.
> Die PC-IP bekommst du mit `ip a` (Linux) oder `ipconfig` (Windows).

## 📱 Android-APK bauen

1. In Godot: **Editor → Manage Export Templates** → Android-Templates herunterladen
2. **Project → Export...** → Preset "Android" ist bereits angelegt
3. Android SDK-Pfad setzen (Editor Settings → Export → Android)
4. Export drücken → `build/whatmeme.apk`

Das Preset hat bereits:
- ✅ Internet-Berechtigung (`permissions/internet=true`)
- ✅ Querformat (Landscape)
- ✅ Immersive Mode (volle Bildschirmfläche)
- ✅ arm64-Unterstützung

## 🎮 Spielablauf

1. **Login/Registrieren** - E-Mail-Code wird per E-Mail gesendet (wie bei GitHub)
2. **Spiel erstellen**: Spieler-Anzahl (2-10) + Runden wählen (5, 10, 20 oder Unbegrenzt)
3. **Raum erstellen** oder mit 4-stelligem **Code beitreten**
4. **Lobby** - Freunde einladen, Host startet das Spiel
5. **Runde**: Ein Richter zieht eine Caption → alle anderen wählen ein Meme
   (44 beliebte Memes: Big Baba Bum, Drake, Doge, Grumpy Cat, Stonks ...)
6. **Voting**: Alle stimmen für das beste Meme - **Punkte sind immer sichtbar**
7. **Spielende**: Nach dem Runden-Limit gewinnt der Spieler mit den meisten Punkten
   (bei Unbegrenzt: der erste mit 5 Punkten) 🏆

## 🧪 Testen ohne E-Mail-Server

Backend mit Entwicklungsmodus starten (Codes kommen dann in der API-Antwort zurück):

```bash
DEV_CODE_RETURN=1 WIN_SCORE=2 python3 -m uvicorn backend:app --port 8000
```

## 🖼️ Meme-Bilder

Die Meme-Bilder werden **vom Backend selbst generiert** (`/meme-images/{id}.png`) -
kein externer Bilddienst nötig! Das Spiel funktioniert komplett im eigenen Netzwerk.

## 🧪 Eingebaute Tests

```bash
# Szenen-Smoke-Test (prüft alle 5 Szenen)
godot --headless -s res://tests/test_scenes.gd

# Kompletter E2E-Test (3 Spieler, ganzes Spiel - Backend mit DEV_CODE_RETURN=1 nötig)
WM_API_BASE=http://localhost:8001 godot --headless -s res://tests/test_e2e.gd
```

## 📁 Struktur

```
scenes/          Szenen (Login, Home, Lobby, Spiel, Spielende)
scripts/         GDScript-Logik (UI wird komplett im Code aufgebaut)
global.gd        Autoload: Server-Verbindung, HTTP-Queue, WebSocket, Bild-Cache
ui.gd            Autoload: einheitliches UI-Design
tests/           E2E-Test + Szenen-Test
export_presets.cfg  Android-Export-Konfiguration
```
