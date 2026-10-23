"""Tests du service de construction de la timeline (positions proportionnelles)."""

from __future__ import annotations

import datetime as dt
import re

from app.models import Candidature, Relance, Statut
from app.services import timeline


def _candidature_fictive() -> Candidature:
    c = Candidature(
        offre="x",
        entreprise="y",
        date_candidature=dt.date(2026, 10, 8),
        statut=Statut.envoyee,
    )
    c.relances = [
        Relance(date=dt.date(2026, 10, 15)),
        Relance(date=dt.date(2026, 10, 22)),
    ]
    c.entretiens = []
    return c


def test_positions_proportionnelles():
    ev = timeline.construire(_candidature_fictive())
    # 3 evenements : candidature + 2 relances, espaces de 7 jours chacun.
    assert [e.type for e in ev] == ["candidature", "relance", "relance"]
    assert ev[0].position == 0.0
    assert ev[1].position == 0.5  # 7 jours sur 14
    assert ev[2].position == 1.0


def test_frise_transmise_sans_script_inline(client):
    """
    Les donnees de la frise passent par un attribut data-*, pas par un
    bloc <script>. Aucun script inline ne doit subsister sur la page de
    detail, sinon la CSP stricte le signale (et le bloquera).
    """
    r = client.post(
        "/candidatures",
        data={
            "offre": "Technicien",
            "entreprise": "Acme",
            "date_candidature": "2026-10-20",
        },
    )
    cid = r.headers["location"].rsplit("/", 1)[-1]
    page = client.get(f"/candidatures/{cid}").text

    # Tout <script> de la page doit porter un src : aucun contenu inline.
    scripts = re.findall(r"<script([^>]*)>", page)
    assert scripts, "la page doit charger au moins un script"
    assert all("src=" in attrs for attrs in scripts), scripts

    # Les donnees sont bien la, et serialisees de maniere sure.
    assert "data-evenements=" in page
    assert "| safe" not in page
    # tojson neutralise les sequences dangereuses en contexte HTML.
    assert "</script" not in page.split("data-evenements=")[1].split(">")[0]


def test_evenement_unique():
    c = Candidature(
        offre="x",
        entreprise="y",
        date_candidature=dt.date(2026, 10, 8),
        statut=Statut.envoyee,
    )
    c.relances = []
    c.entretiens = []
    ev = timeline.construire(c)
    assert len(ev) == 1
    assert ev[0].position == 0.0
