"""
Gestion des comptes locaux : liste, creation, changement de son propre
mot de passe, suppression de son propre compte.

Monte uniquement en mode AUTH_MODE=local (voir main.py). En mode OIDC
ces routes n'existent pas : les comptes sont geres par le fournisseur
d'identite, et l'application n'a aucun mot de passe a changer.

Modele PLAT, volontairement : aucun role d'administrateur, tous les
comptes sont egaux. Tout utilisateur connecte peut consulter la liste et
creer un compte ; en revanche chacun ne peut toucher QUE le sien, pour
le mot de passe comme pour la suppression. C'est le modele de confiance
d'un poste partage entre quelques personnes qui se connaissent, pas
celui d'un service ouvert.

Cote donnees, la separation entre comptes est LOGIQUE : toutes les
requetes filtrent par user_id, mais la base SQLite n'est pas chiffree.
Voir SECURITE.md.
"""

from __future__ import annotations

import shutil

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.local import (
    creer_compte,
    hash_password,
    identifiant_deja_pris,
    verify_password,
)
from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import CompteCreate, MotDePasseChange
from app.session import get_current_user, logout_user
from app.templating import templates

router = APIRouter(tags=["comptes"])
settings = get_settings()


def _premier_message(exc: ValidationError) -> str:
    """
    Premier message de validation, debarrasse du prefixe "Value error, "
    que Pydantic ajoute aux ValueError levees dans un validateur.
    """
    return exc.errors()[0]["msg"].removeprefix("Value error, ")


def _tous_les_comptes(db: Session) -> list[User]:
    """Comptes existants, par identifiant, pour affichage."""
    return list(db.scalars(select(User).order_by(User.identifiant)))


def _nombre_de_comptes(db: Session) -> int:
    return db.query(User).count()


def _page_comptes(
    request: Request,
    db: Session,
    user: User,
    erreur: str | None = None,
    identifiant: str = "",
    nom_affichage: str = "",
    code: int = status.HTTP_200_OK,
):
    """
    Rend la page des comptes. Factorise le rendu entre l'affichage simple
    et le reaffichage apres une erreur de validation, qui doit conserver
    la saisie (jamais les mots de passe).
    """
    return templates.TemplateResponse(
        request,
        "comptes.html",
        {
            "comptes": _tous_les_comptes(db),
            "utilisateur": user,
            "erreur": erreur,
            "identifiant": identifiant,
            "nom_affichage": nom_affichage,
        },
        status_code=code,
    )


@router.get("/comptes", response_class=HTMLResponse)
def page_comptes(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste des comptes, et formulaire de creation."""
    return _page_comptes(request, db, user)


@router.post("/comptes", response_class=HTMLResponse)
def creer_un_compte(
    request: Request,
    identifiant: str = Form(""),
    nom_affichage: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Cree un compte supplementaire. Reserve aux utilisateurs connectes
    (get_current_user), contrairement a /bienvenue qui est la voie
    d'amorcage quand la base est vide.

    La session de l'utilisateur courant n'est pas touchee : on cree un
    compte pour quelqu'un d'autre, on ne se connecte pas dessus.
    """
    try:
        donnees = CompteCreate(
            identifiant=identifiant,
            nom_affichage=nom_affichage,
            password=password,
            password_confirm=password_confirm,
        )
    except ValidationError as exc:
        return _page_comptes(
            request,
            db,
            user,
            erreur=_premier_message(exc),
            identifiant=identifiant,
            nom_affichage=nom_affichage,
            code=status.HTTP_400_BAD_REQUEST,
        )

    # Unicite verifiee avant l'insertion, pour rendre un message clair
    # plutot que de laisser remonter une IntegrityError en 500.
    if identifiant_deja_pris(db, donnees.identifiant):
        return _page_comptes(
            request,
            db,
            user,
            erreur=f"L'identifiant « {donnees.identifiant} » est deja pris.",
            identifiant=identifiant,
            nom_affichage=nom_affichage,
            code=status.HTTP_400_BAD_REQUEST,
        )

    creer_compte(db, donnees)
    return RedirectResponse(url="/comptes", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/mon-compte/mot-de-passe", response_class=HTMLResponse)
def page_mot_de_passe(
    request: Request, user: User = Depends(get_current_user)
):
    """Formulaire de changement de SON propre mot de passe."""
    return templates.TemplateResponse(
        request, "mot_de_passe.html", {"utilisateur": user}
    )


@router.post("/mon-compte/mot-de-passe", response_class=HTMLResponse)
def changer_mot_de_passe(
    request: Request,
    password_actuel: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Change le mot de passe de l'utilisateur courant, et de lui seul :
    la cible n'est pas un parametre de la requete mais l'utilisateur
    resolu depuis la session. Aucun identifiant a fournir, donc aucun
    moyen de viser le compte d'un autre.

    Le mot de passe actuel est exige : un cookie de session vole ne doit
    pas suffire a verrouiller le compte de sa victime.
    """
    def erreur(message: str):
        # Aucun des trois champs n'est reaffiche : ce sont tous des mots
        # de passe.
        return templates.TemplateResponse(
            request,
            "mot_de_passe.html",
            {"utilisateur": user, "erreur": message},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if user.password_hash is None or not verify_password(
        password_actuel, user.password_hash
    ):
        return erreur("Mot de passe actuel incorrect.")

    try:
        donnees = MotDePasseChange(
            password_actuel=password_actuel,
            password=password,
            password_confirm=password_confirm,
        )
    except ValidationError as exc:
        return erreur(_premier_message(exc))

    user.password_hash = hash_password(donnees.password)
    db.commit()

    return templates.TemplateResponse(
        request,
        "mot_de_passe.html",
        {"utilisateur": user, "succes": "Mot de passe modifie."},
    )


@router.post("/comptes/{compte_id}/supprimer")
def supprimer_mon_compte(
    request: Request,
    compte_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Supprime SON propre compte, avec ses candidatures, documents et
    profil. Deux garde-fous, tous deux reverifies ici cote serveur :

    - l'identifiant vise doit etre celui de l'utilisateur courant. Un
      autre id repond 404 et non 403 : on ne confirme pas l'existence du
      compte d'autrui ;
    - le dernier compte restant n'est pas supprimable. Le supprimer
      laisserait une base vide, donc une instance que /bienvenue
      rouvrirait au premier visiteur venu.

    Le dossier uploads/<user_id>/ est efface a part : la cascade
    SQLAlchemy ne connait que les lignes, pas les fichiers sur disque.
    """
    if compte_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable"
        )

    if _nombre_de_comptes(db) <= 1:
        return _page_comptes(
            request,
            db,
            user,
            erreur=(
                "Impossible de supprimer le dernier compte : l'instance se "
                "retrouverait sans aucun utilisateur. Creez un autre compte "
                "d'abord."
            ),
            code=status.HTTP_400_BAD_REQUEST,
        )

    dossier_uploads = settings.uploads_dir / str(user.id)

    # La base d'abord, le disque ensuite. Si l'effacement des fichiers
    # echouait, il resterait des fichiers orphelins, sans reference :
    # moins grave que l'inverse, des lignes pointant vers des fichiers
    # disparus.
    db.delete(user)
    db.commit()

    shutil.rmtree(dossier_uploads, ignore_errors=True)

    # La session designe un compte qui n'existe plus : la vider
    # explicitement plutot que de laisser get_current_user la nettoyer
    # au prochain acces.
    logout_user(request)

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
