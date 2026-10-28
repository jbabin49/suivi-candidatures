"""
Tests des alertes "actions a mener" et du pre-remplissage de la date de
prochaine action.

L'alerte est pilotee par date_prochaine_action, et non plus par des
jalons J+7/14/21 depuis la date de candidature : ces tests fixent la
nouvelle regle et verifient qu'une relance l'eteint, y compris le cas
qui ne s'eteignait pas avant (relance saisie loin du jalon theorique).
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models import Candidature, Statut
from app.services import relances_calc

AUJOURDHUI = dt.date(2026, 10, 28)


def _candidature(**champs) -> Candidature:
    """Candidature en memoire, non persistee, pour tester le service seul."""
    defauts = {
        "offre": "Admin sys",
        "entreprise": "Armoni",
        "date_candidature": dt.date(2026, 10, 1),
        "statut": Statut.envoyee,
        "sans_relance_possible": False,
    }
    return Candidature(**{**defauts, **champs})


# Regle de l'alerte


def test_date_passee_declenche_une_action():
    c = _candidature(date_prochaine_action=dt.date(2026, 10, 20))

    actions = relances_calc.actions_du_jour([c], AUJOURDHUI)

    assert [a.candidature for a in actions] == [c]
    assert actions[0].echeance == dt.date(2026, 10, 20)
    assert actions[0].en_retard is True


def test_date_du_jour_declenche_une_action_pas_en_retard():
    c = _candidature(date_prochaine_action=AUJOURDHUI)

    actions = relances_calc.actions_du_jour([c], AUJOURDHUI)

    assert len(actions) == 1
    assert actions[0].en_retard is False


def test_date_future_ou_vide_ne_declenche_rien():
    future = _candidature(date_prochaine_action=dt.date(2026, 11, 15))
    vide = _candidature(date_prochaine_action=None)

    assert relances_calc.actions_du_jour([future, vide], AUJOURDHUI) == []


def test_statut_clos_ne_declenche_rien():
    for statut in relances_calc.STATUTS_CLOS:
        c = _candidature(
            statut=statut, date_prochaine_action=dt.date(2026, 10, 20)
        )
        assert relances_calc.actions_du_jour([c], AUJOURDHUI) == []


def test_sans_relance_possible_ne_declenche_jamais_rien():
    """Case cochee : aucune alerte, meme avec une date largement echue."""
    c = _candidature(
        date_prochaine_action=dt.date(2026, 1, 1),
        sans_relance_possible=True,
    )

    assert relances_calc.actions_du_jour([c], AUJOURDHUI) == []
    assert relances_calc.prochaine_action(c, AUJOURDHUI) is None


def test_actions_triees_par_echeance_croissante():
    recente = _candidature(date_prochaine_action=dt.date(2026, 10, 27))
    ancienne = _candidature(date_prochaine_action=dt.date(2026, 10, 10))
    moyenne = _candidature(date_prochaine_action=dt.date(2026, 10, 20))

    actions = relances_calc.actions_du_jour(
        [recente, ancienne, moyenne], AUJOURDHUI
    )

    assert [a.echeance for a in actions] == [
        dt.date(2026, 10, 10),
        dt.date(2026, 10, 20),
        dt.date(2026, 10, 27),
    ]


def test_echeance_apres_ajoute_sept_jours():
    assert relances_calc.echeance_apres(dt.date(2026, 10, 1)) == dt.date(
        2026, 10, 8
    )


# Pre-remplissage par les routes


def _creer(client: TestClient, date_candidature: str) -> int:
    r = client.post(
        "/candidatures",
        data={
            "offre": "Admin sys",
            "entreprise": "Armoni",
            "date_candidature": date_candidature,
        },
    )
    assert r.status_code == 303
    return int(r.headers["location"].rsplit("/", 1)[-1])


def _relire(candidature_id: int) -> Candidature:
    """Candidature rechargee depuis la base, relances comprises."""
    db = SessionLocal()
    try:
        return db.get(
            Candidature, candidature_id, options=[selectinload(Candidature.relances)]
        )
    finally:
        db.close()


def test_creation_programme_la_prochaine_action_a_j7(client):
    cid = _creer(client, "2026-10-08")

    candidature = _relire(cid)
    assert candidature.date_prochaine_action == dt.date(2026, 10, 15)
    assert candidature.sans_relance_possible is False


def test_relance_repousse_la_prochaine_action_et_eteint_l_alerte(client):
    cid = _creer(client, "2026-10-01")
    # La candidature est en alerte : prochaine action au 08/10, passee.
    assert _relire(cid).date_prochaine_action == dt.date(2026, 10, 8)
    assert relances_calc.actions_du_jour([_relire(cid)], AUJOURDHUI)

    r = client.post(
        f"/candidatures/{cid}/relances",
        data={"date": AUJOURDHUI.isoformat(), "moyen": "Mail"},
    )
    assert r.status_code == 303

    candidature = _relire(cid)
    assert candidature.date_prochaine_action == AUJOURDHUI + dt.timedelta(days=7)
    assert relances_calc.actions_du_jour([candidature], AUJOURDHUI) == []


def test_relance_tardive_eteint_aussi_l_alerte(client):
    """
    Le bug d'origine : une relance saisie bien apres le jalon theorique
    (ici J+24 au lieu de J+7) laissait l'alerte allumee, la fenetre de
    tolerance etant de +/- 2 jours autour du jalon. Desormais c'est la
    date de la relance qui compte.
    """
    cid = _creer(client, "2026-10-01")
    date_relance = dt.date(2026, 10, 25)  # J+24, hors de toute fenetre

    r = client.post(
        f"/candidatures/{cid}/relances",
        data={"date": date_relance.isoformat(), "moyen": "Mail"},
    )
    assert r.status_code == 303

    candidature = _relire(cid)
    assert candidature.date_prochaine_action == dt.date(2026, 11, 1)
    assert relances_calc.actions_du_jour([candidature], AUJOURDHUI) == []


def test_suppression_de_relance_ne_recalcule_pas_la_date(client):
    cid = _creer(client, "2026-10-01")
    client.post(
        f"/candidatures/{cid}/relances",
        data={"date": "2026-10-25", "moyen": "Mail"},
    )
    candidature = _relire(cid)
    relance_id = candidature.relances[0].id

    r = client.post(f"/candidatures/{cid}/relances/{relance_id}/supprimer")
    assert r.status_code == 303

    assert _relire(cid).date_prochaine_action == dt.date(2026, 11, 1)


# Case a cocher sur la fiche


def _formulaire(candidature: Candidature) -> dict[str, str]:
    """Champs du formulaire d'edition, tels que le gabarit les poste."""
    return {
        "offre": candidature.offre,
        "entreprise": candidature.entreprise,
        "date_candidature": candidature.date_candidature.isoformat(),
        "statut": candidature.statut.value,
        "date_prochaine_action": candidature.date_prochaine_action.isoformat(),
    }


def test_case_cochee_puis_decochee_par_le_formulaire(client):
    cid = _creer(client, "2026-10-01")
    champs = _formulaire(_relire(cid))

    # Cochee : la case est postee avec la valeur "1".
    r = client.post(
        f"/candidatures/{cid}", data={**champs, "sans_relance_possible": "1"}
    )
    assert r.status_code == 303
    candidature = _relire(cid)
    assert candidature.sans_relance_possible is True
    assert relances_calc.actions_du_jour([candidature], AUJOURDHUI) == []

    # Decochee : le navigateur n'envoie pas le champ du tout.
    r = client.post(f"/candidatures/{cid}", data=champs)
    assert r.status_code == 303
    candidature = _relire(cid)
    assert candidature.sans_relance_possible is False
    assert relances_calc.actions_du_jour([candidature], AUJOURDHUI)


def test_date_videe_depuis_le_formulaire_eteint_l_alerte(client):
    """
    Un champ date laisse vide est poste comme chaine vide. Elle doit
    valoir "pas de date" et non declencher un 422 : c'est le seul moyen
    de sortir une candidature des actions a mener sans la clore ni
    cocher la case.
    """
    cid = _creer(client, "2026-10-01")
    champs = _formulaire(_relire(cid))
    # La candidature est bien en alerte avant l'effacement.
    assert relances_calc.actions_du_jour([_relire(cid)], AUJOURDHUI)

    r = client.post(
        f"/candidatures/{cid}", data={**champs, "date_prochaine_action": ""}
    )

    assert r.status_code == 303
    candidature = _relire(cid)
    assert candidature.date_prochaine_action is None
    assert relances_calc.actions_du_jour([candidature], AUJOURDHUI) == []


def test_case_presente_sur_la_fiche(client):
    cid = _creer(client, "2026-10-01")

    page = client.get(f"/candidatures/{cid}").text

    assert 'name="sans_relance_possible"' in page
    assert "Aucun moyen de relancer cette candidature" in page
