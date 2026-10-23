"""
Authentification locale : comptes stockes en base, mots de passe hashes
avec argon2.

Actif lorsque AUTH_MODE=local. Fournit le hachage/verification des mots
de passe et les routes de connexion/deconnexion.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.session import login_user, logout_user

router = APIRouter(tags=["auth"])

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


def authenticate(db: Session, email: str, password: str) -> User | None:
    """
    Verifie les identifiants. Retourne l'utilisateur si valides, sinon
    None. Les comptes sans mot de passe (comptes OIDC) ne peuvent pas se
    connecter par cette voie.
    """
    user = db.scalar(select(User).where(User.email == email))
    if user is None or user.password_hash is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Traite le formulaire de connexion."""
    user = authenticate(db, email, password)
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
