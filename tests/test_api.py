"""
API Tests
Testet die REST API Endpunkte
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthCheck:
    """Testet Health Check Endpoint"""

    def test_health_check(self):
        """Gesundheitscheck sollte 200 zurückgeben"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "What Meme"
        assert "database" in data
        assert "redis" in data


class TestAuthEndpoints:
    """Testet Auth Endpoints"""

    def test_register_missing_fields(self):
        """Registrierung ohne E-Mail sollte 422 zurückgeben"""
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "password": "password123"
        })
        assert response.status_code == 422

    def test_register_invalid_email(self):
        """Registrierung mit ungültiger E-Mail sollte 422 zurückgeben"""
        response = client.post("/api/auth/register", json={
            "email": "invalid-email",
            "username": "testuser",
            "password": "password123"
        })
        assert response.status_code == 422

    def test_register_invalid_password(self):
        """Registrierung mit zu kurzem Passwort sollte 422 zurückgeben"""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "short"
        })
        assert response.status_code == 422

    def test_register_invalid_username(self):
        """Registrierung mit ungültigem Username sollte 422 zurückgeben"""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "username": "ab",
            "password": "password123"
        })
        assert response.status_code == 422


class TestGameEndpoints:
    """Testet Game Endpoints"""

    def test_get_memes(self):
        """Memes sollten geladen werden können"""
        response = client.get("/api/memes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "url" in data[0]

    def test_get_captions(self):
        """Textkarten sollten geladen werden können"""
        response = client.get("/api/captions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "text" in data[0]

    def test_create_room(self):
        """Raum erstellen sollte 401 zurückgeben (nicht authentifiziert)"""
        response = client.post("/api/rooms", json={"max_players": 10})
        assert response.status_code == 401

    def test_get_rooms(self):
        """Räume abfragen sollte 401 zurückgeben (nicht authentifiziert)"""
        response = client.get("/api/rooms/1234")
        assert response.status_code == 401


class TestUserEndpoints:
    """Testet User Endpoints"""

    def test_get_user_me(self):
        """Eigene Daten abfragen sollte 401 zurückgeben (nicht authentifiziert)"""
        response = client.get("/api/users/me")
        assert response.status_code == 401

    def test_update_user(self):
        """Profil aktualisieren sollte 401 zurückgeben (nicht authentifiziert)"""
        response = client.patch("/api/users/me", json={"username": "newname"})
        assert response.status_code == 401

    def test_get_user_stats(self):
        """Statistiken abfragen sollte 401 zurückgeben (nicht authentifiziert)"""
        response = client.get("/api/users/me/stats")
        assert response.status_code == 401
