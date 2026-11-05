"""
Database Models
SQLAlchemy Models für User, GameHistory, etc.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """Benutzer-Modell"""
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

    # Beziehungen
    game_history = relationship("GameHistory", back_populates="user", cascade="all, delete-orphan")
    friends = relationship("Friendship", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_email_verified", "email", "is_verified"),
    )


class EmailVerification(Base):
    """E-Mail Verifizierungs-Tokens"""
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="email_verifications")


class PasswordReset(Base):
    """Passwort-Reset-Tokens"""
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="password_resets")


class GameHistory(Base):
    """Spiel-Historie für Statistiken"""
    __tablename__ = "game_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_code = Column(String(10), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    won = Column(Boolean, nullable=False)
    total_players = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    played_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="game_history")

    __table_args__ = (
        Index("idx_user_played", "user_id", "played_at"),
    )


class Friendship(Base):
    """Freundesliste"""
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="friends", foreign_keys=[user_id])
    friend = relationship("User", back_populates="friends", foreign_keys=[friend_id])

    __table_args__ = (
        Index("idx_friendship", "user_id", "friend_id", unique=True),
    )


class Room(Base):
    """Spiel-Räume (für zukünftige Erweiterungen)"""
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    max_players = Column(Integer, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
