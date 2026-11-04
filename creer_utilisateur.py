"""
Creation d'un utilisateur en mode auth locale, depuis la ligne de commande.

Utile pour creer le premier compte sans passer par les variables
ADMIN_IDENTIFIANT / ADMIN_PASSWORD ni par l'ecran /bienvenue, ou pour
ajouter un utilisateur sans passer par /comptes.

L'identifiant est une chaine libre, pas forcement une adresse email :
"julien" convient.

Usage (depuis la racine du projet) :
    python creer_utilisateur.py <identifiant> [nom_affichage]

Le nom affiche est facultatif : a defaut, l'identifiant est repris.
Le mot de passe est demande de maniere interactive (non affiche).

En Docker :
    docker compose exec app python creer_utilisateur.py <identifiant> "<Nom>"
"""

from __future__ import annotations

import getpass
import sys

from sqlalchemy import select

from app.auth.local import hash_password
from app.database import SessionLocal, init_db
from app.models import User
from app.schemas import LONGUEUR_MINIMALE_MOT_DE_PASSE


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print(
            "Usage : python creer_utilisateur.py <identifiant> [nom_affichage]"
        )
        sys.exit(1)

    identifiant = sys.argv[1].strip()
    if not identifiant:
        print("Identifiant vide, abandon.")
        sys.exit(1)
    # Nom affiche facultatif : a defaut, l'identifiant fait office de nom.
    nom = (sys.argv[2].strip() if len(sys.argv) == 3 else "") or identifiant

    mot_de_passe = getpass.getpass("Mot de passe : ")
    if not mot_de_passe:
        print("Mot de passe vide, abandon.")
        sys.exit(1)
    if len(mot_de_passe) < LONGUEUR_MINIMALE_MOT_DE_PASSE:
        print(
            "Mot de passe trop court : "
            f"{LONGUEUR_MINIMALE_MOT_DE_PASSE} caracteres minimum."
        )
        sys.exit(1)
    # Confirmation : aucune procedure de recuperation n'existe, une faute
    # de frappe rendrait le compte inaccessible.
    if getpass.getpass("Confirmation : ") != mot_de_passe:
        print("Les deux mots de passe ne correspondent pas, abandon.")
        sys.exit(1)

    init_db()
    db = SessionLocal()
    try:
        if (
            db.scalar(select(User.id).where(User.identifiant == identifiant))
            is not None
        ):
            print(f"Un utilisateur avec l'identifiant {identifiant} existe deja.")
            sys.exit(1)
        db.add(
            User(
                identifiant=identifiant,
                nom_affichage=nom,
                password_hash=hash_password(mot_de_passe),
            )
        )
        db.commit()
        print(f"Utilisateur {identifiant} cree.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
