"""
What Meme Backend - Vollständiges Backend in einer Datei
FastAPI + WebSockets + E-Mail System wie bei GitHub/Google
GEFIXT - funktioniert mit Godot 4.7 Client, Web und Mobile
"""
import json
import os
import random
import asyncio
import struct
import zlib
import bcrypt
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from jose import JWTError, jwt
import aiohttp
from redis import asyncio as aioredis

# ===== CONFIGURATION =====
class Settings:
    APP_NAME = "What Meme"
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = APP_ENV != "production"
    VERSION = "1.1.0"
    HOST = "0.0.0.0"
    PORT = int(os.getenv("PORT", "8000"))
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/whatmeme"
    )
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_this_to_a_very_long_random_string")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Resend API Key
    SMTP_FROM = os.getenv("SMTP_FROM", "noreply@whatmeme.de")
    SMTP_FROM_NAME = "What Meme"
    MAX_PLAYERS_PER_ROOM = 10
    MIN_PLAYERS_TO_START = 2
    WIN_SCORE = int(os.getenv("WIN_SCORE", "5"))
    # Nur für Tests: Verifizierungs-Codes in der API-Antwort zurückgeben (NIE in Produktion setzen!)
    DEV_CODE_RETURN = os.getenv("DEV_CODE_RETURN", "0") == "1"

settings = Settings()

# ===== DATABASE =====
Base = declarative_base()
engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=20, max_overflow=40)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# ===== MODELS =====
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

class EmailVerification(Base):
    __tablename__ = "email_verifications"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(10), unique=True, index=True, nullable=False)  # 6-stelliger Code
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(10), unique=True, index=True, nullable=False)  # 6-stelliger Code
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class GameHistory(Base):
    __tablename__ = "game_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_code = Column(String(10), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    won = Column(Boolean, nullable=False)
    total_players = Column(Integer, nullable=False)
    played_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ===== PASSWORD HASHING (bcrypt direkt - stabil mit Python 3.14) =====
def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]  # bcrypt Limit: 72 Bytes
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pw = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(pw, hashed_password.encode("utf-8"))
    except Exception:
        return False

# ===== JWT =====
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None

# ===== EMAIL SERVICE (Resend API) =====
class EmailService:
    def __init__(self):
        self.api_key = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM
        self.from_name = settings.SMTP_FROM_NAME
        self.base_url = "https://api.resend.com/emails"

    async def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        if not self.api_key or self.api_key == "your_resend_api_key_here":
            print(f"⚠️  Kein E-Mail API Key konfiguriert. E-Mail an {to_email} übersprungen (Entwicklungsmodus).")
            return True  # Entwicklungsmodus: kein echter Versand

        payload = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status in (200, 202):
                        print(f"✅ E-Mail gesendet: {to_email} - {subject}")
                        return True
                    print(f"❌ E-Mail Fehler {response.status}: {await response.text()}")
                    return False
        except Exception as e:
            print(f"❌ E-Mail Versand fehlgeschlagen: {e}")
            return False

    async def send_verification_email(self, to_email: str, username: str, code: str) -> bool:
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
            <h1 style="color:#4CAF50">✅ E-Mail verifizieren</h1>
            <p>Hallo {username},</p>
            <p>Vielen Dank für die Registrierung bei <strong>What Meme</strong>!</p>
            <p><strong>Dein Verifizierungs-Code:</strong></p>
            <p style="font-size:32px;font-weight:bold;color:#4CAF50;letter-spacing:5px">{code}</p>
            <p style="font-size:14px;color:#666">Der Code ist 24 Stunden gültig.</p>
        </div>"""
        return await self.send_email(to_email, "Verifizierungs-Code für What Meme", html)

    async def send_password_reset_email(self, to_email: str, username: str, code: str) -> bool:
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
            <h1 style="color:#FF5722">🔑 Passwort zurücksetzen</h1>
            <p>Hallo {username},</p>
            <p>Wir haben einen Passwort-Reset für dein <strong>What Meme</strong> Konto angefordert.</p>
            <p><strong>Dein Reset-Code:</strong></p>
            <p style="font-size:32px;font-weight:bold;color:#FF5722;letter-spacing:5px">{code}</p>
            <p style="font-size:14px;color:#666">Der Code ist 24 Stunden gültig.</p>
        </div>"""
        return await self.send_email(to_email, "Reset-Code für What Meme", html)

email_service = EmailService()

# ===== REDIS WRAPPER =====
class RedisStore:
    def __init__(self, url: str):
        self.client = aioredis.from_url(url, decode_responses=True)

    async def set_room_state(self, room_code: str, room: dict, ttl: int = 86400):
        await self.client.set(f"room:{room_code}", json.dumps(room), ex=ttl)

    async def get_room_state(self, room_code: str) -> Optional[dict]:
        raw = await self.client.get(f"room:{room_code}")
        return json.loads(raw) if raw else None

    async def delete_room_state(self, room_code: str):
        await self.client.delete(f"room:{room_code}")

    async def set_refresh_token(self, token: str, user_id: int):
        await self.client.set(f"refresh:{token}", str(user_id), ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)

store = RedisStore(settings.REDIS_URL)

# ===== GAME DATEN =====
# Beliebte Memes - Karten werden vom Backend selbst als PNG generiert (kein externer Dienst!)
_POPULAR_MEME_NAMES = [
    "BIG BABA BUM", "DRAKE HOTLINE", "DOGE", "GRUMPY CAT", "SURPRISED PIKACHU",
    "DISTRACTED BF", "THIS IS FINE", "YELLING AT CAT", "BERNIE SANDERS",
    "EXPANDING BRAIN", "SAD KEANU", "SUCCESS KID", "SPONGEBOB MOCK",
    "ROLL SAFE", "HIDE THE PAIN", "IS THIS A PIGEON", "CHANGE MY MIND",
    "MITTWOCHSFROSCH", "SIDE EYE CHLOE", "STONKS", "UNO REVERSE",
    "CHUCK NORRIS", "RICKROLL", "OVER 9000", "DEAL WITH IT", "EVIL KERMIT",
    "BUTTERFLY GUY", "MONKEY PUPPET", "GIGA CHAD", "AMONG US SUS",
    "PEPE THE FROG", "LEEROY JENKINS", "TRADE OFFER", "ME AND THE BOYS",
    "THANOS SNAP", "ELMO FIRE", "CAT JAM", "GALAXY BRAIN", "SHREK",
    "SWEATING MAN", "CASH MONEY", "GOOD MORNING", "ALLES GUT", "PRESS F",
]

MEMES = [
    {
        "id": i + 1,
        "url": f"/meme-images/{i + 1}.png",
        "width": 400,
        "height": 400,
        "name": _POPULAR_MEME_NAMES[i],
    }
    for i in range(len(_POPULAR_MEME_NAMES))
]

# 5x7 Bitmap-Font für Text auf den Meme-Karten
_FONT_5X7 = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
    "'": ["00100", "00100", "00000", "00000", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    ">": ["10000", "01000", "00100", "00010", "00100", "01000", "10000"],
}

def _text_width(text: str) -> int:
    return max(1, sum(6 for _ in text) - 1)

def _draw_text(buf: bytearray, w: int, h: int, x0: int, y0: int, text: str, scale: int, color):
    cx = x0
    for ch in text.upper():
        glyph = _FONT_5X7.get(ch)
        if glyph is None:
            cx += 6 * scale
            continue
        for gy in range(7):
            row = glyph[gy]
            for gx in range(5):
                if row[gx] == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            px_x = cx + gx * scale + dx
                            px_y = y0 + gy * scale + dy
                            if 0 <= px_x < w and 0 <= px_y < h:
                                idx = (px_y * w + px_x) * 4
                                buf[idx] = color[0]
                                buf[idx + 1] = color[1]
                                buf[idx + 2] = color[2]
                                buf[idx + 3] = 255
        cx += 6 * scale

_MEME_COLOR_PAIRS = [
    ((255, 107, 107), (255, 0, 0)), ((255, 159, 67), (255, 87, 34)),
    ((255, 221, 87), (255, 152, 0)), ((120, 224, 143), (0, 200, 83)),
    ((80, 205, 255), (0, 150, 255)), ((130, 140, 255), (70, 80, 255)),
    ((200, 130, 255), (150, 60, 255)), ((255, 130, 200), (255, 60, 160)),
    ((0, 190, 160), (0, 130, 120)), ((160, 230, 80), (100, 180, 40)),
    ((255, 190, 90), (230, 120, 30)), ((90, 200, 220), (30, 140, 180)),
]

_meme_png_cache: Dict[int, bytes] = {}

def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

def _make_meme_png(meme_id: int) -> bytes:
    """Generiert eine 400x400 Meme-Karte mit dem Meme-Namen als Text."""
    w = h = 400
    idx = (meme_id - 1) % len(MEMES)
    name = MEMES[idx]["name"]
    c1, c2 = _MEME_COLOR_PAIRS[idx % len(_MEME_COLOR_PAIRS)]

    buf = bytearray(w * h * 4)
    for y in range(h):
        ty = y / float(h)
        br = int(c1[0] + (c2[0] - c1[0]) * ty)
        bg = int(c1[1] + (c2[1] - c1[1]) * ty)
        bb = int(c1[2] + (c2[2] - c1[2]) * ty)
        for x in range(w):
            r, g, b = br, bg, bb
            if (x + y) % 64 < 22:
                r, g, b = min(br + 45, 255), min(bg + 45, 255), min(bb + 45, 255)
            idx4 = (y * w + x) * 4
            buf[idx4] = r
            buf[idx4 + 1] = g
            buf[idx4 + 2] = b
            buf[idx4 + 3] = 255

    # Weiße Karte in der Mitte
    card_x0, card_y0, card_x1, card_y1 = 55, 75, 345, 325
    for y in range(card_y0, card_y1):
        for x in range(card_x0, card_x1):
            idx4 = (y * w + x) * 4
            buf[idx4] = 250
            buf[idx4 + 1] = 250
            buf[idx4 + 2] = 250
            buf[idx4 + 3] = 255
    # Kartenrand
    for y in range(card_y0 - 4, card_y1 + 4):
        for x in range(card_x0 - 4, card_x1 + 4):
            border = (x < card_x0 or x >= card_x1 or y < card_y0 or y >= card_y1)
            if border:
                idx4 = (y * w + x) * 4
                buf[idx4] = c2[0]
                buf[idx4 + 1] = c2[1]
                buf[idx4 + 2] = c2[2]
                buf[idx4 + 3] = 255

    # "MEME"-Badge oben links
    _draw_text(buf, w, h, card_x0 + 14, card_y0 + 10, "MEME", 2, (c2[0], c2[1], c2[2]))

    # Meme-Name auf der Karte (max. 2 Zeilen)
    words = name.split()
    lines = []
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if line == "" or _text_width(test) * 4 <= (card_x1 - card_x0 - 24):
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    if len(lines) > 2:
        # Zu lang: letzte Zeile kürzen
        lines = lines[:2]
        lines[1] = lines[1][:10] + ".." if len(lines[1]) > 10 else lines[1]

    scale = 4
    max_width = max(_text_width(l) for l in lines)
    while max_width * scale > (card_x1 - card_x0 - 24) and scale > 2:
        scale -= 1

    total_h = len(lines) * 7 * scale + (len(lines) - 1) * 6 * scale
    y_start = card_y0 + (card_y1 - card_y0 - total_h) // 2 + 20
    text_color = (30, 30, 45)
    for i, l in enumerate(lines):
        tw = _text_width(l) * scale
        x_start = card_x0 + ((card_x1 - card_x0) - tw) // 2
        _draw_text(buf, w, h, x_start, y_start + i * 13 * scale, l, scale, text_color)

    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += bytes(buf[y * w * 4:(y + 1) * w * 4])
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + _png_chunk(b"IEND", b""))

def get_meme_png(meme_id: int) -> bytes:
    if meme_id not in _meme_png_cache:
        _meme_png_cache[meme_id] = _make_meme_png(meme_id)
    return _meme_png_cache[meme_id]

CAPTIONS = [
    "Wenn du am Montag aufwachst...",
    "Mein WLAN, wenn ich zocke...",
    "Ich nach 5 Minuten Sport...",
    "Wenn der Döner nur 5€ kostet...",
    "Mein Wecker um 6 Uhr morgens...",
    "Wenn du das letzte Stück Pizza bekommst...",
    "Ich, wenn ich meinen Code verstehe...",
    "Wenn der Lehrer sagt 'Packt eure Sachen weg'...",
    "Mein Akku bei 1%...",
    "Wenn der Kaffee endlich wirkt...",
    "Ich versuche, erwachsen zu sein...",
    "Wenn der Kuchen fertig ist...",
    "Mein Handy fällt aufs Gesicht...",
    "Wenn die Gruppe sich auf einen Film einigt...",
    "Ich habe das Passwort vergessen...",
    "Wenn du im Meeting etwas sagen musst...",
    "Der letzte Spieltag der Saison...",
    "Ich schaue auf mein Bankkonto...",
    "Wenn Oma dir 20€ zusteckt...",
    "Mein Bruder, wenn ich sein Essen esse...",
    "Wenn der Download bei 99% stoppt...",
    "Ich nach der vierten Tasse Kaffee...",
    "Wenn du den Bus verpasst...",
    "Wenn alle lachen, du aber nichts verstanden hast...",
    "Ich, wenn ich um 22 Uhr ins Bett gehe...",
    "Wenn der Kiosk noch offen hat...",
    "Mein Gesicht bei der Matheaufgabe...",
    "Wenn der Server down ist...",
    "Ich warte auf mein Essen...",
    "Wenn die Eltern früh nach Hause kommen...",
    "Wenn du im Lotto gewinnst...",
    "Mein Hund, wenn ich nach Hause komme...",
    "Wenn die Lehrerin mich aufruft...",
    "Ich trinke meinen ersten Kaffee...",
    "Wenn es endlich Freitag ist...",
    "Wenn jemand mein Handy benutzen will...",
    "Ich schaue TikToks um 3 Uhr nachts...",
    "Wenn der Streamer meinen Namen liest...",
    "Mein Kopf am Sonntagabend...",
    "Wenn das Update 2 Stunden dauert...",
]

# ===== SPIEL-LOGIK =====
class GameState:
    LOBBY = "lobby"
    PLAYING = "playing"
    VOTING = "voting"
    RESULT = "result"
    GAME_OVER = "game_over"

# Per-Raum Locks gegen Lost-Update-Races (mehrere Spieler mutieren parallel)
_locks: Dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()

async def _room_lock(room_code: str) -> asyncio.Lock:
    async with _locks_guard:
        if room_code not in _locks:
            _locks[room_code] = asyncio.Lock()
        return _locks[room_code]

class GameLogic:
    async def create_room(self, room_code: str, host_id: str, host_name: str,
                          max_players: int = 10, avatar_url: Optional[str] = None,
                          rounds_limit: int = 0) -> dict:
        room = {
            "code": room_code,
            "state": GameState.LOBBY,
            "host_id": host_id,
            "max_players": max_players,
            "rounds_limit": rounds_limit,  # 0 = unbegrenzt
            "players": [{
                "id": host_id, "name": host_name, "is_host": True,
                "is_guest": False, "is_ready": True, "avatar_url": avatar_url, "score": 0
            }],
            "scores": {host_id: 0},
            "current_round": 0,
            "judge_index": 0,
            "drawn_caption": None,
            "round_memes": [],
            "submissions": {},
            "votes": {},
            "round_submitters": [],
            "round_voters": [],
            "last_result": None,
            "game_over": False,
            "winner_id": None,
        }
        await store.set_room_state(room_code, room)
        return room

    async def join_room(self, room_code: str, player_id: str, player_name: str,
                        is_guest: bool = False, avatar_url: Optional[str] = None) -> Optional[dict]:
        async with await _room_lock(room_code):
            room = await store.get_room_state(room_code)
            if not room:
                return None
            if room["state"] == GameState.GAME_OVER:
                return room  # Kein Beitritt mehr möglich

            # Bereits im Raum? Dann nur Name aktualisieren
            for p in room["players"]:
                if p["id"] == player_id:
                    p["name"] = player_name
                    p["is_ready"] = True
                    await store.set_room_state(room_code, room)
                    return room

            if len(room["players"]) >= room["max_players"]:
                return None  # Raum voll

            room["players"].append({
                "id": player_id, "name": player_name, "is_host": False,
                "is_guest": is_guest, "is_ready": True, "avatar_url": avatar_url, "score": 0
            })
            room["scores"][player_id] = 0
            if room["state"] != GameState.LOBBY:
                room["state"] = GameState.LOBBY
                self._cancel_timer_sync(room_code)
            await store.set_room_state(room_code, room)
            return room

    async def leave_room(self, room_code: str, player_id: str) -> Optional[dict]:
        async with await _room_lock(room_code):
            room = await store.get_room_state(room_code)
            if not room:
                return None
            room["players"] = [p for p in room["players"] if p["id"] != player_id]
            room["scores"].pop(player_id, None)

            if not room["players"]:
                await store.delete_room_state(room_code)
                self._cancel_timer_sync(room_code)
                return None

            if room["host_id"] == player_id:
                room["host_id"] = room["players"][0]["id"]
                room["players"][0]["is_host"] = True

            await store.set_room_state(room_code, room)
            return room

    async def start_game(self, room_code: str, player_id: str) -> dict:
        async with await _room_lock(room_code):
            room = await store.get_room_state(room_code)
            if not room:
                raise ValueError("Raum nicht gefunden")
            if room["host_id"] != player_id:
                raise PermissionError("Nur der Host kann das Spiel starten")
            if len(room["players"]) < settings.MIN_PLAYERS_TO_START:
                raise ValueError(f"Mindestens {settings.MIN_PLAYERS_TO_START} Spieler erforderlich")
            if room["state"] != GameState.LOBBY:
                raise ValueError("Spiel läuft bereits")
            room["state"] = GameState.PLAYING
            room["current_round"] = 0
            await store.set_room_state(room_code, room)
            return room

    async def start_round(self, room_code: str):
        async with await _room_lock(room_code):
            await self._start_round_locked(room_code)

    async def _start_round_locked(self, room_code: str):
        room = await store.get_room_state(room_code)
        if not room or room["state"] in (GameState.GAME_OVER,):
            return
        players = room["players"]
        if len(players) < settings.MIN_PLAYERS_TO_START:
            room["state"] = GameState.LOBBY
            await store.set_room_state(room_code, room)
            return

        judge_index = room["current_round"] % len(players)
        judge = players[judge_index]
        caption = random.choice(CAPTIONS)
        memes = random.sample(MEMES, 6)

        room["current_round"] += 1
        room["judge_index"] = judge_index
        room["drawn_caption"] = caption
        room["round_memes"] = memes
        room["submissions"] = {}
        room["votes"] = {}
        room["round_submitters"] = [p["id"] for p in players if p["id"] != judge["id"]]
        room["round_voters"] = [p["id"] for p in players]
        room["last_result"] = None
        room["state"] = GameState.PLAYING
        await store.set_room_state(room_code, room)

        await manager.send_to_room(room_code, {
            "event": "round_started",
            "round": room["current_round"],
            "caption": caption,
            "memes": memes,
            "judge_id": judge["id"],
            "judge_name": judge["name"],
            "room": room,
        })

    async def submit_meme(self, room_code: str, player_id: str, meme_id: int) -> dict:
        async with await _room_lock(room_code):
            room = await store.get_room_state(room_code)
            if not room or room["state"] != GameState.PLAYING:
                raise ValueError("Keine Einreichung möglich")
            judge = room["players"][room["judge_index"]]
            if player_id == judge["id"]:
                raise ValueError("Du bist der Richter diese Runde")
            if player_id not in room["round_submitters"]:
                raise ValueError("Du bist diese Runde nicht dabei")

            meme = next((m for m in room["round_memes"] if m["id"] == meme_id), None)
            if not meme:
                raise ValueError("Meme nicht gefunden")
            room["submissions"][player_id] = meme
            await store.set_room_state(room_code, room)

            if len(room["submissions"]) >= len(room["round_submitters"]):
                room["state"] = GameState.VOTING
                room["votes"] = {}
                await store.set_room_state(room_code, room)
                subs = []
                for pid, m in room["submissions"].items():
                    p = next((x for x in room["players"] if x["id"] == pid), None)
                    subs.append({
                        "player_id": pid,
                        "player_name": p["name"] if p else "Unbekannt",
                        "meme_url": m["url"],
                    })
                random.shuffle(subs)
                await manager.send_to_room(room_code, {
                    "event": "voting_started",
                    "submissions": subs,
                    "judge_id": judge["id"],
                    "room": room,
                })
            return room

    async def vote(self, room_code: str, player_id: str, target_player_id: str) -> dict:
        async with await _room_lock(room_code):
            room = await store.get_room_state(room_code)
            if not room or room["state"] != GameState.VOTING:
                raise ValueError("Keine Abstimmung möglich")
            if player_id not in room["round_voters"]:
                raise ValueError("Du bist diese Runde nicht dabei")
            if target_player_id not in room["submissions"]:
                raise ValueError("Ungültige Abstimmung")
            if target_player_id == player_id:
                raise ValueError("Du kannst nicht für dich selbst abstimmen")
            room["votes"][player_id] = target_player_id
            await store.set_room_state(room_code, room)

            if len(room["votes"]) >= len(room["round_voters"]):
                return await self._finish_round_locked(room_code)
            return room

    async def _finish_round_locked(self, room_code: str) -> dict:
        room = await store.get_room_state(room_code)
        if not room:
            return {}
        tally: Dict[str, int] = {}
        for target in room["votes"].values():
            tally[target] = tally.get(target, 0) + 1
        if not tally:
            return room
        winner_id = max(tally, key=tally.get)
        room["scores"][winner_id] = room["scores"].get(winner_id, 0) + 1
        for p in room["players"]:
            p["score"] = room["scores"].get(p["id"], 0)
        winner = next((p for p in room["players"] if p["id"] == winner_id), None)
        winner_name = winner["name"] if winner else "Unbekannt"
        winning_meme = room["submissions"].get(winner_id, {})
        room["state"] = GameState.RESULT
        room["last_result"] = {
            "winner_id": winner_id,
            "winner_name": winner_name,
            "meme_url": winning_meme.get("url", ""),
            "votes": tally,
            "scores": dict(room["scores"]),
        }
        await store.set_room_state(room_code, room)

        await manager.send_to_room(room_code, {
            "event": "round_result",
            "winner_id": winner_id,
            "winner_name": winner_name,
            "meme_url": winning_meme.get("url", ""),
            "votes": tally,
            "scores": dict(room["scores"]),
            "round": room["current_round"],
            "room": room,
        })

        game_over = False
        if room["rounds_limit"] > 0 and room["current_round"] >= room["rounds_limit"]:
            game_over = True  # Runden-Limit erreicht → höchste Punktzahl gewinnt
        elif room["rounds_limit"] == 0 and room["scores"].get(winner_id, 0) >= settings.WIN_SCORE:
            game_over = True  # Unbegrenzt: 5 Punkte = Sieg
        if game_over:
            self._schedule(room_code, self.finish_game(room_code), delay=6.0)
        else:
            self._schedule(room_code, self.start_round(room_code), delay=6.0)
        return room

    async def finish_game(self, room_code: str):
        async with await _room_lock(room_code):
            room = await store.get_room_state(room_code)
            if not room or room["state"] == GameState.GAME_OVER:
                return
            winner_id = max(room["scores"], key=room["scores"].get) if room["scores"] else None
            winner = next((p for p in room["players"] if p["id"] == winner_id), None)
            room["state"] = GameState.GAME_OVER
            room["game_over"] = True
            room["winner_id"] = winner_id
            await store.set_room_state(room_code, room)

            await manager.send_to_room(room_code, {
                "event": "game_over",
                "winner_id": winner_id,
                "winner_name": winner["name"] if winner else "Unbekannt",
                "scores": dict(room["scores"]),
                "room": room,
            })
            await self._save_game_history(room_code, room)

    async def _save_game_history(self, room_code: str, room: dict):
        winner_id = room.get("winner_id")
        total = len(room["players"])
        async with AsyncSessionLocal() as session:
            try:
                for p in room["players"]:
                    try:
                        uid = int(p["id"])
                    except (ValueError, TypeError):
                        continue
                    session.add(GameHistory(
                        user_id=uid,
                        room_code=room_code,
                        score=room["scores"].get(p["id"], 0),
                        won=(p["id"] == winner_id),
                        total_players=total,
                    ))
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"❌ GameHistory Fehler: {e}")

    async def skip_result(self, room_code: str):
        async with await _room_lock(room_code):
            room = await store.get_room_state(room_code)
            if not room or room["state"] != GameState.RESULT:
                return
            game_over = False
            if room["rounds_limit"] > 0 and room["current_round"] >= room["rounds_limit"]:
                game_over = True
            elif room["rounds_limit"] == 0 and any(s >= settings.WIN_SCORE for s in room["scores"].values()):
                game_over = True
            if game_over:
                self._schedule(room_code, self.finish_game(room_code), delay=0.1)
            else:
                self._schedule(room_code, self.start_round(room_code), delay=0.1)

    def _schedule(self, room_code: str, coro, delay: float = 6.0):
        self._cancel_timer_sync(room_code)
        async def _run():
            try:
                await asyncio.sleep(delay)
                await coro
            except asyncio.CancelledError:
                pass
        task = asyncio.create_task(_run())
        _timers[room_code] = task

    async def _cancel_timer(self, room_code: str):
        self._cancel_timer_sync(room_code)

    def _cancel_timer_sync(self, room_code: str):
        task = _timers.pop(room_code, None)
        if task and not task.done():
            task.cancel()

    async def get_room_state(self, room_code: str) -> Optional[dict]:
        return await store.get_room_state(room_code)

_timers: Dict[str, asyncio.Task] = {}
game_logic = GameLogic()

# ===== WEBSOCKET MANAGER =====
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, room_code: str, player_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(room_code, {})[player_id] = websocket

    async def disconnect(self, room_code: str, player_id: str):
        room = self.active_connections.get(room_code)
        if room and player_id in room:
            try:
                await room[player_id].close()
            except Exception:
                pass
            del room[player_id]
        if room is not None and not room:
            self.active_connections.pop(room_code, None)

    async def send_to_room(self, room_code: str, message: Dict[str, Any]):
        room = self.active_connections.get(room_code)
        if not room:
            return
        for conn in list(room.values()):
            try:
                await conn.send_json(message)
            except Exception:
                pass

    async def send_to_player(self, room_code: str, player_id: str, message: Dict[str, Any]):
        room = self.active_connections.get(room_code)
        if room and player_id in room:
            try:
                await room[player_id].send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

async def _log_room(room_code: str, where: str):
    if not settings.DEBUG:
        return
    room = await game_logic.get_room_state(room_code)
    if room:
        print(f"📊 {where}: players={[p['id'] for p in room['players']]} state={room['state']} "
              f"submitters={room['round_submitters']} subs={list(room['submissions'].keys())} "
              f"voters={room['round_voters']} votes={room['votes']} scores={room['scores']}")

# ===== PYDANTIC SCHEMAS =====
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.replace("_", "").isalnum():
            raise ValueError("Nur Buchstaben, Zahlen und Unterstriche erlaubt")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class EmailVerify(BaseModel):
    token: str

class PasswordForgot(BaseModel):
    email: EmailStr

class PasswordResetSchema(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

class RoomCreate(BaseModel):
    max_players: int = Field(10, ge=2, le=10)
    rounds_limit: int = Field(0, ge=0, le=100)  # 0 = unbegrenzt (bis 5 Punkte)

class Meme(BaseModel):
    id: int
    url: str
    width: int
    height: int
    name: str = ""

class Caption(BaseModel):
    id: int
    text: str

# ===== FASTAPI APP =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Datenbank-Tabellen erstellt/geprüft")
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    description="Multiplayer Meme Game Backend",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

# ===== AUTH HELPER =====
async def get_user_from_token(token: Optional[str], db: AsyncSession) -> Optional[User]:
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials else None
    user = await get_user_from_token(token, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nicht autorisiert")
    return user

def user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_verified": user.is_verified,
        "avatar_url": user.avatar_url,
    }

# ===== ENDPOINTS =====
@app.get("/health")
async def health_check():
    db_ok = False
    redis_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        db_ok = True
    except Exception:
        pass
    try:
        redis_ok = bool(await store.client.ping())
    except Exception:
        pass
    return {
        "status": "healthy" if (db_ok and redis_ok) else "degraded",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "env": settings.APP_ENV,
        "database": "connected" if db_ok else "error",
        "redis": "connected" if redis_ok else "error",
    }

# ===== AUTH =====
@app.post("/api/auth/register")
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="E-Mail bereits registriert")
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username bereits vergeben")

    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        is_verified=False,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    verification_code = str(random.randint(100000, 999999))
    db.add(EmailVerification(
        token=verification_code,
        user_id=new_user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    ))
    await db.commit()
    await db.refresh(new_user)

    await email_service.send_verification_email(new_user.email, new_user.username, verification_code)
    print(f"📧 Verifizierungs-Code für {new_user.email}: {verification_code}")

    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})
    await store.set_refresh_token(refresh_token, new_user.id)

    response = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_dict(new_user),
    }
    if settings.DEV_CODE_RETURN:
        response["dev_code"] = verification_code
    return response

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldeinformationen")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Benutzer ist inaktiv")
    if not user.is_verified:
        raise HTTPException(status_code=400, detail="Bitte verifiziere zuerst deine E-Mail")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    await store.set_refresh_token(refresh_token, user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_dict(user))

@app.post("/api/auth/verify-email")
async def verify_email(data: EmailVerify, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailVerification).where(EmailVerification.token == data.token))
    verification = result.scalar_one_or_none()
    if not verification:
        raise HTTPException(status_code=400, detail="Code ungültig oder nicht gefunden")
    if verification.expires_at.replace(tzinfo=None) < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code ist abgelaufen (24h)")

    result = await db.execute(select(User).where(User.id == verification.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user.is_verified = True
    await db.commit()
    print(f"✅ E-Mail verifiziert für {user.email}")
    return {"message": "E-Mail erfolgreich verifiziert! Du kannst dich jetzt einloggen."}

@app.post("/api/auth/forgot-password")
async def forgot_password(data: PasswordForgot, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        return {"message": "Wenn diese E-Mail registriert ist, erhältst du einen Reset-Code"}

    reset_code = str(random.randint(100000, 999999))
    db.add(PasswordReset(
        token=reset_code,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    ))
    await db.commit()

    await email_service.send_password_reset_email(user.email, user.username, reset_code)
    print(f"📧 Reset-Code für {user.email}: {reset_code}")
    response = {"message": "Reset-Code per E-Mail gesendet! Prüfe deine E-Mails."}
    if settings.DEV_CODE_RETURN:
        response["dev_code"] = reset_code
    return response

@app.post("/api/auth/reset-password")
async def reset_password(data: PasswordResetSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PasswordReset).where(PasswordReset.token == data.token))
    password_reset = result.scalar_one_or_none()
    if not password_reset or password_reset.expires_at.replace(tzinfo=None) < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code ungültig oder abgelaufen (24h)")

    result = await db.execute(select(User).where(User.id == password_reset.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user.hashed_password = hash_password(data.new_password)
    await db.delete(password_reset)
    await db.commit()
    print(f"✅ Passwort geändert für {user.email}")
    return {"message": "Passwort erfolgreich geändert! Du kannst dich jetzt einloggen."}

# ===== USER =====
@app.get("/api/users/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return user_dict(current_user)

@app.get("/api/users/me/stats")
async def get_user_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GameHistory).where(GameHistory.user_id == current_user.id)
    )
    games = result.scalars().all()
    total_games = len(games)
    total_wins = sum(1 for g in games if g.won)
    total_score = sum(g.score for g in games)
    return {
        "total_games": total_games,
        "total_wins": total_wins,
        "total_score": total_score,
        "average_score": round(total_score / total_games, 2) if total_games else 0,
        "win_rate": round(total_wins / total_games * 100, 2) if total_games else 0,
    }

# ===== GAME REST =====
@app.post("/api/rooms")
async def create_room(room_data: RoomCreate, current_user: User = Depends(get_current_user)):
    room_code = str(random.randint(1000, 9999))
    # Code-Eindeutigkeit sicherstellen
    while await store.get_room_state(room_code):
        room_code = str(random.randint(1000, 9999))

    room = await game_logic.create_room(
        room_code=room_code,
        host_id=str(current_user.id),
        host_name=current_user.username,
        max_players=room_data.max_players,
        avatar_url=current_user.avatar_url,
        rounds_limit=room_data.rounds_limit,
    )
    return room

@app.get("/api/rooms/{code}")
async def get_room(code: str, current_user: User = Depends(get_current_user)):
    room = await game_logic.get_room_state(code)
    if not room:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")
    return room

@app.get("/api/memes", response_model=List[Meme])
async def get_memes():
    return MEMES

@app.get("/meme-images/{meme_id}.png")
async def get_meme_image(meme_id: int):
    if meme_id < 1 or meme_id > len(MEMES):
        raise HTTPException(status_code=404, detail="Meme nicht gefunden")
    from fastapi.responses import Response
    return Response(content=get_meme_png(meme_id), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})

@app.get("/api/captions", response_model=List[Caption])
async def get_captions():
    return [Caption(id=i + 1, text=t) for i, t in enumerate(CAPTIONS)]

# ===== WEBSOCKET =====
@app.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    token = websocket.query_params.get("token")
    async with AsyncSessionLocal() as session:
        user = await get_user_from_token(token, session)

    if user is None:
        await websocket.accept()
        await websocket.send_json({"event": "error", "message": "Nicht autorisiert - bitte einloggen"})
        await websocket.close(code=4401)
        return

    player_name = user.username
    await manager.connect(room_code, player_id, websocket)

    # Aktuellen Raumzustand senden (falls vorhanden)
    room = await game_logic.get_room_state(room_code)
    if room:
        await manager.send_to_player(room_code, player_id, {"event": "room_state", "room": room})

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")
            if settings.DEBUG:
                print(f"📨 WS {room_code}/{player_id} <- {event}")
            try:
                if event == "join_room":
                    room = await game_logic.join_room(room_code, player_id, player_name)
                    if room is None:
                        await manager.send_to_player(room_code, player_id, {
                            "event": "error", "message": "Raum nicht gefunden oder voll"
                        })
                    else:
                        await manager.send_to_room(room_code, {"event": "room_joined", "room": room})
                        await _log_room(room_code, "join_room")
                elif event == "leave_room":
                    room = await game_logic.leave_room(room_code, player_id)
                    if room:
                        await manager.send_to_room(room_code, {
                            "event": "player_left", "player_id": player_id, "room": room
                        })
                    await manager.disconnect(room_code, player_id)
                    return

                elif event == "start_game":
                    room = await game_logic.start_game(room_code, player_id)
                    await manager.send_to_room(room_code, {"event": "game_started", "room": room})
                    await game_logic.start_round(room_code)
                    await _log_room(room_code, "start_game")

                elif event == "submit_meme":
                    await game_logic.submit_meme(room_code, player_id, int(data.get("meme_id", 0)))
                    await _log_room(room_code, "submit_meme:" + str(data.get("meme_id", 0)))

                elif event == "vote":
                    await game_logic.vote(room_code, player_id, str(data.get("target_player_id", "")))
                    await _log_room(room_code, "vote->" + str(data.get("target_player_id", "")))

                elif event == "next_round":
                    await game_logic.skip_result(room_code)

                elif event == "ping":
                    await manager.send_to_player(room_code, player_id, {"event": "pong"})

            except (ValueError, PermissionError) as e:
                await manager.send_to_player(room_code, player_id, {"event": "error", "message": str(e)})
            except Exception as e:
                print(f"⚠️ WS Fehler ({event}): {e}")
                await manager.send_to_player(room_code, player_id, {
                    "event": "error", "message": "Unerwarteter Fehler"
                })

    except WebSocketDisconnect:
        if settings.DEBUG:
            print(f"🔌 WS disconnect: {room_code}/{player_id}")
    except Exception as e:
        print(f"💥 WS Handler-Fehler: {room_code}/{player_id}: {type(e).__name__}: {e}")
    finally:
        if settings.DEBUG:
            print(f"🏁 WS Handler-Ende: {room_code}/{player_id}")
        await manager.disconnect(room_code, player_id)
        room = await game_logic.leave_room(room_code, player_id)
        if room:
            await manager.send_to_room(room_code, {
                "event": "player_left", "player_id": player_id, "room": room
            })

# ===== INDEX =====
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>What Meme</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a2e; color: #eee; }
            h1 { color: #4CAF50; }
            a { color: #4CAF50; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>🎮 What Meme</h1>
        <p>Backend läuft erfolgreich!</p>
        <p><a href="/docs">Dokumentation</a> | <a href="/health">Health Check</a></p>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
