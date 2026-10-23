"""
Fixtures de test partagees.

Chaque test tourne sur une base SQLite temporaire isolee et un client
HTTP deja authentifie, pour ne pas reecrire le login partout.
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Base temporaire definie avant tout import de l'application, pour que la
# configuration pointe dessus des son chargement.
_tmpdir = tempfile.mkdtemp(prefix="candidatures-test-")
os.environ["DATA_DIR"] = _tmpdir
os.environ["AUTH_MODE"] = "local"

from fastapi.testclient import TestClient  # noqa: E402

from app.auth.local import hash_password  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """Client HTTP connecte avec un utilisateur de test."""
    init_db()
    db = SessionLocal()
    if db.query(User).filter_by(email="test@local").first() is None:
        db.add(
            User(
                email="test@local",
                nom_affichage="Test",
                password_hash=hash_password("motdepasse"),
            )
        )
        db.commit()
    db.close()

    c = TestClient(app, follow_redirects=False)
    c.post("/login", data={"email": "test@local", "password": "motdepasse"})
    return c
