"""Tests du cycle de vie d'une candidature et de l'isolation par utilisateur."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.auth.local import hash_password
from app.database import SessionLocal
from app.main import app
from app.models import User


def _creer(client: TestClient) -> str:
    r = client.post(
        "/candidatures",
        data={
            "offre": "Admin sys",
            "entreprise": "Armoni",
            "ville": "Cholet",
            "date_candidature": "2026-10-08",
            "source": "Indeed",
        },
    )
    assert r.status_code == 303
    return r.headers["location"].rsplit("/", 1)[-1]


def test_acces_protege_sans_login():
    c = TestClient(app, follow_redirects=False)
    assert c.get("/").status_code == 401


def test_creation_et_detail(client):
    cid = _creer(client)
    r = client.get(f"/candidatures/{cid}")
    assert r.status_code == 200
    assert "Armoni" in r.text


def test_export_csv(client):
    _creer(client)
    r = client.get("/export.csv")
    assert r.status_code == 200
    assert "Armoni" in r.text


def test_isolation_entre_utilisateurs(client):
    cid = _creer(client)

    db = SessionLocal()
    if db.query(User).filter_by(email="autre@local").first() is None:
        db.add(
            User(
                email="autre@local",
                nom_affichage="Autre",
                password_hash=hash_password("x"),
            )
        )
        db.commit()
    db.close()

    autre = TestClient(app, follow_redirects=False)
    autre.post("/login", data={"email": "autre@local", "password": "x"})
    # La candidature d'un autre utilisateur est invisible (404, pas 403).
    assert autre.get(f"/candidatures/{cid}").status_code == 404
