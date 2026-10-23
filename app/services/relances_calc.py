"""
Service de calcul des relances et des actions a mener.

Les echeances de relance (J+7, J+14, J+21) sont calculees a partir de la
date de candidature. Ce service sert a mettre en evidence, sur l'accueil,
les candidatures dont une relance est due, et a surligner les echeances
depassees.

Note : ce calcul est indicatif. Les relances reellement effectuees sont
saisies manuellement avec leur date exacte (table Relance) ; elles ne
sont pas deduites d'ici.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.models import Candidature, Statut

# Jalons de relance, en jours apres la candidature.
JALONS = (7, 14, 21)

# Statuts pour lesquels une relance n'a plus de sens.
STATUTS_CLOS = (Statut.entretien, Statut.refus, Statut.offre)


@dataclass
class Action:
    """Une relance a effectuer pour une candidature donnee."""

    candidature: Candidature
    echeance: dt.date
    jour_jalon: int
    en_retard: bool


def echeances(candidature: Candidature) -> list[dt.date]:
    """Retourne les dates des jalons de relance pour une candidature."""
    return [
        candidature.date_candidature + dt.timedelta(days=j) for j in JALONS
    ]


def prochaine_relance_due(
    candidature: Candidature, aujourdhui: dt.date | None = None
) -> Action | None:
    """
    Determine la prochaine relance a effectuer : premier jalon atteint
    (echeance <= aujourd'hui) qui n'a pas encore de relance saisie a une
    date proche. Retourne None si la candidature est close ou si aucune
    relance n'est due.
    """
    if candidature.statut in STATUTS_CLOS:
        return None

    aujourdhui = aujourdhui or dt.date.today()
    dates_relances = {r.date for r in candidature.relances}

    for jour, echeance in zip(JALONS, echeances(candidature)):
        if echeance > aujourdhui:
            # Jalon pas encore atteint : rien de du pour l'instant.
            break
        # Jalon atteint : du si aucune relance deja saisie a cette echeance.
        if not any(
            abs((d - echeance).days) <= 2 for d in dates_relances
        ):
            return Action(
                candidature=candidature,
                echeance=echeance,
                jour_jalon=jour,
                en_retard=echeance < aujourdhui,
            )
    return None


def actions_du_jour(
    candidatures: list[Candidature], aujourdhui: dt.date | None = None
) -> list[Action]:
    """
    Liste des relances dues sur l'ensemble des candidatures, triees par
    echeance (les plus anciennes, donc les plus en retard, en premier).
    Alimente le bloc "prochaines actions" de l'accueil.
    """
    aujourdhui = aujourdhui or dt.date.today()
    actions = [
        action
        for c in candidatures
        if (action := prochaine_relance_due(c, aujourdhui)) is not None
    ]
    return sorted(actions, key=lambda a: a.echeance)
