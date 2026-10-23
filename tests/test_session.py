"""
Tests des attributs du cookie de session.

Le cookie est la seule chose qui porte l'authentification : ses drapeaux
sont donc verifies explicitement, pour qu'une mise a jour de Starlette ne
puisse pas les relacher silencieusement.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def _cookie_de_session(reponse) -> str:
    entetes = [
        v
        for k, v in reponse.headers.items()
        if k.lower() == "set-cookie" and v.startswith("session=")
    ]
    assert entetes, "aucun cookie de session pose"
    return entetes[0]


def test_drapeaux_du_cookie_de_session():
    c = TestClient(app, follow_redirects=False)
    r = c.post("/login", data={"email": "test@local", "password": "motdepasse"})
    cookie = _cookie_de_session(r).lower()

    assert "httponly" in cookie  # inaccessible au JavaScript
    assert "samesite=lax" in cookie  # protection anti-CSRF
    assert "path=/" in cookie
    # Duree de vie bornee, et bien plus courte que les 14 jours par defaut.
    assert f"max-age={get_settings().session_max_age}" in cookie
    assert get_settings().session_max_age <= 24 * 60 * 60


def test_secure_absent_en_http_par_defaut():
    """
    Par defaut l'application est servie en HTTP local : un cookie Secure
    serait ignore par le navigateur, donc le drapeau ne doit pas y etre.
    """
    assert get_settings().session_cookie_secure is False
    c = TestClient(app, follow_redirects=False)
    r = c.post("/login", data={"email": "test@local", "password": "motdepasse"})
    assert "secure" not in _cookie_de_session(r).lower()


def test_secure_activable_par_variable_d_environnement(monkeypatch):
    """SESSION_COOKIE_SECURE=true doit bien etre lu comme un booleen."""
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("SESSION_MAX_AGE", "3600")
    # Instance neuve : get_settings() est mis en cache pour le processus.
    parametres = Settings()
    assert parametres.session_cookie_secure is True
    assert parametres.session_max_age == 3600
