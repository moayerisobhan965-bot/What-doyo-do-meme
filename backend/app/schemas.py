"""
Pydantic Schemas
Validierung und Serialisierung von Daten
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator


# ===== AUTH SCHEMAS =====

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


class TokenRefresh(BaseModel):
    refresh_token: str


class EmailVerify(BaseModel):
    token: str


class PasswordForgot(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)


# ===== USER SCHEMAS =====

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_verified: bool
    avatar_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserStats(BaseModel):
    total_games: int
    total_wins: int
    total_score: int
    average_score: float
    win_rate: float


class UserWithStats(UserResponse):
    stats: UserStats


# ===== GAME SCHEMAS =====

class RoomCreate(BaseModel):
    max_players: int = Field(10, ge=2, le=10)


class RoomJoin(BaseModel):
    code: str = Field(..., min_length=4, max_length=4, pattern=r'^[A-Z0-9]+$')
    guest_name: Optional[str] = Field(None, min_length=1, max_length=50)


class GameAction(BaseModel):
    pass


class SubmitMeme(BaseModel):
    meme_id: int


class VoteMeme(BaseModel):
    player_id: int


# ===== GAME STATE SCHEMAS =====

class Player(BaseModel):
    id: str
    name: str
    is_host: bool = False
    is_guest: bool = False
    is_ready: bool = True
    avatar_url: Optional[str]
    score: int = 0


class RoomState(BaseModel):
    code: str
    state: str  # lobby, playing, voting, result, game_over
    host_id: str
    players: List[Player]
    current_round: int = 0
    current_player_index: int = 0
    drawn_caption: Optional[str] = None
    submissions: Dict[str, int] = {}  # player_id -> meme_id
    votes: Dict[str, int] = {}  # player_id -> vote_count
    winner_id: Optional[str] = None
    game_over: bool = False
    winner_score: Optional[int] = None


class Meme(BaseModel):
    id: int
    url: str
    thumbnail_url: Optional[str] = None
    width: int
    height: int


class Caption(BaseModel):
    id: int
    text: str


class RoundResult(BaseModel):
    winner_id: str
    winner_name: str
    meme_id: int
    meme_url: str
    votes: Dict[str, int]
    total_votes: int


class GameOver(BaseModel):
    winner_id: str
    winner_name: str
    scores: Dict[str, int]
    game_over: bool = True
