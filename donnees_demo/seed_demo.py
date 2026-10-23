"""
Jeu de donnees de demonstration, pour captures d'ecran du depot.

Donnees entierement fictives (entreprises, contacts, liens) : rien de
reel, rien de personnel. A lancer sur une base VIERGE et dediee aux
captures, jamais sur la base de production.

Usage (depuis la racine du projet, dans le conteneur) :
    docker compose exec app python donnees_demo/seed_demo.py

Ou en local si l'environnement le permet :
    DATA_DIR=/tmp/demo python donnees_demo/seed_demo.py

Cree un utilisateur de demonstration (demo@exemple.fr / demo) puis une
serie de candidatures a differents stades, dont une bien remplie pour
montrer la fiche detail et la frise.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

# Lance directement depuis un sous-dossier (python donnees_demo/seed_demo.py),
# Python ne met sur sys.path que le dossier du script, pas le repertoire
# courant : la racine du projet y est donc ajoutee explicitement pour que
# les imports app.* fonctionnent.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.local import hash_password  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import (  # noqa: E402
    Candidature,
    Contact,
    Entretien,
    Relance,
    Statut,
    TypeEntretien,
    User,
)

EMAIL_DEMO = "demo@exemple.fr"
MDP_DEMO = "demo"


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email=EMAIL_DEMO).first() is not None:
            print(
                f"L'utilisateur {EMAIL_DEMO} existe deja. "
                "Lance ce script sur une base vierge."
            )
            return

        user = User(
            email=EMAIL_DEMO,
            nom_affichage="Compte de démonstration",
            password_hash=hash_password(MDP_DEMO),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        d = dt.date
        # (offre, entreprise, ville, date, statut, source)
        candidatures = [
            ("Administrateur systèmes et réseaux", "Novatech Solutions", "Angers",
             d(2026, 10, 2), Statut.offre, "LinkedIn"),
            ("Technicien infrastructure", "GreenData Services", "Nantes",
             d(2026, 10, 8), Statut.entretien, "Indeed"),
            ("Admin sys junior", "Atlas Informatique", "Cholet",
             d(2026, 10, 13), Statut.relancee, "Hellowork"),
            ("Technicien support N2", "Lumen Industries", "Le Mans",
             d(2026, 10, 15), Statut.envoyee, "Candidature spontanée"),
            ("Ingénieur système Linux", "Orbit Cloud", "Rennes",
             d(2026, 9, 24), Statut.refus, "LinkedIn"),
            ("Technicien réseau", "Delta Télécom", "Tours",
             d(2026, 9, 20), Statut.sans_reponse, "Indeed"),
        ]

        objets = []
        for offre, ent, ville, date, statut, src in candidatures:
            c = Candidature(
                user_id=user.id,
                offre=offre,
                entreprise=ent,
                ville=ville,
                date_candidature=date,
                statut=statut,
                source=src,
            )
            db.add(c)
            objets.append(c)
        db.commit()
        for c in objets:
            db.refresh(c)

        # Candidature vitrine : Novatech (statut offre), bien remplie.
        novatech = objets[0]
        novatech.salaire = "32 000 - 35 000 € brut / an"
        novatech.type_contrat = "CDI"
        novatech.teletravail = "2 jours / semaine"
        novatech.lien_annonce = "https://exemple.fr/offres/admin-sys-reseaux"
        novatech.texte_annonce = (
            "Nous recherchons un administrateur systèmes et réseaux pour "
            "renforcer notre équipe infrastructure. Environnement : "
            "VMware vSphere, Active Directory, pare-feu FortiGate, "
            "supervision Zabbix. Astreintes ponctuelles."
        )
        db.add_all([
            Relance(candidature_id=novatech.id, date=d(2026, 10, 9), moyen="Mail",
                    texte="Bonjour, je me permets de revenir vers vous "
                          "concernant ma candidature au poste "
                          "d'administrateur systèmes et réseaux. Je reste "
                          "à votre disposition pour un échange."),
            Relance(candidature_id=novatech.id, date=d(2026, 10, 16), moyen="LinkedIn",
                    texte="Relance via LinkedIn auprès du responsable "
                          "infrastructure, qui m'a confirmé la bonne "
                          "réception du dossier."),
            Contact(candidature_id=novatech.id, nom="Responsable recrutement",
                    poste="Chargée RH",
                    email="recrutement@novatech-exemple.fr",
                    lien="https://www.linkedin.com/company/exemple"),
            Contact(candidature_id=novatech.id, nom="Responsable infrastructure",
                    poste="Lead infra",
                    lien="https://www.linkedin.com/in/exemple"),
            Entretien(candidature_id=novatech.id,
                      date_heure=dt.datetime(2026, 10, 14, 10, 30),
                      type=TypeEntretien.visio,
                      lieu_ou_lien="https://meet.exemple.fr/novatech-entretien",
                      personnes="Chargée RH + Lead infrastructure",
                      notes="Très bon échange. Questions sur FortiGate, la "
                            "gestion AD et la supervision. Test technique "
                            "proposé pour la semaine suivante."),
        ])

        # Un peu de relief sur les autres pour les compteurs et la liste.
        greendata = objets[1]
        db.add(Entretien(candidature_id=greendata.id,
                         date_heure=dt.datetime(2026, 10, 21, 14, 0),
                         type=TypeEntretien.telephone,
                         lieu_ou_lien="Appel entrant",
                         personnes="Responsable technique",
                         notes="Préqualification téléphonique, positive."))
        atlas = objets[2]
        atlas.date_prochaine_action = d(2026, 10, 27)
        db.add(Relance(candidature_id=atlas.id, date=d(2026, 10, 20),
                       moyen="Mail", texte="Première relance, une semaine "
                                           "après l'envoi de la candidature."))

        db.commit()
        print("Jeu de démonstration créé.")
        print(f"  Connexion : {EMAIL_DEMO} / {MDP_DEMO}")
        print(f"  {len(objets)} candidatures, dont 1 complète (Novatech).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
