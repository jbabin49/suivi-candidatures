"""
Tests de securite du televersement et de la consultation des documents.

Couvre les deux garde-fous poses contre la XSS stockee par fichier
televerse : la liste blanche d'extensions au depot, et le telechargement
force a la consultation.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Document


def _creer_candidature(client: TestClient) -> str:
    r = client.post(
        "/candidatures",
        data={
            "offre": "Technicien",
            "entreprise": "Ouest Reseaux",
            "date_candidature": "2026-10-20",
        },
    )
    assert r.status_code == 303
    return r.headers["location"].rsplit("/", 1)[-1]


def _televerser(client: TestClient, cid: str, nom: str, mime: str):
    return client.post(
        f"/candidatures/{cid}/documents",
        data={"type": "cv"},
        files={"fichier": (nom, b"contenu de test", mime)},
    )


def test_extension_hors_liste_blanche_refusee(client):
    """Un .html televerse puis consulte serait une XSS stockee : refus."""
    cid = _creer_candidature(client)
    r = _televerser(client, cid, "charge.html", "text/html")
    assert r.status_code == 400
    assert "non autorisee" in r.text


def test_extension_svg_refusee(client):
    """Le SVG porte du script : il ne doit pas passer non plus."""
    cid = _creer_candidature(client)
    assert _televerser(client, cid, "image.svg", "image/svg+xml").status_code == 400


def test_consultation_force_le_telechargement(client):
    """
    Un document legitime est servi en piece jointe, avec un type opaque
    et sans reniflage de contenu, quel que soit le type annonce au depot.
    """
    cid = _creer_candidature(client)
    # Type MIME volontairement mensonger a l'envoi : il ne doit ni etre
    # stocke ni etre reutilise pour servir le fichier.
    assert _televerser(client, cid, "cv.pdf", "text/html").status_code == 303

    db = SessionLocal()
    document = db.scalar(select(Document).order_by(Document.id.desc()))
    doc_id, mime_stocke = document.id, document.mime
    db.close()

    # Le mime du client ("text/html") a ete remplace par celui deduit de
    # l'extension validee.
    assert mime_stocke == "application/pdf"

    r = client.get(f"/documents/{doc_id}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"
    assert r.headers["content-disposition"].startswith("attachment")
    assert r.headers["x-content-type-options"] == "nosniff"
