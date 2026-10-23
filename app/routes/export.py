"""
Route d'export des candidatures au format CSV.

Produit un fichier telechargeable reprenant les candidatures de
l'utilisateur, utilisable comme justificatif d'activite ou pour une
reprise dans un tableur. Le CSV est genere en memoire, sans fichier
temporaire sur disque.

Format CSV retenu plutot que xlsx natif : lisible partout, sans
dependance supplementaire, et ouvrable directement par Excel/LibreOffice.
"""

from __future__ import annotations

import csv
import datetime as dt
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidature, User
from app.session import get_current_user

router = APIRouter(tags=["export"])

EN_TETES = [
    "Offre",
    "Entreprise",
    "Ville",
    "Date de candidature",
    "Statut",
    "Source",
    "Prochaine action",
    "Nb relances",
    "Nb entretiens",
]


@router.get("/export.csv")
def exporter_csv(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Exporte toutes les candidatures de l'utilisateur en CSV."""
    candidatures = db.scalars(
        select(Candidature)
        .where(Candidature.user_id == user.id)
        .order_by(Candidature.date_candidature.desc())
    ).all()

    tampon = io.StringIO()
    # Separateur point-virgule : attendu par Excel en locale francaise.
    ecrivain = csv.writer(tampon, delimiter=";")
    ecrivain.writerow(EN_TETES)
    for c in candidatures:
        ecrivain.writerow(
            [
                c.offre,
                c.entreprise,
                c.ville or "",
                c.date_candidature.strftime("%d/%m/%Y"),
                c.statut.value,
                c.source or "",
                c.date_prochaine_action.strftime("%d/%m/%Y")
                if c.date_prochaine_action
                else "",
                len(c.relances),
                len(c.entretiens),
            ]
        )

    tampon.seek(0)
    horodatage = dt.date.today().strftime("%Y%m%d")
    nom = f"candidatures_{horodatage}.csv"
    # BOM UTF-8 en tete pour qu'Excel reconnaisse l'encodage et les accents.
    contenu = "\ufeff" + tampon.getvalue()
    return StreamingResponse(
        io.BytesIO(contenu.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )
