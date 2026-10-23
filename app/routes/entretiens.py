"""
Routes des entretiens rattaches a une candidature.

Un entretien : date et heure, type (telephone, visio, presentiel), lieu
ou lien de connexion, personnes presentes et notes.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidature, Entretien, TypeEntretien, User
from app.session import get_current_user

router = APIRouter(tags=["entretiens"])


def _get_owned_candidature(
    db: Session, candidature_id: int, user: User
) -> Candidature:
    candidature = db.get(Candidature, candidature_id)
    if candidature is None or candidature.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidature introuvable"
        )
    return candidature


@router.post("/candidatures/{candidature_id}/entretiens")
def ajouter(
    candidature_id: int,
    date_heure: dt.datetime = Form(...),
    type: TypeEntretien = Form(...),
    lieu_ou_lien: str | None = Form(None),
    personnes: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ajoute un entretien a la candidature."""
    candidature = _get_owned_candidature(db, candidature_id, user)
    entretien = Entretien(
        candidature_id=candidature.id,
        date_heure=date_heure,
        type=type,
        lieu_ou_lien=lieu_ou_lien,
        personnes=personnes,
        notes=notes,
    )
    db.add(entretien)
    db.commit()
    return RedirectResponse(
        url=f"/candidatures/{candidature_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/candidatures/{candidature_id}/entretiens/{entretien_id}/supprimer")
def supprimer(
    candidature_id: int,
    entretien_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Supprime un entretien."""
    candidature = _get_owned_candidature(db, candidature_id, user)
    entretien = db.get(Entretien, entretien_id)
    if entretien is None or entretien.candidature_id != candidature.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entretien introuvable"
        )
    db.delete(entretien)
    db.commit()
    return RedirectResponse(
        url=f"/candidatures/{candidature_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
