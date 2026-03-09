from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from jose import jwt

from src.infrastructure.auth.jwt_handler import create_token, verify_token
from src.infrastructure.auth.password import hash_password, verify_password
from src.infrastructure.config import Settings


# ── Password hashing tests ─────────────────────────────────────────────


class TestHashPassword:
    def test_returns_bcrypt_hash(self):
        hashed = hash_password("my_secret")
        assert hashed != "my_secret"
        assert hashed.startswith("$2b$")

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # different salts


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = hash_password("correct_horse")
        assert verify_password("correct_horse", hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct_horse")
        assert verify_password("wrong_horse", hashed) is False

    def test_empty_password_rejected(self):
        hashed = hash_password("something")
        assert verify_password("", hashed) is False


# ── JWT tests ───────────────────────────────────────────────────────────


def _make_settings(**overrides: object) -> Settings:
    defaults = {
        "SECRET_KEY": "test-secret-key-for-jwt",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRATION_MINUTES": 60,
        "DATABASE_URL": "postgresql+asyncpg://x@localhost/x",
        "REDIS_URL": "redis://localhost:6379/0",
    }
    defaults.update(overrides)
    return Settings(**defaults)


class TestCreateToken:
    @patch("src.infrastructure.auth.jwt_handler.get_settings")
    def test_returns_valid_jwt(self, mock_settings):
        mock_settings.return_value = _make_settings()
        user_id = uuid4()
        token = create_token(user_id, "alice@example.com")

        payload = jwt.decode(token, "test-secret-key-for-jwt", algorithms=["HS256"])
        assert payload["sub"] == str(user_id)
        assert payload["email"] == "alice@example.com"
        assert "exp" in payload

    @patch("src.infrastructure.auth.jwt_handler.get_settings")
    def test_custom_expiration(self, mock_settings):
        mock_settings.return_value = _make_settings(JWT_EXPIRATION_MINUTES=30)
        token = create_token(uuid4(), "bob@example.com")

        payload = jwt.decode(
            token, "test-secret-key-for-jwt", algorithms=["HS256"]
        )
        assert "exp" in payload


class TestVerifyToken:
    @patch("src.infrastructure.auth.jwt_handler.get_settings")
    def test_valid_token(self, mock_settings):
        mock_settings.return_value = _make_settings()
        user_id = uuid4()
        token = create_token(user_id, "alice@example.com")

        payload = verify_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["email"] == "alice@example.com"

    @patch("src.infrastructure.auth.jwt_handler.get_settings")
    def test_expired_token(self, mock_settings):
        mock_settings.return_value = _make_settings(JWT_EXPIRATION_MINUTES=-1)
        token = create_token(uuid4(), "expired@example.com")

        with pytest.raises(Exception):
            verify_token(token)

    @patch("src.infrastructure.auth.jwt_handler.get_settings")
    def test_invalid_token(self, mock_settings):
        mock_settings.return_value = _make_settings()
        with pytest.raises(Exception):
            verify_token("this.is.not.a.valid.jwt")

    @patch("src.infrastructure.auth.jwt_handler.get_settings")
    def test_tampered_token(self, mock_settings):
        mock_settings.return_value = _make_settings()
        token = create_token(uuid4(), "alice@example.com")
        tampered = token[:-5] + "XXXXX"

        with pytest.raises(Exception):
            verify_token(tampered)

    @patch("src.infrastructure.auth.jwt_handler.get_settings")
    def test_wrong_secret_rejected(self, mock_settings):
        mock_settings.return_value = _make_settings()
        user_id = uuid4()
        # Create token with the real secret
        token = create_token(user_id, "alice@example.com")

        # Verify with different secret
        mock_settings.return_value = _make_settings(SECRET_KEY="wrong-secret")
        with pytest.raises(Exception):
            verify_token(token)
