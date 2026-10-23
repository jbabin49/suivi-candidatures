"""
Service de construction de la timeline d'une candidature.

La frise est derivee des dates deja presentes : date de candidature,
relances, entretiens, et date de reponse lorsque le statut est conclusif
(refus ou offre). Aucune table d'evenements n'est tenue.

Ce service produit une liste d'evenements ordonnes, avec pour chacun une
position relative (0 a 1) calculee proportionnellement au temps ecoule
entre le premier et le dernier evenement. Le rendu SVG (cote client ou
template) consomme cette liste ; la position permet l'espacement
proportionnel, le type permet la couleur de l'etiquette.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.models import Candidature, Statut


@dataclass
class Evenement:
    """Un point de la frise chronologique."""

    date: dt.date
    libelle: str
    type: str  # candidature | relance | entretien | reponse
    # Statut final pour un evenement de type "reponse" (offre/refus),
    # sinon None. Permet au rendu de colorer en vert ou rouge.
    issue: str | None = None
    position: float = 0.0  # 0 a 1, rempli par _positionner


def construire(candidature: Candidature) -> list[Evenement]:
    """
    Assemble et ordonne les evenements de la candidature, puis calcule
    leur position relative sur l'axe.
    """
    evenements: list[Evenement] = [
        Evenement(
            date=candidature.date_candidature,
            libelle="Candidature",
            type="candidature",
        )
    ]

    for i, relance in enumerate(
        sorted(candidature.relances, key=lambda r: r.date), start=1
    ):
        evenements.append(
            Evenement(
                date=relance.date,
                libelle=f"Relance {i}",
                type="relance",
            )
        )

    for entretien in candidature.entretiens:
        evenements.append(
            Evenement(
                date=entretien.date_heure.date(),
                libelle="Entretien",
                type="entretien",
            )
        )

    # Date de reponse : seulement si le statut est conclusif. On n'a pas
    # de date de reponse dediee en base, on utilise updated_at comme
    # meilleure approximation du moment ou le statut a ete pose.
    if candidature.statut in (Statut.offre, Statut.refus):
        evenements.append(
            Evenement(
                date=candidature.updated_at.date(),
                libelle="Reponse",
                type="reponse",
                issue=candidature.statut.value,
            )
        )

    evenements.sort(key=lambda e: e.date)
    _positionner(evenements)
    return evenements


def _positionner(evenements: list[Evenement]) -> None:
    """
    Calcule la position (0 a 1) de chaque evenement proportionnellement a
    sa date, entre le premier et le dernier. Modifie la liste en place.

    Cas limites : un seul evenement, ou tous a la meme date, sont repartis
    uniformement pour eviter une division par zero et un empilement.
    """
    if not evenements:
        return
    if len(evenements) == 1:
        evenements[0].position = 0.0
        return

    debut = evenements[0].date
    fin = evenements[-1].date
    duree = (fin - debut).days

    if duree == 0:
        # Toutes les dates identiques : repartition reguliere.
        n = len(evenements) - 1
        for i, e in enumerate(evenements):
            e.position = i / n
        return

    for e in evenements:
        e.position = (e.date - debut).days / duree
