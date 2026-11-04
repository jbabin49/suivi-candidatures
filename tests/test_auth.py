"""
Tests de l'authentification locale : hachage, verification, login, et
ecran de premiere connexion (/bienvenue).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth.local import hash_password, verify_password
from app.database import SessionLocal, init_db
from app.main import app
from app.models import User
from app.schemas import CompteCreate


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
    r = c.post("/login", data={"identifiant": "test", "password": "FAUX"})
    assert r.status_code == 401


# Ecran de premiere connexion (/bienvenue)


@pytest.fixture
def client_base_vide() -> Iterator[TestClient]:
    """
    Client non authentifie sur une base sans aucun utilisateur.

    La base temporaire est partagee par toute la session de test (voir
    conftest.py) et la fixture client y cree test@local : il faut donc
    vider explicitement la table pour retrouver l'etat "premier
    lancement", et la revider ensuite pour ne pas laisser de compte aux
    tests suivants.
    """
    init_db()
    _vider_utilisateurs()
    yield TestClient(app, follow_redirects=False)
    _vider_utilisateurs()


def _vider_utilisateurs() -> None:
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def _nombre_utilisateurs() -> int:
    db = SessionLocal()
    try:
        return db.query(User).count()
    finally:
        db.close()


def _identifiants() -> list[str]:
    db = SessionLocal()
    try:
        return sorted(u.identifiant for u in db.query(User).all())
    finally:
        db.close()


FORMULAIRE_VALIDE = {
    "identifiant": "premier",
    "nom_affichage": "Premier compte",
    "password": "motdepasse",
    "password_confirm": "motdepasse",
}


def test_login_redirige_vers_bienvenue_si_base_vide(client_base_vide):
    r = client_base_vide.get("/login")
    assert r.status_code == 307
    assert r.headers["location"] == "/bienvenue"


def test_bienvenue_affiche_le_formulaire_si_base_vide(client_base_vide):
    r = client_base_vide.get("/bienvenue")
    assert r.status_code == 200
    assert 'action="/bienvenue"' in r.text
    assert 'name="password_confirm"' in r.text


def test_bienvenue_cree_le_premier_compte_et_ouvre_la_session(client_base_vide):
    r = client_base_vide.post("/bienvenue", data=FORMULAIRE_VALIDE)
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    assert _nombre_utilisateurs() == 1

    # Session ouverte : une page protegee repond sans rediriger vers /login.
    assert client_base_vide.get("/").status_code == 200


def test_bienvenue_redirige_vers_login_une_fois_le_compte_cree(client_base_vide):
    client_base_vide.post("/bienvenue", data=FORMULAIRE_VALIDE)

    # Nouveau client : sans session, la page ne doit plus etre proposee.
    anonyme = TestClient(app, follow_redirects=False)
    r = anonyme.get("/bienvenue")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    # Et /login redevient la page de connexion normale.
    assert anonyme.get("/login").status_code == 200


def test_bienvenue_refuse_un_second_compte(client):
    """
    Garde-fou central : l'endpoint est sans authentification, il ne doit
    rien creer des qu'un compte existe. La fixture client en a cree un.
    """
    avant = _nombre_utilisateurs()
    assert avant >= 1

    anonyme = TestClient(app, follow_redirects=False)
    r = anonyme.post("/bienvenue", data={**FORMULAIRE_VALIDE, "identifiant": "second"})
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    assert _nombre_utilisateurs() == avant


def test_bienvenue_refuse_une_confirmation_differente(client_base_vide):
    r = client_base_vide.post(
        "/bienvenue",
        data={**FORMULAIRE_VALIDE, "password_confirm": "autrechose"},
    )
    assert r.status_code == 400
    assert "correspondent pas" in r.text
    assert _nombre_utilisateurs() == 0


def test_bienvenue_refuse_un_mot_de_passe_trop_court(client_base_vide):
    r = client_base_vide.post(
        "/bienvenue",
        data={**FORMULAIRE_VALIDE, "password": "court", "password_confirm": "court"},
    )
    assert r.status_code == 400
    assert "8 caracteres" in r.text
    assert _nombre_utilisateurs() == 0


def test_bienvenue_refuse_un_identifiant_vide(client_base_vide):
    r = client_base_vide.post("/bienvenue", data={**FORMULAIRE_VALIDE, "identifiant": "   "})
    assert r.status_code == 400
    assert _nombre_utilisateurs() == 0


def test_bienvenue_accepte_un_identifiant_non_email(client_base_vide):
    """
    Tout l'objet du passage de l'email a l'identifiant libre : un simple
    nom doit suffire.
    """
    r = client_base_vide.post("/bienvenue", data={**FORMULAIRE_VALIDE, "identifiant": "julien"})
    assert r.status_code == 303
    assert _identifiants() == ["julien"]


def test_bienvenue_nom_affichage_facultatif(client_base_vide):
    """Nom affiche vide : l'identifiant est repris comme nom."""
    r = client_base_vide.post(
        "/bienvenue",
        data={**FORMULAIRE_VALIDE, "identifiant": "julien", "nom_affichage": ""},
    )
    assert r.status_code == 303

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(identifiant="julien").one()
        assert user.nom_affichage == "julien"
    finally:
        db.close()


def test_bienvenue_reaffiche_la_saisie_sans_les_mots_de_passe(client_base_vide):
    r = client_base_vide.post(
        "/bienvenue",
        data={**FORMULAIRE_VALIDE, "password_confirm": "autrechose"},
    )
    assert r.status_code == 400
    assert 'value="premier"' in r.text
    assert 'value="Premier compte"' in r.text
    # Les mots de passe ne repartent jamais vers le navigateur.
    assert "motdepasse" not in r.text
    assert "autrechose" not in r.text


# Regle de validation de l'identifiant
#
# Chaine libre : aucun format impose, contrairement a l'ancien identifiant
# qui devait etre une adresse email. Seules les bornes qui protegent la
# base sont verifiees.


@pytest.mark.parametrize(
    "valeur",
    [
        "julien",
        "j",
        "vous@example.com",  # une adresse reste un identifiant valide
        "Jean-Luc Picard",  # espaces et ponctuation admis
        "utilisateur_42",
        "x" * 255,  # borne haute exacte
    ],
)
def test_identifiant_accepte(valeur):
    assert CompteCreate(
        identifiant=valeur,
        password="motdepasse",
        password_confirm="motdepasse",
    ).identifiant == valeur


@pytest.mark.parametrize(
    "valeur",
    [
        "",
        "   ",  # vide apres trim
        "\t\n",
        "x" * 256,  # depasse la longueur de la colonne
    ],
)
def test_identifiant_refuse(valeur):
    with pytest.raises(ValidationError):
        CompteCreate(
            identifiant=valeur,
            password="motdepasse",
            password_confirm="motdepasse",
        )


def test_identifiant_est_trimme():
    donnees = CompteCreate(
        identifiant="  julien  ",
        nom_affichage="  Julien  ",
        password="motdepasse",
        password_confirm="motdepasse",
    )
    assert donnees.identifiant == "julien"
    assert donnees.nom_affichage == "Julien"


def test_nom_affichage_effectif_reprend_l_identifiant():
    donnees = CompteCreate(
        identifiant="julien",
        password="motdepasse",
        password_confirm="motdepasse",
    )
    assert donnees.nom_affichage_effectif == "julien"


def test_login_avec_un_identifiant_non_email(client_base_vide):
    """
    Bout en bout : creation d'un compte "julien", deconnexion, puis
    reconnexion avec ce meme identifiant non-email.
    """
    client_base_vide.post(
        "/bienvenue", data={**FORMULAIRE_VALIDE, "identifiant": "julien"}
    )

    anonyme = TestClient(app, follow_redirects=False)
    r = anonyme.post("/login", data={"identifiant": "julien", "password": "motdepasse"})
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    assert anonyme.get("/").status_code == 200


def test_login_est_trimme(client_base_vide):
    """Une espace collee avant l'identifiant ne doit pas bloquer l'entree."""
    client_base_vide.post(
        "/bienvenue", data={**FORMULAIRE_VALIDE, "identifiant": "julien"}
    )

    anonyme = TestClient(app, follow_redirects=False)
    r = anonyme.post(
        "/login", data={"identifiant": "  julien  ", "password": "motdepasse"}
    )
    assert r.status_code == 303


def test_bienvenue_echappe_la_saisie_reaffichee(client_base_vide):
    """
    La saisie refusee est reaffichee dans l'attribut value du formulaire :
    elle doit passer par l'echappement automatique de Jinja. C'est la
    contrepartie de l'absence de | safe dans bienvenue.html.
    """
    hostile = '"><script>alert(1)</script>'
    r = client_base_vide.post(
        "/bienvenue",
        data={**FORMULAIRE_VALIDE, "identifiant": hostile, "password": "court"},
    )
    assert r.status_code == 400
    # La balise ne ressort jamais telle quelle, et l'attribut n'est pas
    # ferme prematurement par le guillemet injecte.
    assert "<script>" not in r.text
    assert "&lt;script&gt;" in r.text
    assert "&#34;&gt;" in r.text or "&quot;&gt;" in r.text
