"""
Service de calcul des compteurs de synthese affiches sur l'accueil.

Donne une vue d'ensemble de l'activite : volume de candidatures, part
ayant donne lieu a un retour, part ayant abouti a un entretien. Utile
pour ajuster sa strategie et, au besoin, justifier son activite de
recherche.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Candidature, Statut

# Statuts consideres comme "actifs" : la candidature est encore en jeu.
STATUTS_ACTIFS = (Statut.envoyee, Statut.relancee, Statut.entretien)

# Statuts temoignant d'un retour de l'employeur (positif ou negatif).
STATUTS_AVEC_RETOUR = (Statut.entretien, Statut.refus, Statut.offre)


@dataclass
class Compteurs:
    total: int
    actives: int
    taux_reponse: float  # pourcentage, 0 a 100
    taux_entretien: float  # pourcentage, 0 a 100


def compteurs(candidatures: list[Candidature]) -> Compteurs:
    """
    Calcule les compteurs a partir de la liste des candidatures de
    l'utilisateur. Les taux sont exprimes en pourcentage du total ;
    renvoie 0 si aucune candidature.
    """
    total = len(candidatures)
    if total == 0:
        return Compteurs(total=0, actives=0, taux_reponse=0.0, taux_entretien=0.0)

    actives = sum(1 for c in candidatures if c.statut in STATUTS_ACTIFS)
    avec_retour = sum(
        1 for c in candidatures if c.statut in STATUTS_AVEC_RETOUR
    )
    entretiens = sum(
        1 for c in candidatures if c.statut in (Statut.entretien, Statut.offre)
    )

    return Compteurs(
        total=total,
        actives=actives,
        taux_reponse=round(avec_retour / total * 100, 1),
        taux_entretien=round(entretiens / total * 100, 1),
    )
