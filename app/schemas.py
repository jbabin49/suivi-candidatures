"""
Modeles Pydantic : validation des donnees entrantes (formulaires, API)
et mise en forme des donnees sortantes.

Separes des modeles SQLAlchemy (models.py) : ces derniers decrivent le
stockage, ceux-ci decrivent les echanges. Cette separation evite
d'exposer ou d'accepter des champs non voulus (ex. id, user_id).
"""

from __future__ import annotations

import datetime as dt
import re

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models import Statut, TypeDocument, TypeEntretien


# Candidatures


class CandidatureBase(BaseModel):
    offre: str
    entreprise: str
    ville: str | None = None
    date_candidature: dt.date
    statut: Statut = Statut.envoyee
    source: str | None = None
    date_prochaine_action: dt.date | None = None
    sans_relance_possible: bool = False
    lien_annonce: str | None = None
    texte_annonce: str | None = None
    salaire: str | None = None
    type_contrat: str | None = None
    teletravail: str | None = None


class CandidatureCreate(CandidatureBase):
    """Donnees acceptees a la creation."""


class CandidatureUpdate(BaseModel):
    """
    Donnees acceptees a l'edition. Tous les champs optionnels : seuls
    ceux fournis sont modifies.
    """

    offre: str | None = None
    entreprise: str | None = None
    ville: str | None = None
    date_candidature: dt.date | None = None
    statut: Statut | None = None
    source: str | None = None
    date_prochaine_action: dt.date | None = None
    sans_relance_possible: bool | None = None
    lien_annonce: str | None = None
    texte_annonce: str | None = None
    salaire: str | None = None
    type_contrat: str | None = None
    teletravail: str | None = None


class CandidatureRead(CandidatureBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: dt.datetime
    updated_at: dt.datetime


# Relances


class RelanceBase(BaseModel):
    date: dt.date
    moyen: str | None = None
    texte: str | None = None


class RelanceCreate(RelanceBase):
    pass


class RelanceRead(RelanceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidature_id: int


# Contacts


class ContactBase(BaseModel):
    nom: str
    poste: str | None = None
    email: str | None = None
    lien: str | None = None


class ContactCreate(ContactBase):
    pass


class ContactRead(ContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidature_id: int


# Entretiens


class EntretienBase(BaseModel):
    date_heure: dt.datetime
    type: TypeEntretien
    lieu_ou_lien: str | None = None
    personnes: str | None = None
    notes: str | None = None


class EntretienCreate(EntretienBase):
    pass


class EntretienRead(EntretienBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidature_id: int


# Documents


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidature_id: int | None
    type: TypeDocument
    nom_fichier: str
    mime: str | None
    taille: int | None
    uploaded_at: dt.datetime


# Premier compte (ecran de premiere connexion, mode auth locale)

# Validation de forme de l'adresse email.
#
# C'est la regle "valid e-mail address" de la specification HTML du
# WHATWG, reprise telle quelle : exactement celle qu'applique
# <input type="email"> dans le navigateur. Volontairement ni une regex
# maison, ni pydantic EmailStr.
#
#   - pas de regex maison : plus stricte que le navigateur, elle ferait
#     passer la validation cote client puis echouer cote serveur, sans
#     explication comprehensible pour l'utilisateur ; plus laxiste, elle
#     accepterait ce que le formulaire a deja refuse, donc du code mort ;
#   - pas de EmailStr : cela ajouterait la dependance email-validator
#     pour un unique champ de formulaire.
#
# A noter, c'est le comportement du navigateur et non celui de la RFC
# 5322 : le point n'est pas exige dans le domaine, donc vous@nas ou
# admin@localhost sont acceptes. C'est voulu pour une application
# auto-hebergee sur reseau local.
#
# Source : https://html.spec.whatwg.org/multipage/input.html#valid-e-mail-address
_FORME_EMAIL = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# L'application n'offre aucune route de recuperation ni de changement de
# mot de passe : un mot de passe mal saisi enferme l'utilisateur hors de
# ses donnees. D'ou la confirmation obligatoire ci-dessous.
LONGUEUR_MINIMALE_MOT_DE_PASSE = 8


class PremierCompte(BaseModel):
    """
    Donnees du formulaire de creation du premier compte (/bienvenue).

    Les messages d'erreur sont rediges en francais : ils sont reaffiches
    tels quels a l'utilisateur par la route, et non journalises.
    """

    email: str
    nom_affichage: str
    password: str
    password_confirm: str

    @field_validator("email")
    @classmethod
    def _valider_email(cls, valeur: str) -> str:
        valeur = valeur.strip()
        # fullmatch et non match : en Python, "$" tolere un retour a la
        # ligne final. Le strip() ci-dessus l'enleve deja, fullmatch
        # n'est donc qu'une ceinture de securite si ce strip disparait.
        if not _FORME_EMAIL.fullmatch(valeur):
            raise ValueError("Adresse email invalide.")
        return valeur

    @field_validator("nom_affichage")
    @classmethod
    def _valider_nom(cls, valeur: str) -> str:
        valeur = valeur.strip()
        if not valeur:
            raise ValueError("Le nom affiche est obligatoire.")
        return valeur

    @field_validator("password")
    @classmethod
    def _valider_mot_de_passe(cls, valeur: str) -> str:
        if len(valeur) < LONGUEUR_MINIMALE_MOT_DE_PASSE:
            raise ValueError(
                "Le mot de passe doit comporter au moins "
                f"{LONGUEUR_MINIMALE_MOT_DE_PASSE} caracteres."
            )
        return valeur

    @model_validator(mode="after")
    def _valider_confirmation(self) -> "PremierCompte":
        if self.password != self.password_confirm:
            raise ValueError("Les deux mots de passe ne correspondent pas.")
        return self
