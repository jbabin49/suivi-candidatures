"""
Modeles Pydantic : validation des donnees entrantes (formulaires, API)
et mise en forme des donnees sortantes.

Separes des modeles SQLAlchemy (models.py) : ces derniers decrivent le
stockage, ceux-ci decrivent les echanges. Cette separation evite
d'exposer ou d'accepter des champs non voulus (ex. id, user_id).
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

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
