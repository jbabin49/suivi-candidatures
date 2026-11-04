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
from app.schemas import PremierCompte


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


FORMULAIRE_VALIDE = {
    "email": "premier@local",
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
    r = anonyme.post("/bienvenue", data={**FORMULAIRE_VALIDE, "email": "second@local"})
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


def test_bienvenue_refuse_un_email_invalide(client_base_vide):
    # Sans arobase : rejete cote serveur comme cote navigateur.
    r = client_base_vide.post("/bienvenue", data={**FORMULAIRE_VALIDE, "email": "pas-un-email"})
    assert r.status_code == 400
    assert _nombre_utilisateurs() == 0


def test_bienvenue_refuse_un_nom_affichage_vide(client_base_vide):
    r = client_base_vide.post("/bienvenue", data={**FORMULAIRE_VALIDE, "nom_affichage": "   "})
    assert r.status_code == 400
    assert _nombre_utilisateurs() == 0


def test_bienvenue_reaffiche_la_saisie_sans_les_mots_de_passe(client_base_vide):
    r = client_base_vide.post(
        "/bienvenue",
        data={**FORMULAIRE_VALIDE, "password_confirm": "autrechose"},
    )
    assert r.status_code == 400
    assert 'value="premier@local"' in r.text
    assert 'value="Premier compte"' in r.text
    # Les mots de passe ne repartent jamais vers le navigateur.
    assert "motdepasse" not in r.text
    assert "autrechose" not in r.text


# Regle de validation de l'adresse email


@pytest.mark.parametrize(
    "adresse",
    [
        "vous@example.com",
        # Pas de point exige dans le domaine : le navigateur l'accepte,
        # et c'est courant sur un reseau local.
        "premier@local",
        "admin@localhost",
        "vous@nas",
        # Caracteres speciaux autorises par le WHATWG dans la partie locale.
        "pre.nom+etiquette@example.co.uk",
        "a!#$%&'*+-/=?^_`{|}~b@example.com",
        # Tiret autorise a l'interieur d'un label de domaine.
        "vous@mon-serveur.example",
    ],
)
def test_email_accepte(adresse):
    assert PremierCompte(
        email=adresse,
        nom_affichage="Nom",
        password="motdepasse",
        password_confirm="motdepasse",
    ).email == adresse


@pytest.mark.parametrize(
    "adresse",
    [
        "",
        "pas-un-email",  # pas d'arobase
        "@example.com",  # partie locale vide
        "vous@",  # domaine vide
        "vous@@example.com",  # deux arobases
        "vous @example.com",  # espace dans la partie locale
        "vous@exa mple.com",  # espace dans le domaine
        "vous@-example.com",  # label de domaine commencant par un tiret
        "vous@example-.com",  # label de domaine finissant par un tiret
        "vous@exa_mple.com",  # souligne interdit dans le domaine
        "vous@example..com",  # label vide
        "vous@exa\nmple.com",  # retour a la ligne interne
    ],
)
def test_email_refuse(adresse):
    with pytest.raises(ValidationError):
        PremierCompte(
            email=adresse,
            nom_affichage="Nom",
            password="motdepasse",
            password_confirm="motdepasse",
        )


def test_email_est_trimme_avant_validation():
    """
    Les espaces autour de la saisie sont retires, pas refuses : un
    copier-coller depuis un client mail traine souvent une espace.
    """
    donnees = PremierCompte(
        email="  vous@example.com \n",
        nom_affichage="  Nom  ",
        password="motdepasse",
        password_confirm="motdepasse",
    )
    assert donnees.email == "vous@example.com"
    assert donnees.nom_affichage == "Nom"


def test_bienvenue_echappe_la_saisie_reaffichee(client_base_vide):
    """
    La saisie refusee est reaffichee dans l'attribut value du formulaire :
    elle doit passer par l'echappement automatique de Jinja. C'est la
    contrepartie de l'absence de | safe dans bienvenue.html.
    """
    hostile = '"><script>alert(1)</script>'
    r = client_base_vide.post(
        "/bienvenue",
        data={**FORMULAIRE_VALIDE, "email": "x", "nom_affichage": hostile},
    )
    assert r.status_code == 400
    # La balise ne ressort jamais telle quelle, et l'attribut n'est pas
    # ferme prematurement par le guillemet injecte.
    assert "<script>" not in r.text
    assert "&lt;script&gt;" in r.text
    assert "&#34;&gt;" in r.text or "&quot;&gt;" in r.text
