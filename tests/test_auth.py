"""Tests de l'authentification locale (hachage, verification, login)."""

from __future__ import annotations

from app.auth.local import hash_password, verify_password


def test_hash_et_verification():
    h = hash_password("motdepasse")
    assert h != "motdepasse"  # jamais stocke en clair
    assert verify_password("motdepasse", h) is True
    assert verify_password("mauvais", h) is False


def test_login_identifiants_invalides(client):
    # Le client fixture est deja connecte ; on teste un echec explicite.
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app, follow_redirects=False)
    r = c.post("/login", data={"email": "test@local", "password": "FAUX"})
    assert r.status_code == 401
