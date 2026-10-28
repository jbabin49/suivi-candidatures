"""
Modeles de donnees de l'application de suivi de candidatures.

Definit les tables SQLAlchemy et leurs relations. Chaque utilisateur
possede ses propres candidatures ; une candidature agrege ses relances,
contacts, entretiens et documents.

Convention : les dates d'evenement (candidature, relance, entretien)
sont stockees telles que saisies. La timeline du detail est derivee de
ces dates a l'affichage, aucune table d'evenements separee n'est tenue.
"""

from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> dt.datetime:
    """Horodatage UTC courant (naif), pour les champs created_at/updated_at."""
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


# Enumerations


class Statut(str, enum.Enum):
    """Statut courant d'une candidature."""

    envoyee = "envoyee"
    relancee = "relancee"
    entretien = "entretien"
    sans_reponse = "sans_reponse"
    refus = "refus"
    offre = "offre"


class TypeEntretien(str, enum.Enum):
    telephone = "telephone"
    visio = "visio"
    presentiel = "presentiel"


class TypeDocument(str, enum.Enum):
    cv = "cv"
    lm = "lm"
    image_annonce = "image_annonce"


# Utilisateur et profil


class User(Base):
    """
    Compte utilisateur. Supporte l'auth locale (password_hash renseigne)
    ou l'auth externe OIDC (oidc_subject renseigne). Un seul des deux
    selon le mode d'authentification actif.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    nom_affichage: Mapped[str] = mapped_column(String(255), nullable=False)

    # Auth locale : hash argon2 du mot de passe. Nul si compte OIDC.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Auth OIDC : identifiant stable du sujet fourni par le fournisseur.
    # Nul si compte local.
    oidc_subject: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    profil: Mapped["Profil"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    candidatures: Mapped[list["Candidature"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Profil(Base):
    """
    Informations du candidat, une entree par utilisateur. Regroupe les
    coordonnees reutilisees dans les candidatures et le CV principal par
    defaut.
    """

    __tablename__ = "profils"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    telephone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email_candidat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # CV principal par defaut, reutilisable sur une candidature.
    cv_principal_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="profil")
    cv_principal: Mapped["Document | None"] = relationship(
        foreign_keys=[cv_principal_document_id]
    )


# Candidature et entites rattachees


class Candidature(Base):
    """Table centrale. Une candidature et ses informations de poste."""

    __tablename__ = "candidatures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    offre: Mapped[str] = mapped_column(String(255), nullable=False)
    entreprise: Mapped[str] = mapped_column(String(255), nullable=False)
    ville: Mapped[str | None] = mapped_column(String(255), nullable=True)

    date_candidature: Mapped[dt.date] = mapped_column(Date, nullable=False)
    statut: Mapped[Statut] = mapped_column(
        Enum(Statut), default=Statut.envoyee, nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_prochaine_action: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    # Candidature qu'on ne peut pas relancer (aucun contact, formulaire
    # anonyme...). Cochee, elle ne remonte jamais dans les actions a mener,
    # quelle que soit date_prochaine_action.
    sans_relance_possible: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )

    # Informations sur l'annonce.
    lien_annonce: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    texte_annonce: Mapped[str | None] = mapped_column(Text, nullable=True)
    salaire: Mapped[str | None] = mapped_column(String(100), nullable=True)
    type_contrat: Mapped[str | None] = mapped_column(String(100), nullable=True)
    teletravail: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="candidatures")
    relances: Mapped[list["Relance"]] = relationship(
        back_populates="candidature",
        cascade="all, delete-orphan",
        order_by="Relance.date",
    )
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="candidature", cascade="all, delete-orphan"
    )
    entretiens: Mapped[list["Entretien"]] = relationship(
        back_populates="candidature",
        cascade="all, delete-orphan",
        order_by="Entretien.date_heure",
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="candidature", cascade="all, delete-orphan"
    )


class Relance(Base):
    """
    Relance effectuee sur une candidature. On conserve le corps exact du
    message envoye (mail, message LinkedIn...) pour pouvoir le relire,
    l'archiver et le montrer.
    """

    __tablename__ = "relances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidature_id: Mapped[int] = mapped_column(
        ForeignKey("candidatures.id", ondelete="CASCADE"), nullable=False
    )

    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    moyen: Mapped[str | None] = mapped_column(String(100), nullable=True)
    texte: Mapped[str | None] = mapped_column(Text, nullable=True)

    candidature: Mapped["Candidature"] = relationship(back_populates="relances")


class Contact(Base):
    """Personne contact rattachee a une candidature."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidature_id: Mapped[int] = mapped_column(
        ForeignKey("candidatures.id", ondelete="CASCADE"), nullable=False
    )

    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    poste: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Lien LinkedIn ou page web du contact.
    lien: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    candidature: Mapped["Candidature"] = relationship(back_populates="contacts")


class Entretien(Base):
    """Entretien rattache a une candidature."""

    __tablename__ = "entretiens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidature_id: Mapped[int] = mapped_column(
        ForeignKey("candidatures.id", ondelete="CASCADE"), nullable=False
    )

    date_heure: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    type: Mapped[TypeEntretien] = mapped_column(Enum(TypeEntretien), nullable=False)
    # Lieu physique ou lien de visio selon le type.
    lieu_ou_lien: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Texte libre : noms et fonctions des personnes presentes.
    personnes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    candidature: Mapped["Candidature"] = relationship(back_populates="entretiens")


class Document(Base):
    """
    Fichier televerse (CV, lettre de motivation, image d'annonce) ou CV
    principal du profil.

    Le fichier est stocke sur disque dans le volume data/uploads ; seule
    la reference (chemin, metadonnees) est en base.

    candidature_id nul = document rattache au profil (ex. CV principal),
    non lie a une candidature precise.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    candidature_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidatures.id", ondelete="CASCADE"), nullable=True
    )

    type: Mapped[TypeDocument] = mapped_column(Enum(TypeDocument), nullable=False)
    nom_fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    # Chemin relatif au dossier uploads du volume.
    chemin: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    taille: Mapped[int | None] = mapped_column(Integer, nullable=True)

    uploaded_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(
        back_populates="documents", foreign_keys=[user_id]
    )
    candidature: Mapped["Candidature | None"] = relationship(
        back_populates="documents", foreign_keys=[candidature_id]
    )
