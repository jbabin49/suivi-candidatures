"""
Service des actions a mener : quelles candidatures relancer aujourd'hui.

Le pilote est le champ date_prochaine_action de la candidature, pas un
calcul de jalons. Une candidature remonte dans les actions de l'accueil
si et seulement si :

- son statut n'est pas clos (entretien, refus, offre) ;
- date_prochaine_action est renseignee et echue (<= aujourd'hui) ;
- la case "aucun moyen de relancer" n'est pas cochee.

Consequence voulue : l'alerte s'eteint des que date_prochaine_action est
repoussee. Les routes s'en chargent (creation de la candidature et
enregistrement d'une relance la positionnent a +7 jours), et le champ
reste modifiable a la main sur la fiche. L'ancien calcul par jalons
J+7/14/21 depuis la date de candidature est abandonne : il ne tenait pas
compte des relances saisies hors d'une fenetre de +/- 2 jours autour du
jalon, et laissait donc l'alerte allumee a tort.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.models import Candidature, Statut

# Delai par defaut avant la prochaine relance, en jours. Applique a la
# creation d'une candidature et apres chaque relance enregistree.
DELAI_RELANCE_JOURS = 7

# Statuts pour lesquels une relance n'a plus de sens.
STATUTS_CLOS = (Statut.entretien, Statut.refus, Statut.offre)


@dataclass
class Action:
    """Une action a mener sur une candidature, et son echeance."""

    candidature: Candidature
    echeance: dt.date
    en_retard: bool


def prochaine_action(
    candidature: Candidature, aujourdhui: dt.date | None = None
) -> Action | None:
    """
    Action a mener sur cette candidature, ou None s'il n'y en a pas.

    None si le statut est clos, si la case "aucun moyen de relancer" est
    cochee, ou si date_prochaine_action est vide ou encore a venir.
    """
    if candidature.statut in STATUTS_CLOS:
        return None
    if candidature.sans_relance_possible:
        return None

    echeance = candidature.date_prochaine_action
    if echeance is None:
        return None

    aujourdhui = aujourdhui or dt.date.today()
    if echeance > aujourdhui:
        return None

    return Action(
        candidature=candidature,
        echeance=echeance,
        en_retard=echeance < aujourdhui,
    )


def actions_du_jour(
    candidatures: list[Candidature], aujourdhui: dt.date | None = None
) -> list[Action]:
    """
    Actions a mener sur l'ensemble des candidatures, triees par echeance
    croissante (les plus anciennes, donc les plus en retard, en premier).
    Alimente le bloc "prochaines actions" de l'accueil.
    """
    aujourdhui = aujourdhui or dt.date.today()
    actions = [
        action
        for c in candidatures
        if (action := prochaine_action(c, aujourdhui)) is not None
    ]
    return sorted(actions, key=lambda a: a.echeance)


def echeance_apres(reference: dt.date) -> dt.date:
    """
    Date de prochaine action a retenir apres un evenement date du
    `reference` (envoi de la candidature, ou relance enregistree).
    """
    return reference + dt.timedelta(days=DELAI_RELANCE_JOURS)
