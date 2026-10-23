"""
Routes des candidatures : page d'accueil (tableau + compteurs), creation,
page de detail et edition.

Les pages HTML sont rendues avec Jinja2. Les actions de creation/edition
sont traitees a partir de formulaires et redirigent apres succes (schema
Post/Redirect/Get). La logique metier (stats, timeline, calcul des
relances) est deleguee aux services, ces routes restent courtes.
"""

from __future__ import annotations

from pathlib import Path

import datetime as dt

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidature, Statut, User
from app.services import stats as stats_service
from app.services import timeline as timeline_service
from app.services import relances_calc
from app.session import get_current_user

router = APIRouter(tags=["candidatures"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)


def _get_owned_candidature(
    db: Session, candidature_id: int, user: User
) -> Candidature:
    """
    Recupere une candidature en verifiant qu'elle appartient bien a
    l'utilisateur courant. Leve 404 sinon (on ne distingue pas "inexistante"
    de "appartient a un autre", pour ne pas divulguer son existence).
    """
    candidature = db.get(Candidature, candidature_id)
    if candidature is None or candidature.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidature introuvable"
        )
    return candidature


@router.get("/", response_class=HTMLResponse)
def accueil(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Page d'accueil : tableau des candidatures de l'utilisateur, compteurs
    de synthese et rappel des prochaines actions a mener.
    """
    candidatures = db.scalars(
        select(Candidature)
        .where(Candidature.user_id == user.id)
        .order_by(Candidature.date_candidature.desc())
    ).all()

    compteurs = stats_service.compteurs(candidatures)
    actions = relances_calc.actions_du_jour(candidatures)

    return templates.TemplateResponse(
        request,
        "accueil.html",
        {
            "candidatures": candidatures,
            "compteurs": compteurs,
            "actions": actions,
            "aujourdhui": dt.date.today(),
        },
    )


@router.post("/candidatures")
def creer(
    request: Request,
    offre: str = Form(...),
    entreprise: str = Form(...),
    ville: str | None = Form(None),
    date_candidature: dt.date = Form(...),
    source: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Cree une candidature depuis le formulaire d'ajout de ligne de
    l'accueil. Les champs detailles (annonce, salaire...) se renseignent
    ensuite sur la page de detail.
    """
    candidature = Candidature(
        user_id=user.id,
        offre=offre,
        entreprise=entreprise,
        ville=ville,
        date_candidature=date_candidature,
        source=source,
        statut=Statut.envoyee,
    )
    db.add(candidature)
    db.commit()
    db.refresh(candidature)
    return RedirectResponse(
        url=f"/candidatures/{candidature.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/candidatures/{candidature_id}", response_class=HTMLResponse)
def detail(
    candidature_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Page de detail d'une candidature : timeline en haut, puis relances,
    contacts, entretiens, documents et informations du poste.
    """
    candidature = _get_owned_candidature(db, candidature_id, user)
    evenements = timeline_service.construire(candidature)

    # Evenements de la frise, transmis telle quelle au gabarit. La
    # serialisation est faite par le filtre tojson de Jinja dans un
    # attribut data-*, qui echappe <, >, & et l'apostrophe : aucune
    # donnee ne peut s'echapper du contexte HTML.
    evenements_frise = [
        {
            "date": e.date.strftime("%d/%m/%Y"),
            "libelle": e.libelle,
            "type": e.type,
            "issue": e.issue,
            "position": e.position,
        }
        for e in evenements
    ]

    return templates.TemplateResponse(
        request,
        "candidature.html",
        {
            "candidature": candidature,
            "evenements_frise": evenements_frise,
            "statuts": list(Statut),
        },
    )


@router.post("/candidatures/{candidature_id}")
def editer(
    candidature_id: int,
    request: Request,
    offre: str = Form(...),
    entreprise: str = Form(...),
    ville: str | None = Form(None),
    date_candidature: dt.date = Form(...),
    statut: Statut = Form(...),
    source: str | None = Form(None),
    date_prochaine_action: dt.date | None = Form(None),
    lien_annonce: str | None = Form(None),
    texte_annonce: str | None = Form(None),
    salaire: str | None = Form(None),
    type_contrat: str | None = Form(None),
    teletravail: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enregistre les modifications de la candidature."""
    candidature = _get_owned_candidature(db, candidature_id, user)

    candidature.offre = offre
    candidature.entreprise = entreprise
    candidature.ville = ville
    candidature.date_candidature = date_candidature
    candidature.statut = statut
    candidature.source = source
    candidature.date_prochaine_action = date_prochaine_action
    candidature.lien_annonce = lien_annonce
    candidature.texte_annonce = texte_annonce
    candidature.salaire = salaire
    candidature.type_contrat = type_contrat
    candidature.teletravail = teletravail

    db.commit()
    return RedirectResponse(
        url=f"/candidatures/{candidature_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/candidatures/{candidature_id}/supprimer")
def supprimer(
    candidature_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Supprime une candidature et, par cascade, ses relances, contacts,
    entretiens et documents rattaches.
    """
    candidature = _get_owned_candidature(db, candidature_id, user)
    db.delete(candidature)
    db.commit()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
