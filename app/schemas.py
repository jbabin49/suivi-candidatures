"""
Modeles Pydantic : validation des donnees entrantes (formulaires, API)
et mise en forme des donnees sortantes.

Separes des modeles SQLAlchemy (models.py) : ces derniers decrivent le
stockage, ceux-ci decrivent les echanges. Cette separation evite
d'exposer ou d'accepter des champs non voulus (ex. id, user_id).
"""

from __future__ import annotations

import datetime as dt

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


# Comptes (ecran de premiere connexion et gestion des comptes locaux)

# Longueur maximale de l'identifiant, alignee sur la colonne
# users.identifiant (String(255)) : valider ici evite une erreur
# d'integrite SQLite remontee en 500.
LONGUEUR_MAX_IDENTIFIANT = 255

# L'application n'offre aucune procedure de recuperation de mot de
# passe : un mot de passe mal saisi enferme l'utilisateur hors de ses
# donnees. D'ou la confirmation obligatoire partout ou un mot de passe
# est choisi.
LONGUEUR_MINIMALE_MOT_DE_PASSE = 8


class _ChoixMotDePasse(BaseModel):
    """
    Partie commune a tous les formulaires qui font choisir un mot de
    passe : longueur minimale et confirmation identique.
    """

    password: str
    password_confirm: str

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
    def _valider_confirmation(self) -> "_ChoixMotDePasse":
        if self.password != self.password_confirm:
            raise ValueError("Les deux mots de passe ne correspondent pas.")
        return self


class CompteCreate(_ChoixMotDePasse):
    """
    Donnees de creation d'un compte local : premier compte (/bienvenue)
    comme comptes suivants (/comptes).

    L'identifiant est une chaine libre, volontairement sans contrainte
    de format : ni email impose, ni jeu de caracteres restreint. Il
    n'est ni envoye par courriel, ni interpole dans une requete (toutes
    passent par SQLAlchemy), ni rendu sans echappement (autoescape
    Jinja2). Seules les bornes qui protegent la base sont verifiees.

    Les messages d'erreur sont rediges en francais : ils sont reaffiches
    tels quels a l'utilisateur par la route, et non journalises.
    """

    identifiant: str
    # Facultatif : l'utilisateur peut ne saisir qu'un identifiant et un
    # mot de passe. Le defaut est applique par nom_affichage_effectif.
    nom_affichage: str = ""

    @field_validator("identifiant")
    @classmethod
    def _valider_identifiant(cls, valeur: str) -> str:
        valeur = valeur.strip()
        if not valeur:
            raise ValueError("L'identifiant est obligatoire.")
        if len(valeur) > LONGUEUR_MAX_IDENTIFIANT:
            raise ValueError(
                "L'identifiant ne peut pas depasser "
                f"{LONGUEUR_MAX_IDENTIFIANT} caracteres."
            )
        return valeur

    @field_validator("nom_affichage")
    @classmethod
    def _valider_nom(cls, valeur: str) -> str:
        return valeur.strip()

    @property
    def nom_affichage_effectif(self) -> str:
        """
        Nom a enregistrer : celui saisi, sinon l'identifiant. Permet de
        creer un compte avec le seul couple identifiant / mot de passe.
        """
        return self.nom_affichage or self.identifiant


class MotDePasseChange(_ChoixMotDePasse):
    """
    Changement de son propre mot de passe. Le mot de passe actuel est
    verifie par la route (verify_password) et non ici : ce modele ne
    valide que la forme du nouveau.
    """

    password_actuel: str
