"""
Gestion de la session utilisateur.

Le middleware de session (configure dans main.py) stocke un cookie signe
cote client contenant l'identifiant de l'utilisateur connecte. Ce module
fournit les fonctions pour ouvrir/fermer une session et la dependance
FastAPI qui resout l'utilisateur courant a partir du cookie.

Independant du mode d'authentification : auth locale et OIDC appellent
tous deux login_user une fois l'identite verifiee.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

# Cle sous laquelle l'id utilisateur est range dans la session.
SESSION_USER_ID = "user_id"


def login_user(request: Request, user: User) -> None:
    """Ouvre une session pour l'utilisateur donne."""
    request.session[SESSION_USER_ID] = user.id


def logout_user(request: Request) -> None:
    """Ferme la session courante."""
    request.session.clear()


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    """
    Dependance FastAPI : retourne l'utilisateur connecte ou leve une
    erreur 401 si aucune session valide. A utiliser sur toutes les routes
    protegees.
    """
    user_id = request.session.get(SESSION_USER_ID)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
        )

    user = db.get(User, user_id)
    if user is None:
        # Session pointant vers un compte supprime : on la nettoie.
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide",
        )

    return user


def get_optional_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    """
    Variante non bloquante : retourne l'utilisateur connecte ou None.
    Utile pour les pages accessibles connecte ou non (ex. page de login
    qui redirige si deja connecte).
    """
    user_id = request.session.get(SESSION_USER_ID)
    if user_id is None:
        return None
    return db.get(User, user_id)
