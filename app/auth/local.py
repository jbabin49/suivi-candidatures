"""
Authentification locale : comptes stockes en base, mots de passe hashes
avec argon2.

Actif lorsque AUTH_MODE=local. Fournit le hachage/verification des mots
de passe, les routes de connexion/deconnexion et l'ecran de premiere
connexion (/bienvenue), qui cree le premier compte quand la base est vide.
"""

from __future__ import annotations

from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import CompteCreate
from app.session import login_user, logout_user

router = APIRouter(tags=["auth"])

# Gabarits : meme dossier que celui monte par main.py. Resolu ici plutot
# qu'importe de main.py, qui importe ce module (dependance circulaire).
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Retourne le hash argon2 d'un mot de passe en clair."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifie un mot de passe en clair contre son hash. True si correct."""
    try:
        _hasher.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def authenticate(db: Session, identifiant: str, password: str) -> User | None:
    """
    Verifie les identifiants. Retourne l'utilisateur si valides, sinon
    None. Les comptes sans mot de passe (comptes OIDC) ne peuvent pas se
    connecter par cette voie.
    """
    user = db.scalar(select(User).where(User.identifiant == identifiant))
    if user is None or user.password_hash is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


@router.post("/login")
def login(
    request: Request,
    identifiant: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Traite le formulaire de connexion."""
    user = authenticate(db, identifiant.strip(), password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
        )
    login_user(request, user)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(request: Request):
    """Deconnecte l'utilisateur courant."""
    logout_user(request)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


def aucun_utilisateur(db: Session) -> bool:
    """Vraie si la base ne contient encore aucun compte."""
    return db.scalar(select(User.id).limit(1)) is None


def _premier_message(exc: ValidationError) -> str:
    """
    Extrait le premier message de validation lisible. Pydantic prefixe
    les ValueError levees dans un validateur par "Value error, " ; on le
    retire pour reafficher la phrase telle qu'ecrite dans schemas.py.
    """
    message = exc.errors()[0]["msg"]
    return message.removeprefix("Value error, ")


@router.get("/bienvenue", response_class=HTMLResponse)
def page_bienvenue(request: Request, db: Session = Depends(get_db)):
    """
    Ecran de premiere connexion : formulaire de creation du premier
    compte. Des qu'un compte existe, la page disparait au profit de
    /login.
    """
    if not aucun_utilisateur(db):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "bienvenue.html", {})


@router.post("/bienvenue", response_class=HTMLResponse)
def creer_premier_compte(
    request: Request,
    identifiant: str = Form(""),
    nom_affichage: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Cree le premier compte, puis ouvre directement sa session.

    C'est le seul endpoint de creation de compte accessible sans
    authentification : il n'est donc ouvert que tant que la base est
    vide. La verification est refaite ici, juste avant l'insertion, et
    pas seulement a l'affichage du formulaire (la page peut avoir ete
    chargee avant qu'un compte soit cree par ailleurs : variables
    ADMIN_*, script creer_utilisateur.py, autre onglet).
    """
    if not aucun_utilisateur(db):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        donnees = CompteCreate(
            identifiant=identifiant,
            nom_affichage=nom_affichage,
            password=password,
            password_confirm=password_confirm,
        )
    except ValidationError as exc:
        # Les mots de passe saisis ne sont jamais renvoyes au formulaire.
        return templates.TemplateResponse(
            request,
            "bienvenue.html",
            {
                "erreur": _premier_message(exc),
                "identifiant": identifiant,
                "nom_affichage": nom_affichage,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = creer_compte(db, donnees)
    login_user(request, user)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


def identifiant_deja_pris(db: Session, identifiant: str) -> bool:
    """Vraie si un compte porte deja cet identifiant."""
    return (
        db.scalar(select(User.id).where(User.identifiant == identifiant))
        is not None
    )


def creer_compte(db: Session, donnees: CompteCreate) -> User:
    """
    Insere un compte local a partir de donnees deja validees. Ne verifie
    pas l'unicite de l'identifiant : c'est a l'appelant de le faire, le
    message d'erreur n'etant pas le meme selon le formulaire d'origine.
    """
    user = User(
        identifiant=donnees.identifiant,
        nom_affichage=donnees.nom_affichage_effectif,
        password_hash=hash_password(donnees.password),
    )
    db.add(user)
    db.commit()
    return user
