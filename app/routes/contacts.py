"""
Routes des contacts rattaches a une candidature.

Un contact : nom, poste eventuel, et un moyen de le joindre (email ou
lien LinkedIn / page web).

Le lien est le seul champ de l'application rendu tel quel dans un
attribut href. Il est donc valide a l'enregistrement : seuls http et
https sont acceptes (voir _valider_lien).
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidature, Contact, User
from app.session import get_current_user

router = APIRouter(tags=["contacts"])

# Seuls schemas d'URL acceptes pour le lien d'un contact.
SCHEMAS_AUTORISES = frozenset({"http", "https"})


def _normaliser_lien(lien: str) -> str:
    """
    Complete un lien sans schema par https://, pour accepter le domaine
    nu qu'on obtient en copiant une adresse ("linkedin.com/in/...").

    Un schema explicite n'est jamais complete ni reecrit : il est rendu
    tel quel a la validation, qui refusera tout ce qui n'est pas
    http(s). Prefixer "javascript:alert(1)" serait absurde et masquerait
    l'erreur.
    """
    if lien.lower().startswith(("http://", "https://")):
        return lien

    # URL relative au protocole (//exemple.test/page) : on fixe https.
    if lien.startswith("//"):
        return "https:" + lien

    # Schema explicite autre que http(s) : laisse tel quel pour que la
    # validation le refuse. Note : une adresse de la forme
    # "machine:8000/x" est lue comme un schema "machine" par urlparse et
    # sera donc refusee plutot que completee. Cas marginal pour un lien
    # de contact, et le refus est explicite.
    if urlparse(lien).scheme:
        return lien

    # Aucun schema : cas courant du domaine nu.
    return "https://" + lien


def _valider_lien(lien: str | None) -> str | None:
    """
    Normalise le lien puis verifie qu'il est bien en http ou https.

    Liste blanche volontairement stricte, donc fermee par defaut : tout
    ce qui n'est pas explicitement http(s) apres normalisation est
    refuse. Cela couvre javascript: et data:, qui permettraient
    l'execution de script depuis le href de la page de detail, ainsi que
    les schemas exotiques.
    """
    if lien is None or not lien.strip():
        return None

    lien = _normaliser_lien(lien.strip())
    # urlparse normalise la casse du schema et retire les caracteres de
    # controle (tabulations, retours a la ligne) qu'un navigateur
    # ignorerait aussi, ce qui evite les contournements du type
    # "java\nscript:".
    schema = urlparse(lien).scheme.lower()
    if schema not in SCHEMAS_AUTORISES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Le lien d'un contact doit commencer par http:// ou "
                "https:// (recu : "
                f"{schema + ':' if schema else 'aucun schema'})."
            ),
        )
    return lien


def _get_owned_candidature(
    db: Session, candidature_id: int, user: User
) -> Candidature:
    candidature = db.get(Candidature, candidature_id)
    if candidature is None or candidature.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidature introuvable"
        )
    return candidature


@router.post("/candidatures/{candidature_id}/contacts")
def ajouter(
    candidature_id: int,
    nom: str = Form(...),
    poste: str | None = Form(None),
    email: str | None = Form(None),
    lien: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ajoute un contact a la candidature."""
    candidature = _get_owned_candidature(db, candidature_id, user)
    contact = Contact(
        candidature_id=candidature.id,
        nom=nom,
        poste=poste,
        email=email,
        lien=_valider_lien(lien),
    )
    db.add(contact)
    db.commit()
    return RedirectResponse(
        url=f"/candidatures/{candidature_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/candidatures/{candidature_id}/contacts/{contact_id}/supprimer")
def supprimer(
    candidature_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Supprime un contact."""
    candidature = _get_owned_candidature(db, candidature_id, user)
    contact = db.get(Contact, contact_id)
    if contact is None or contact.candidature_id != candidature.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable"
        )
    db.delete(contact)
    db.commit()
    return RedirectResponse(
        url=f"/candidatures/{candidature_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
