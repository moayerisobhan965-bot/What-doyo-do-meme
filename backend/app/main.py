"""
Main Application
FastAPI + Socket.io + REST API
E-Mail Verifizierung wie GitHub/Google
"""
import json
import random
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import init_db
from app.game.redis_client import redis_client
from app.game.game_logic import game_logic
from app.game.socket_handlers import handle_socket_events, manager
from app.auth.jwt import (
    get_current_user, get_current_active_user,
    create_access_token, create_refresh_token,
    oauth2_scheme
)
from app.auth.password import hash_password, verify_password
from app.email.service import email_service
from app.models import User, EmailVerification, PasswordReset
from app.schemas import (
    UserRegister, UserLogin, TokenResponse,
    EmailVerify, PasswordForgot, PasswordReset as PasswordResetSchema,
    UserResponse, UserUpdate, UserStats,
    RoomCreate, RoomJoin, RoomState,
    Caption, Meme
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi_socketio import SocketIO


settings = get_settings()


# ===== LIFE CYCLE =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle Manager für App-Start und -Stop"""
    # Startup
    print("🚀 Starting What Meme Backend...")
    print(f"📦 Environment: {settings.APP_ENV}")
    print(f"🔧 Debug Mode: {settings.DEBUG}")

    # Datenbank initialisieren
    await init_db()
    print("✅ Database initialized")

    # Redis verbinden
    await redis_client.connect()
    print("✅ Redis connected")

    yield

    # Shutdown
    print("🛑 Shutting down...")
    await redis_client.disconnect()
    print("✅ Redis disconnected")


# ===== APP SETUP =====

app = FastAPI(
    title=settings.APP_NAME,
    description="Multiplayer Meme Game Backend",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware (für SSL)
if settings.ENABLE_SSL:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["whatmeme.de", "www.whatmeme.de", "localhost"]
    )

# ===== SOCKET.IO =====

socket_io = SocketIO(
    app,
    cors_allowed_origins=settings.cors_origins_list,
    async_mode="asgi",
    ping_timeout=60,
    ping_interval=25,
    logger=False,
    engineio_logger=False,
)


# ===== STATIC FILES =====
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/memes", StaticFiles(directory="app/static/memes"), name="memes")


# ===== MEME DATA =====
MEMES_DATA = [
    Meme(id=i, url=f"https://i.imgflip.com/{i}.jpg", width=500, height=500)
    for i in range(1, 101)
]

CAPTIONS_DATA = [
    Caption(id=i, text=f"Caption {i}")
    for i in range(1, 101)
]


# ===== HEALTH CHECK =====

@app.get("/health")
async def health_check():
    """Health Check Endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "env": settings.APP_ENV,
        "database": "connected",
        "redis": "connected"
    }


# ===== AUTH ENDPOINTS =====

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Registrierung - Code wird per E-Mail gesendet
    Benutzer gibt Code im Frontend ein
    """
    # Prüfen ob E-Mail schon existiert
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-Mail bereits registriert"
        )

    # Prüfen ob Username schon existiert
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username bereits vergeben"
        )

    # Benutzer erstellen (NICHT verifiziert!)
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        is_verified=False,  # WICHTIG: Nicht verifiziert
        is_active=True
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # CODE GENERIEREN
    verification_code = str(random.randint(100000, 999999))
    # Beispiel: "456789"

    # CODE IN DATABASE SPEICHERN
    verification = EmailVerification(
        token=verification_code,
        user_id=new_user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(verification)
    await db.commit()

    # 📧 E-Mail MIT CODE SENDEN
    await email_service.send_verification_email(
        to_email=new_user.email,
        username=new_user.username,
        verification_code=verification_code
    )

    print(f"📧 Code gesendet an {new_user.email}: {verification_code}")

    # JWT Token erstellen
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

    # Refresh Token in Redis speichern
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
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login"""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Anmeldeinformationen"
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Benutzer ist inaktiv")

    # Prüfen ob E-Mail verifiziert
    if not user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Bitte verifiziere zuerst deine E-Mail. Code wurde per E-Mail gesendet!"
        )

    # JWT Token erstellen
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Refresh Token in Redis speichern
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
async def verify_email(
    data: EmailVerify,
    db: AsyncSession = Depends(get_db)
):
    """
    Code verifizieren - Benutzer gibt Code ein
    Wie bei GitHub/Google
    """
    # CODE AUS DATABASE LADEN
    result = await db.execute(
        select(EmailVerification).where(EmailVerification.token == data.token)
    )
    verification = result.scalar_one_or_none()

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code ungültig oder nicht gefunden"
        )

    if verification.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code ist abgelaufen (24h)"
        )

    # USER VERIFIZIEREN
    result = await db.execute(select(User).where(User.id == verification.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user.is_verified = True
    await db.commit()

    print(f"✅ E-Mail verifiziert für {user.email}")

    return {"message": "E-Mail erfolgreich verifiziert! Du kannst dich jetzt einloggen."}


@app.post("/api/auth/forgot-password")
async def forgot_password(
    data: PasswordForgot,
    db: AsyncSession = Depends(get_db)
):
    """
    Passwort vergessen - Code wird per E-Mail gesendet
    Benutzer gibt Code ein
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        # Nicht verraten dass User existiert
        return {"message": "Wenn diese E-Mail registriert ist, erhältst du einen Reset-Code"}

    # RESET CODE GENERIEREN
    reset_code = str(random.randint(100000, 999999))
    # Beispiel: "789123"

    # CODE IN DATABASE SPEICHERN
    password_reset = PasswordReset(
        token=reset_code,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(password_reset)
    await db.commit()

    # 📧 E-Mail MIT CODE SENDEN
    await email_service.send_password_reset_email(
        to_email=user.email,
        username=user.username,
        reset_code=reset_code
    )

    print(f"📧 Reset-Code gesendet an {user.email}: {reset_code}")

    return {"message": "Reset-Code per E-Mail gesendet! Prüfe deine E-Mails."}


@app.post("/api/auth/reset-password")
async def reset_password(
    data: PasswordResetSchema,
    db: AsyncSession = Depends(get_db)
):
    """
    Passwort zurücksetzen - Benutzer gibt Code ein
    Wie bei GitHub/Google
    """
    # CODE AUS DATABASE LADEN
    result = await db.execute(
        select(PasswordReset).where(PasswordReset.token == data.token)
    )
    password_reset = result.scalar_one_or_none()

    if not password_reset or password_reset.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code ungültig oder abgelaufen (24h)"
        )

    # USER FUNDEN
    result = await db.execute(select(User).where(User.id == password_reset.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    # PASSWORT ÄNDERN
    user.hashed_password = hash_password(data.new_password)
    await db.commit()

    # CODE LÖSCHEN
    await db.execute(
        select(PasswordReset).where(PasswordReset.token == data.token)
    )
    db.delete(password_reset)
    await db.commit()

    print(f"✅ Passwort geändert für {user.email}")

    return {"message": "Passwort erfolgreich geändert! Du kannst dich jetzt einloggen."}


# ===== USER ENDPOINTS =====

@app.get("/api/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Eigene User-Info"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_verified=current_user.is_verified,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at
    )


@app.patch("/api/users/me", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """User-Info aktualisieren"""
    if user_data.username:
        # Prüfen ob Username schon vergeben
        result = await db.execute(select(User).where(User.username == user_data.username))
        if result.scalar_one_or_none() and result.scalar_one_or_none().id != current_user.id:
            raise HTTPException(status_code=409, detail="Username bereits vergeben")
        current_user.username = user_data.username

    if user_data.avatar_url:
        current_user.avatar_url = user_data.avatar_url

    await db.commit()
    await db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_verified=current_user.is_verified,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at
    )


@app.get("/api/users/me/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """User-Statistiken"""
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


# ===== GAME ENDPOINTS =====

@app.post("/api/rooms", response_model=RoomState)
async def create_room(
    room_data: RoomCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Raum erstellen"""
    # 4-stelliger Code generieren
    room_code = f"{random.randint(1000, 9999)}".upper()

    room = await game_logic.create_room(
        room_code=room_code,
        host_id=str(current_user.id),
        host_name=current_user.username,
        max_players=room_data.max_players,
        avatar_url=current_user.avatar_url
    )

    return room


@app.get("/api/rooms/{code}", response_model=RoomState)
async def get_room(code: str):
    """Raum abfragen"""
    room = game_logic.get_room_state(code)
    if not room:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")
    return room


@app.get("/api/memes", response_model=List[Meme])
async def get_memes():
    """Alle Memes abfragen"""
    return MEMES_DATA


@app.get("/api/captions", response_model=List[Caption])
async def get_captions():
    """Alle Textkarten abfragen"""
    return CAPTIONS_DATA


# ===== WEBSOCKET ENDPOINTS =====

@app.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    player_id: str,
    token: str = None
):
    """WebSocket Endpoint für Socket.io"""
    user_data = None

    # Token prüfen
    if token:
        from app.auth.jwt import get_current_user as get_current_user_from_token
        from sqlalchemy.ext.asyncio import AsyncSession

        # Simulieren der Dependency Injection
        from fastapi import Request
        from app.database import get_db

        # Token validieren
        try:
            from jose import jwt
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")

            if user_id:
                db = AsyncSession(get_db())
                result = await db.execute(select(User).where(User.id == int(user_id)))
                user = result.scalar_one_or_none()

                if user:
                    user_data = {
                        "id": user.id,
                        "username": user.username,
                        "avatar_url": user.avatar_url
                    }
        except:
            pass

    # Socket.io Handler aufrufen
    await handle_socket_events(websocket, room_code, player_id, user_data)


# ===== INDEX PAGE =====

@app.get("/", response_class=HTMLResponse)
async def index():
    """Index Page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>What Meme</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
            }
            h1 {
                color: #4CAF50;
            }
            a {
                color: #4CAF50;
                text-decoration: none;
            }
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
    uvicorn.run(
        "app/main.py:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
