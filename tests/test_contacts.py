"""
Tests de la validation du lien d'un contact.

Le lien est le seul champ rendu tel quel dans un attribut href : seuls
http et https doivent etre acceptes.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Contact


def _creer_candidature(client: TestClient) -> str:
    r = client.post(
        "/candidatures",
        data={
            "offre": "Technicien",
            "entreprise": "Acme",
            "date_candidature": "2026-10-20",
        },
    )
    return r.headers["location"].rsplit("/", 1)[-1]


def _ajouter_contact(client: TestClient, cid: str, lien: str):
    return client.post(
        f"/candidatures/{cid}/contacts",
        data={"nom": "Dupont", "lien": lien},
    )


def _dernier_lien_stocke() -> str | None:
    db = SessionLocal()
    contact = db.scalar(select(Contact).order_by(Contact.id.desc()))
    lien = contact.lien
    db.close()
    return lien


@pytest.mark.parametrize(
    "lien",
    [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",  # la casse du schema ne doit pas aider
        "java\nscript:alert(1)",  # ni les caracteres de controle
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
    ],
)
def test_schemas_dangereux_toujours_refuses(client, lien):
    """
    Un schema explicite dangereux n'est jamais complete ni reecrit : il
    est refuse, meme depuis que le prefixage automatique existe.
    """
    cid = _creer_candidature(client)
    r = _ajouter_contact(client, cid, lien)
    assert r.status_code == 400, lien
    assert "http://" in r.text


@pytest.mark.parametrize(
    "lien",
    ["https://www.linkedin.com/in/dupont", "http://exemple.test/page"],
)
def test_schema_explicite_conserve_tel_quel(client, lien):
    cid = _creer_candidature(client)
    assert _ajouter_contact(client, cid, lien).status_code == 303
    assert _dernier_lien_stocke() == lien


@pytest.mark.parametrize(
    ("saisi", "stocke"),
    [
        ("www.linkedin.com/in/dupont", "https://www.linkedin.com/in/dupont"),
        ("linkedin.com/in/dupont", "https://linkedin.com/in/dupont"),
        ("exemple.test/page", "https://exemple.test/page"),
        # URL relative au protocole : on fixe https, sans doubler les /.
        ("//exemple.test/page", "https://exemple.test/page"),
    ],
)
def test_prefixage_automatique_en_https(client, saisi, stocke):
    """Un domaine nu est accepte et complete en https://."""
    cid = _creer_candidature(client)
    assert _ajouter_contact(client, cid, saisi).status_code == 303
    assert _dernier_lien_stocke() == stocke


def test_lien_vide_accepte(client):
    """Le lien est optionnel : une chaine vide devient None, pas une 400."""
    cid = _creer_candidature(client)
    r = client.post(
        f"/candidatures/{cid}/contacts", data={"nom": "Dupont", "lien": ""}
    )
    assert r.status_code == 303


def test_lien_hostile_deja_en_base_non_rendu_en_href(client):
    """
    Un contact enregistre avant la validation (donc directement en base)
    ne doit pas produire de href javascript: a l'affichage.
    """
    cid = _creer_candidature(client)

    db = SessionLocal()
    db.add(
        Contact(
            candidature_id=int(cid),
            nom="Ancien",
            lien="javascript:alert(document.cookie)",
        )
    )
    db.commit()
    db.close()

    page = client.get(f"/candidatures/{cid}").text
    assert page.count("Ancien") == 1  # le contact est bien affiche
    assert "javascript:" not in page  # mais son lien n'est pas rendu
    assert 'href="javascript' not in page
