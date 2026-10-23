"""
Routes des documents : televersement, consultation et suppression des
CV, lettres de motivation et images d'annonce.

Les fichiers sont stockes sur disque dans le volume data/uploads, ranges
par utilisateur et par candidature. Seules les references (chemin,
metadonnees) sont en base.

Le CV principal du profil (candidature_id nul) est gere ici aussi : il
peut etre reutilise sur une candidature, par reference (on pointe le meme
document) ou par copie (on duplique le fichier pour figer ce qui a ete
envoye). Le choix se fait a l'appel de reutiliser_cv_principal.

La validation des televersements (liste blanche d'extensions, plafond de
taille, type MIME determine cote serveur) est portee par
app.services.fichiers, partagee avec les routes du profil.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Candidature, Document, TypeDocument, User
from app.services import fichiers
from app.session import get_current_user

router = APIRouter(tags=["documents"])
settings = get_settings()


def _get_owned_candidature(
    db: Session, candidature_id: int, user: User
) -> Candidature:
    candidature = db.get(Candidature, candidature_id)
    if candidature is None or candidature.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidature introuvable"
        )
    return candidature


@router.post("/candidatures/{candidature_id}/documents")
def televerser(
    candidature_id: int,
    type: TypeDocument = Form(...),
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Televerse un document (CV, LM, image d'annonce) sur une candidature."""
    candidature = _get_owned_candidature(db, candidature_id, user)
    chemin, taille, mime = fichiers.enregistrer(
        fichier, fichiers.dossier_cible(user.id, candidature.id)
    )

    document = Document(
        user_id=user.id,
        candidature_id=candidature.id,
        type=type,
        nom_fichier=fichier.filename or "document",
        chemin=chemin,
        # Type determine cote serveur depuis l'extension validee, jamais
        # celui annonce par le client.
        mime=mime,
        taille=taille,
    )
    db.add(document)
    db.commit()
    return RedirectResponse(
        url=f"/candidatures/{candidature_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/documents/{document_id}")
def consulter(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Renvoie le fichier d'un document en telechargement, apres
    verification qu'il appartient bien a l'utilisateur.

    Le fichier est toujours servi en piece jointe avec un type opaque,
    jamais avec le type MIME de la base : aucun fichier televerse ne doit
    pouvoir etre rendu ni execute dans l'origine de l'application.
    """
    document = db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable"
        )
    chemin_abs = settings.uploads_dir / document.chemin
    if not chemin_abs.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fichier manquant"
        )
    return FileResponse(
        chemin_abs,
        filename=document.nom_fichier,
        media_type="application/octet-stream",
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post("/candidatures/{candidature_id}/documents/reutiliser-cv")
def reutiliser_cv_principal(
    candidature_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Rattache le CV principal du profil a la candidature, en copiant le
    fichier pour figer exactement ce qui a ete envoye (une modification
    ulterieure du CV principal n'affecte pas l'archive de la candidature).
    """
    candidature = _get_owned_candidature(db, candidature_id, user)
    if user.profil is None or user.profil.cv_principal is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun CV principal enregistre dans le profil",
        )

    source = user.profil.cv_principal
    source_abs = settings.uploads_dir / source.chemin
    if not source_abs.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier du CV principal manquant",
        )

    dossier_rel = fichiers.dossier_cible(user.id, candidature.id)
    dossier_abs = settings.uploads_dir / dossier_rel
    dossier_abs.mkdir(parents=True, exist_ok=True)
    extension = Path(source.chemin).suffix.lower()
    nom_stocke = f"{uuid.uuid4().hex}{extension}"
    shutil.copy2(source_abs, dossier_abs / nom_stocke)

    copie = Document(
        user_id=user.id,
        candidature_id=candidature.id,
        type=TypeDocument.cv,
        nom_fichier=source.nom_fichier,
        chemin=str(dossier_rel / nom_stocke),
        mime=fichiers.mime_depuis_extension(extension),
        taille=source.taille,
    )
    db.add(copie)
    db.commit()
    return RedirectResponse(
        url=f"/candidatures/{candidature_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/documents/{document_id}/supprimer")
def supprimer(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Supprime un document (enregistrement en base et fichier sur disque)."""
    document = db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable"
        )
    candidature_id = document.candidature_id
    chemin_abs = settings.uploads_dir / document.chemin
    chemin_abs.unlink(missing_ok=True)
    db.delete(document)
    db.commit()

    cible = f"/candidatures/{candidature_id}" if candidature_id else "/profil"
    return RedirectResponse(url=cible, status_code=status.HTTP_303_SEE_OTHER)
