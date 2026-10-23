"""
Routes du profil candidat : coordonnees reutilisables et CV principal.

Le profil est unique par utilisateur. Il est cree a la volee s'il
n'existe pas encore lors de la premiere edition.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, Profil, TypeDocument, User
from app.services import fichiers
from app.session import get_current_user

router = APIRouter(tags=["profil"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)


def _get_or_create_profil(db: Session, user: User) -> Profil:
    if user.profil is not None:
        return user.profil
    profil = Profil(user_id=user.id)
    db.add(profil)
    db.commit()
    db.refresh(profil)
    return profil


@router.get("/profil", response_class=HTMLResponse)
def afficher(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Page du profil : coordonnees et CV principal."""
    profil = _get_or_create_profil(db, user)
    return templates.TemplateResponse(
        request, "profil.html", {"profil": profil, "user": user}
    )


@router.post("/profil")
def enregistrer(
    telephone: str | None = Form(None),
    email_candidat: str | None = Form(None),
    linkedin: str | None = Form(None),
    github: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enregistre les coordonnees du profil."""
    profil = _get_or_create_profil(db, user)
    profil.telephone = telephone
    profil.email_candidat = email_candidat
    profil.linkedin = linkedin
    profil.github = github
    db.commit()
    return RedirectResponse(url="/profil", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/profil/cv")
def definir_cv_principal(
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Televerse et definit le CV principal du profil. Enregistre comme
    document de profil (sans candidature), puis reference dans le profil.

    Memes controles que sur les documents d'une candidature : liste
    blanche d'extensions, plafond de taille, type MIME determine cote
    serveur (voir app.services.fichiers).
    """
    profil = _get_or_create_profil(db, user)

    chemin, taille, mime = fichiers.enregistrer(
        fichier, fichiers.dossier_cible(user.id, None)
    )

    document = Document(
        user_id=user.id,
        candidature_id=None,
        type=TypeDocument.cv,
        nom_fichier=fichier.filename or "cv",
        chemin=chemin,
        mime=mime,
        taille=taille,
    )
    db.add(document)
    db.flush()  # pour obtenir l'id du document avant de le referencer
    profil.cv_principal_document_id = document.id
    db.commit()
    return RedirectResponse(url="/profil", status_code=status.HTTP_303_SEE_OTHER)
