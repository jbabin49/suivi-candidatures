"""
Tests de la gestion des comptes locaux : liste, creation, changement de
son propre mot de passe, suppression de son propre compte.

Le modele est plat (aucun role d'administrateur), mais chacun ne peut
agir que sur son propre compte. Les tests ci-dessous verifient surtout
cette limite, et l'isolation des donnees entre comptes.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.auth.local import hash_password, verify_password
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.main import app
from app.models import User

settings = get_settings()


@pytest.fixture
def db_propre() -> Iterator[None]:
    """
    Base sans aucun compte au depart, et videe a la sortie : la base
    temporaire est partagee par toute la session de test (conftest.py).
    """
    init_db()
    _vider()
    yield
    _vider()


def _vider() -> None:
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def _creer(identifiant: str, mot_de_passe: str = "motdepasse") -> int:
    """Insere un compte directement en base, et retourne son id."""
    db = SessionLocal()
    try:
        user = User(
            identifiant=identifiant,
            nom_affichage=identifiant,
            password_hash=hash_password(mot_de_passe),
        )
        db.add(user)
        db.commit()
        return user.id
    finally:
        db.close()


def _connecte(identifiant: str, mot_de_passe: str = "motdepasse") -> TestClient:
    c = TestClient(app, follow_redirects=False)
    reponse = c.post(
        "/login", data={"identifiant": identifiant, "password": mot_de_passe}
    )
    assert reponse.status_code == 303, reponse.status_code
    return c


def _identifiants() -> list[str]:
    db = SessionLocal()
    try:
        return sorted(u.identifiant for u in db.query(User).all())
    finally:
        db.close()


# Liste et creation


def test_comptes_exige_une_session(db_propre):
    _creer("alice")
    anonyme = TestClient(app, follow_redirects=False)
    assert anonyme.get("/comptes").status_code in (303, 401)


def test_liste_affiche_tous_les_comptes(db_propre):
    _creer("alice")
    _creer("bob")

    r = _connecte("alice").get("/comptes")
    assert r.status_code == 200
    assert "alice" in r.text
    assert "bob" in r.text


def test_creation_d_un_second_compte(db_propre):
    _creer("alice")

    r = _connecte("alice").post(
        "/comptes",
        data={
            "identifiant": "bob",
            "nom_affichage": "Bob",
            "password": "motdepasse",
            "password_confirm": "motdepasse",
        },
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/comptes"
    assert _identifiants() == ["alice", "bob"]

    # Le nouveau compte peut se connecter.
    assert _connecte("bob").get("/").status_code == 200


def test_creation_ne_change_pas_la_session_du_createur(db_propre):
    _creer("alice")
    client = _connecte("alice")
    client.post(
        "/comptes",
        data={
            "identifiant": "bob",
            "password": "motdepasse",
            "password_confirm": "motdepasse",
        },
    )

    # Toujours connecte en alice, pas bascule sur bob.
    r = client.get("/comptes")
    assert r.status_code == 200
    db = SessionLocal()
    try:
        alice = db.query(User).filter_by(identifiant="alice").one()
    finally:
        db.close()
    assert f"/comptes/{alice.id}/supprimer" in r.text


def test_creation_identifiant_deja_pris(db_propre):
    _creer("alice")

    r = _connecte("alice").post(
        "/comptes",
        data={
            "identifiant": "alice",
            "password": "motdepasse",
            "password_confirm": "motdepasse",
        },
    )
    assert r.status_code == 400
    assert "deja pris" in r.text
    assert _identifiants() == ["alice"]


def test_creation_nom_affichage_facultatif(db_propre):
    _creer("alice")
    _connecte("alice").post(
        "/comptes",
        data={
            "identifiant": "bob",
            "nom_affichage": "",
            "password": "motdepasse",
            "password_confirm": "motdepasse",
        },
    )
    db = SessionLocal()
    try:
        assert db.query(User).filter_by(identifiant="bob").one().nom_affichage == "bob"
    finally:
        db.close()


def test_creation_confirmation_differente(db_propre):
    _creer("alice")
    r = _connecte("alice").post(
        "/comptes",
        data={
            "identifiant": "bob",
            "password": "motdepasse",
            "password_confirm": "autrechose",
        },
    )
    assert r.status_code == 400
    assert _identifiants() == ["alice"]


def test_creation_mot_de_passe_trop_court(db_propre):
    _creer("alice")
    r = _connecte("alice").post(
        "/comptes",
        data={
            "identifiant": "bob",
            "password": "court",
            "password_confirm": "court",
        },
    )
    assert r.status_code == 400
    assert _identifiants() == ["alice"]


# Isolation des donnees entre comptes


def test_un_compte_ne_voit_pas_le_document_d_un_autre(db_propre):
    """
    Le filtrage par user_id est deja en place cote back-end ; ce test
    verrouille le comportement maintenant que l'interface permet de
    creer plusieurs comptes.
    """
    _creer("alice")
    _creer("bob")

    alice = _connecte("alice")
    r = alice.post(
        "/candidatures",
        data={
            "offre": "Dev",
            "entreprise": "ACME",
            "date_candidature": "2026-01-15",
            "statut": "envoyee",
        },
    )
    assert r.status_code == 303
    candidature_id = int(r.headers["location"].rstrip("/").split("/")[-1])

    r = alice.post(
        f"/candidatures/{candidature_id}/documents",
        data={"type": "cv"},
        files={"fichier": ("cv.pdf", io.BytesIO(b"%PDF-1.4 factice"), "application/pdf")},
    )
    assert r.status_code == 303

    db = SessionLocal()
    try:
        from app.models import Document

        document_id = db.query(Document).one().id
    finally:
        db.close()

    # Alice accede a son document.
    assert alice.get(f"/documents/{document_id}").status_code == 200
    # Bob non : 404, et non 403, pour ne pas confirmer son existence.
    assert _connecte("bob").get(f"/documents/{document_id}").status_code == 404


# Changement de son propre mot de passe


def test_changement_de_mot_de_passe(db_propre):
    _creer("alice", "ancienmotdepasse")
    client = _connecte("alice", "ancienmotdepasse")

    r = client.post(
        "/mon-compte/mot-de-passe",
        data={
            "password_actuel": "ancienmotdepasse",
            "password": "nouveaumotdepasse",
            "password_confirm": "nouveaumotdepasse",
        },
    )
    assert r.status_code == 200
    assert "modifie" in r.text

    # Le hash en base a bien change.
    db = SessionLocal()
    try:
        alice = db.query(User).filter_by(identifiant="alice").one()
        assert verify_password("nouveaumotdepasse", alice.password_hash) is True
        assert verify_password("ancienmotdepasse", alice.password_hash) is False
    finally:
        db.close()

    # Reconnexion avec le nouveau, et echec avec l'ancien.
    assert _connecte("alice", "nouveaumotdepasse").get("/").status_code == 200
    echec = TestClient(app, follow_redirects=False)
    assert (
        echec.post(
            "/login", data={"identifiant": "alice", "password": "ancienmotdepasse"}
        ).status_code
        == 401
    )


def test_changement_refuse_si_actuel_incorrect(db_propre):
    _creer("alice", "ancienmotdepasse")
    client = _connecte("alice", "ancienmotdepasse")

    r = client.post(
        "/mon-compte/mot-de-passe",
        data={
            "password_actuel": "FAUX",
            "password": "nouveaumotdepasse",
            "password_confirm": "nouveaumotdepasse",
        },
    )
    assert r.status_code == 400
    assert "actuel incorrect" in r.text

    # Rien n'a change : l'ancien fonctionne toujours.
    assert _connecte("alice", "ancienmotdepasse").get("/").status_code == 200


def test_changement_refuse_si_confirmation_differente(db_propre):
    _creer("alice")
    r = _connecte("alice").post(
        "/mon-compte/mot-de-passe",
        data={
            "password_actuel": "motdepasse",
            "password": "nouveaumotdepasse",
            "password_confirm": "autrechose",
        },
    )
    assert r.status_code == 400
    assert _connecte("alice").get("/").status_code == 200


def test_changement_refuse_si_trop_court(db_propre):
    _creer("alice")
    r = _connecte("alice").post(
        "/mon-compte/mot-de-passe",
        data={
            "password_actuel": "motdepasse",
            "password": "court",
            "password_confirm": "court",
        },
    )
    assert r.status_code == 400
    assert _connecte("alice").get("/").status_code == 200


def test_changement_n_affecte_que_son_compte(db_propre):
    """
    La cible n'est pas un parametre de la requete : aucun champ ne permet
    de viser un autre compte. Bob garde son mot de passe.
    """
    _creer("alice")
    _creer("bob", "motdepassebob")

    _connecte("alice").post(
        "/mon-compte/mot-de-passe",
        data={
            "password_actuel": "motdepasse",
            "password": "nouveaumotdepasse",
            "password_confirm": "nouveaumotdepasse",
        },
    )
    assert _connecte("bob", "motdepassebob").get("/").status_code == 200


# Suppression de son propre compte


def test_suppression_de_son_compte(db_propre):
    alice_id = _creer("alice")
    _creer("bob")

    client = _connecte("alice")

    # Un document televerse, pour verifier l'effacement du dossier.
    r = client.post(
        "/candidatures",
        data={
            "offre": "Dev",
            "entreprise": "ACME",
            "date_candidature": "2026-01-15",
            "statut": "envoyee",
        },
    )
    candidature_id = int(r.headers["location"].rstrip("/").split("/")[-1])
    client.post(
        f"/candidatures/{candidature_id}/documents",
        data={"type": "cv"},
        files={"fichier": ("cv.pdf", io.BytesIO(b"%PDF-1.4 factice"), "application/pdf")},
    )

    dossier = settings.uploads_dir / str(alice_id)
    assert dossier.is_dir(), "le televersement doit avoir cree le dossier"

    r = client.post(f"/comptes/{alice_id}/supprimer")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

    # Compte parti, bob intact.
    assert _identifiants() == ["bob"]
    # Cascade : plus aucune candidature ni document.
    db = SessionLocal()
    try:
        from app.models import Candidature, Document

        assert db.query(Candidature).count() == 0
        assert db.query(Document).count() == 0
    finally:
        db.close()
    # Dossier d'uploads efface du disque : la cascade SQLAlchemy ne
    # couvre que les lignes.
    assert not dossier.exists()
    # Session invalidee.
    assert client.get("/").status_code in (303, 401)


def test_suppression_refusee_si_dernier_compte(db_propre):
    alice_id = _creer("alice")
    client = _connecte("alice")

    r = client.post(f"/comptes/{alice_id}/supprimer")
    assert r.status_code == 400
    assert "dernier compte" in r.text
    # Rien supprime, session toujours valide.
    assert _identifiants() == ["alice"]
    assert client.get("/").status_code == 200


def test_suppression_du_compte_d_un_autre_refusee(db_propre):
    _creer("alice")
    bob_id = _creer("bob")

    r = _connecte("alice").post(f"/comptes/{bob_id}/supprimer")
    assert r.status_code == 404
    # Bob intact, et toujours capable de se connecter.
    assert _identifiants() == ["alice", "bob"]
    assert _connecte("bob").get("/").status_code == 200


def test_suppression_exige_une_session(db_propre):
    alice_id = _creer("alice")
    _creer("bob")

    anonyme = TestClient(app, follow_redirects=False)
    r = anonyme.post(f"/comptes/{alice_id}/supprimer")
    assert r.status_code in (303, 401)
    assert _identifiants() == ["alice", "bob"]


# Gabarits : conformite CSP


def test_pages_comptes_sans_script_inline(db_propre):
    """
    Aucun <script> porteur de contenu inline : la CSP de l'application
    est script-src 'self' strict.
    """
    _creer("alice")
    client = _connecte("alice")

    for url in ("/comptes", "/mon-compte/mot-de-passe"):
        texte = client.get(url).text
        # Tous les <script> de base.html ont un src, aucun n'est inline.
        for morceau in texte.split("<script")[1:]:
            ouverture = morceau.split(">")[0]
            assert "src=" in ouverture, f"{url} : <script{ouverture}> est inline"


def test_identifiant_hostile_echappe_dans_la_liste(db_propre):
    """
    Les identifiants sont saisis par les utilisateurs et reaffiches dans
    la liste : l'echappement Jinja2 doit s'appliquer (aucun | safe).
    """
    _creer("alice")
    _creer('<script>alert(1)</script>')

    texte = _connecte("alice").get("/comptes").text
    assert "<script>alert(1)</script>" not in texte
    assert "&lt;script&gt;" in texte
