"""
Routes des relances rattachees a une candidature.

Une relance conserve la date, le moyen utilise et le corps exact du
message envoye, pour archivage et relecture.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidature, Relance, User
from app.session import get_current_user

router = APIRouter(tags=["relances"])


def _get_owned_candidature(
    db: Session, candidature_id: int, user: User
) -> Candidature:
    candidature = db.get(Candidature, candidature_id)
    if candidature is None or candidature.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidature introuvable"
        )
    return candidature


@router.post("/candidatures/{candidature_id}/relances")
def ajouter(
    candidature_id: int,
    date: dt.date = Form(...),
    moyen: str | None = Form(None),
    texte: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ajoute une relance a la candidature."""
    candidature = _get_owned_candidature(db, candidature_id, user)
    relance = Relance(
        candidature_id=candidature.id, date=date, moyen=moyen, texte=texte
    )
    db.add(relance)
    db.commit()
    return RedirectResponse(
        url=f"/candidatures/{candidature_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/candidatures/{candidature_id}/relances/{relance_id}/supprimer")
def supprimer(
    candidature_id: int,
    relance_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Supprime une relance."""
    candidature = _get_owned_candidature(db, candidature_id, user)
    relance = db.get(Relance, relance_id)
    if relance is None or relance.candidature_id != candidature.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Relance introuvable"
        )
    db.delete(relance)
    db.commit()
    return RedirectResponse(
        url=f"/candidatures/{candidature_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
