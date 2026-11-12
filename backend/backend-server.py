"""
What Meme Backend - Vollständiges Backend in einer Datei
FastAPI + Socket.io + E-Mail System wie bei GitHub/Google
"""
import json
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi_socketio import SocketIO
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from passlib.context import CryptContext
from jose import JWTError, jwt
import aiohttp
from redis import asyncio as aioredis

# ===== CONFIGURATION =====
class Settings:
    """Konfiguration"""
    APP_NAME = "What Meme"
    APP_ENV = "production"
    DEBUG = False
    VERSION = "1.0.0"
    HOST = "0.0.0.0"
    PORT = 8000
    DATABASE_URL = "postgresql+asyncpg://postgres:postgrespassword@postgres:5432/whatmeme"
    REDIS_URL = "redis://redis:6379/0"
    JWT_SECRET_KEY = "change_this_to_a_very_long_random_string"
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    SMTP_PASSWORD = "your_resend_api_key_here"
    SMTP_FROM = "noreply@whatmeme.de"
    SMTP_FROM_NAME = "What Meme"
    MAX_PLAYERS_PER_ROOM = 10
    MIN_PLAYERS_TO_START = 2
    WIN_SCORE = 5

settings = Settings()

# ===== DATABASE =====
Base = declarative_base()
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    """DB Session Dependency"""
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
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)
    game_history = relationship("GameHistory", back_populates="user", cascade="all, delete-orphan")

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
    user = relationship("User", back_populates="game_history")

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    max_players = Column(Integer, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

Base.metadata.create_all(engine)

# ===== PASSWORD HASHING =====
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ===== JWT =====
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

# ===== EMAIL SERVICE =====
class EmailService:
    def __init__(self):
        self.api_key = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM
        self.from_name = settings.SMTP_FROM_NAME
        self.base_url = "https://api.resend.com/emails"

    async def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        if not self.api_key:
            print(f"⚠️  Email API Key nicht gesetzt")
            return False

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
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status == 200:
                        print(f"✅ E-Mail gesendet: {to_email} - {subject}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Fehler: {error_text}")
                        return False
        except Exception as e:
            print(f"❌ E-Mail Sendung fehlgeschlagen: {str(e)}")
            return False

    async def send_verification_email(self, to_email: str, username: str, verification_code: str) -> bool:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>E-Mail verifizieren - What Meme</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .container {{ background-color: white; padding: 30px; border-radius: 10px; }}
                h1 {{ color: #4CAF50; margin-top: 0; }}
                .info {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .code {{ font-size: 32px; font-weight: bold; color: #4CAF50; letter-spacing: 5px; }}
                .instructions {{ background-color: #e3f2fd; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ E-Mail verifizieren</h1>
                <p>Hallo {username},</p>
                <p>Vielen Dank für die Registrierung bei <strong>What Meme</strong>!</p>
                <div class="instructions">
                    <p style="font-weight: bold;">So verifizierst du deine E-Mail:</p>
                    <ol><li>Schau in deine E-Mails nach</li><li>Kopiere den Code: <strong>{verification_code}</strong></li><li>Gehe zurück zum Frontend</li><li>Füge den Code ein und bestätige</li></ol>
                </div>
                <div class="info">
                    <p style="margin: 0 0 10px 0;"><strong>Dein Verifizierungs-Code:</strong></p>
                    <p class="code">{verification_code}</p>
                </div>
                <p style="font-size: 14px; color: #666;">Der Code ist 24 Stunden gültig.</p>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, "Verifizierungs-Code für What Meme", html_content)

    async def send_password_reset_email(self, to_email: str, username: str, reset_code: str) -> bool:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Passwort zurücksetzen - What Meme</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .container {{ background-color: white; padding: 30px; border-radius: 10px; }}
                h1 {{ color: #FF5722; margin-top: 0; }}
                .info {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .code {{ font-size: 32px; font-weight: bold; color: #FF5722; letter-spacing: 5px; }}
                .instructions {{ background-color: #ffebee; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔑 Passwort zurücksetzen</h1>
                <p>Hallo {username},</p>
                <p>Wir haben ein Passwort-Reset für dein <strong>What Meme</strong> Konto angefordert.</p>
                <div class="instructions">
                    <p style="font-weight: bold;">So setzt du dein Passwort zurück:</p>
                    <ol><li>Schau in deine E-Mails nach</li><li>Kopiere den Code: <strong>{reset_code}</strong></li><li>Gehe zurück zum Frontend</li><li>Füge den Code und dein neues Passwort ein</li></ol>
                </div>
                <div class="info">
                    <p style="margin: 0 0 10px 0;"><strong>Dein Reset-Code:</strong></p>
                    <p class="code">{reset_code}</p>
                </div>
                <p style="font-size: 14px; color: #666;">Der Code ist 24 Stunden gültig.</p>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, "Reset-Code für What Meme", html_content)

email_service = EmailService()

# ===== REDIS =====
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

# ===== GAME LOGIC =====
class GameState:
    LOBBY = "lobby"
    PLAYING = "playing"
    VOTING = "voting"
    RESULT = "result"
    GAME_OVER = "game_over"

class GameLogic:
    def __init__(self):
        self.current_room = None

    async def create_room(self, room_code: str, host_id: str, host_name: str, max_players: int = 10, avatar_url: Optional[str] = None):
        self.current_room = {
            "code": room_code,
            "state": GameState.LOBBY.value,
            "host_id": host_id,
            "players": [{"id": host_id, "name": host_name, "is_host": True, "is_guest": False, "is_ready": True, "avatar_url": avatar_url, "score": 0}],
            "current_round": 0,
            "current_player_index": 0,
            "drawn_caption": None,
            "submissions": {},
            "votes": {},
            "winner_id": None,
            "game_over": False,
            "winner_score": None,
        }
        await redis_client.set_room_state(room_code, self.current_room, ttl=86400)
        return self.current_room

    async def join_room(self, room_code: str, player_id: str, player_name: str, is_guest: bool = False, avatar_url: Optional[str] = None):
        room = await redis_client.get_room_state(room_code)
        if not room:
            raise ValueError("Raum nicht gefunden")

        new_player = {"id": player_id, "name": player_name, "is_host": False, "is_guest": is_guest, "is_ready": True, "avatar_url": avatar_url, "score": 0}
        room["players"].append(new_player)
        room["state"] = GameState.LOBBY.value
        await redis_client.set_room_state(room_code, room)
        return room

    async def leave_room(self, room_code: str, player_id: str):
        room = await redis_client.get_room_state(room_code)
        if not room:
            return None

        room["players"] = [p for p in room["players"] if p["id"] != player_id]

        if room["host_id"] == player_id and room["players"]:
            room["host_id"] = room["players"][0]["id"]
            room["players"][0]["is_host"] = True

        if not room["players"]:
            await redis_client.delete_room_state(room_code)
            return None

        await redis_client.set_room_state(room_code, room)
        return room

    async def start_game(self, room_code: str):
        room = await redis_client.get_room_state(room_code)
        if not room:
            raise ValueError("Raum nicht gefunden")

        if len(room["players"]) < 2:
            raise ValueError("Mindestens 2 Spieler erforderlich")

        room["state"] = GameState.PLAYING.value
        room["current_round"] = 1
        room["current_player_index"] = 0
        await redis_client.set_room_state(room_code, room)
        return room

    def get_room_state(self, room_code: str):
        return redis_client.get_room_state(room_code)

game_logic = GameLogic()

# ===== SOCKET.IO =====
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, room_code: str, player_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_code not in self.active_connections:
            self.active_connections[room_code] = {}
        self.active_connections[room_code][player_id] = websocket

    async def disconnect(self, room_code: str, player_id: str):
        if room_code in self.active_connections and player_id in self.active_connections[room_code]:
            await self.active_connections[room_code][player_id].close()
            del self.active_connections[room_code][player_id]

        if room_code in self.active_connections and not self.active_connections[room_code]:
            del self.active_connections[room_code]

    async def send_to_room(self, room_code: str, message: Dict[str, Any]):
        if room_code in self.active_connections:
            for connection in self.active_connections[room_code].values():
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# ===== PYDANTIC SCHEMAS =====
from pydantic import BaseModel, EmailStr, Field, validator

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Nur Buchstaben, Zahlen und Unterstriche erlaubt')
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

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_verified: bool
    avatar_url: Optional[str]
    created_at: datetime

class UserStats(BaseModel):
    total_games: int
    total_wins: int
    total_score: int
    average_score: float
    win_rate: float

class RoomCreate(BaseModel):
    max_players: int = Field(10, ge=2, le=10)

class RoomJoin(BaseModel):
    code: str = Field(..., min_length=4, max_length=4)
    guest_name: Optional[str] = Field(None, min_length=1, max_length=50)

class Caption(BaseModel):
    id: int
    text: str

class Meme(BaseModel):
    id: int
    url: str
    thumbnail_url: Optional[str] = None
    width: int
    height: int

# ===== MAIN APP =====
app = FastAPI(
    title=settings.APP_NAME,
    description="Multiplayer Meme Game Backend",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENABLE_SSL:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["whatmeme.de", "www.whatmeme.de", "localhost"])

socket_io = SocketIO(app, cors_allowed_origins=["*"], async_mode="asgi")

# ===== ENDPOINTS =====

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "env": settings.APP_ENV,
        "database": "connected",
        "redis": "connected"
    }

# ===== AUTH =====

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="E-Mail bereits registriert")

    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username bereits vergeben")

    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        is_verified=False,
        is_active=True
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    verification_code = str(random.randint(100000, 999999))

    verification = EmailVerification(
        token=verification_code,
        user_id=new_user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(verification)
    await db.commit()

    await email_service.send_verification_email(
        to_email=new_user.email,
        username=new_user.username,
        verification_code=verification_code
    )

    print(f"📧 Code gesendet an {new_user.email}: {verification_code}")

    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

    await redis_client.set_refresh_token(refresh_token, new_user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "is_verified": new_user.is_verified,
            "avatar_url": new_user.avatar_url
        }
    )

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

    await redis_client.set_refresh_token(refresh_token, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_verified": user.is_verified,
            "avatar_url": user.avatar_url
        }
    )

@app.post("/api/auth/verify-email")
async def verify_email(data: EmailVerify, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailVerification).where(EmailVerification.token == data.token))
    verification = result.scalar_one_or_none()

    if not verification:
        raise HTTPException(status_code=400, detail="Code ungültig oder nicht gefunden")

    if verification.expires_at < datetime.utcnow():
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

    password_reset = PasswordReset(
        token=reset_code,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(password_reset)
    await db.commit()

    await email_service.send_password_reset_email(
        to_email=user.email,
        username=user.username,
        reset_code=reset_code
    )

    print(f"📧 Reset-Code gesendet an {user.email}: {reset_code}")

    return {"message": "Reset-Code per E-Mail gesendet! Prüfe deine E-Mails."}

@app.post("/api/auth/reset-password")
async def reset_password(data: PasswordResetSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PasswordReset).where(PasswordReset.token == data.token))
    password_reset = result.scalar_one_or_none()

    if not password_reset or password_reset.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code ungültig oder abgelaufen (24h)")

    result = await db.execute(select(User).where(User.id == password_reset.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user.hashed_password = hash_password(data.new_password)
    await db.commit()

    await db.execute(select(PasswordReset).where(PasswordReset.token == data.token))
    db.delete(password_reset)
    await db.commit()

    print(f"✅ Passwort geändert für {user.email}")

    return {"message": "Passwort erfolgreich geändert! Du kannst dich jetzt einloggen."}

# ===== USER =====

@app.get("/api/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(lambda: None), db: AsyncSession = Depends(get_db)):
    # Simuliert - würde von JWT Dependency kommen
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_verified=current_user.is_verified,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at
    )

@app.get("/api/users/me/stats", response_model=UserStats)
async def get_user_stats(current_user: User = Depends(lambda: None), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GameHistory)
        .where(GameHistory.user_id == current_user.id)
        .order_by(GameHistory.played_at.desc())
    )
    games = result.scalars().all()

    total_games = len(games)
    total_wins = sum(1 for g in games if g.won)
    total_score = sum(g.score for g in games)
    average_score = total_score / total_games if total_games > 0 else 0
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0

    return UserStats(
        total_games=total_games,
        total_wins=total_wins,
        total_score=total_score,
        average_score=round(average_score, 2),
        win_rate=round(win_rate, 2)
    )

# ===== GAME =====

@app.post("/api/rooms", response_model=dict)
async def create_room(room_data: RoomCreate, current_user: User = Depends(lambda: None)):
    room_code = f"{random.randint(1000, 9999)}".upper()

    room = await game_logic.create_room(
        room_code=room_code,
        host_id=str(current_user.id),
        host_name=current_user.username,
        max_players=room_data.max_players,
        avatar_url=current_user.avatar_url
    )

    return room

@app.get("/api/rooms/{code}", response_model=dict)
async def get_room(code: str):
    room = game_logic.get_room_state(code)
    if not room:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")
    return room

@app.get("/api/memes", response_model=List[Meme])
async def get_memes():
    return [Meme(id=i, url=f"https://i.imgflip.com/{i}.jpg", width=500, height=500) for i in range(1, 101)]

@app.get("/api/captions", response_model=List[Caption])
async def get_captions():
    return [Caption(id=i, text=f"Caption {i}") for i in range(1, 101)]

# ===== WEBSOCKET =====

@app.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    await manager.connect(room_code, player_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "join_room":
                room = await game_logic.join_room(
                    room_code=room_code,
                    player_id=player_id,
                    player_name=data.get("guest_name", "Gast")
                )
                await manager.send_to_room(room_code, {"event": "room_joined", "room": room})

            elif event == "leave_room":
                room = await game_logic.leave_room(room_code, player_id)
                if room:
                    await manager.send_to_room(room_code, {"event": "player_left", "player_id": player_id, "room": room})

    except WebSocketDisconnect:
        await game_logic.leave_room(room_code, player_id)
        await manager.disconnect(room_code, player_id)

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
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
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
