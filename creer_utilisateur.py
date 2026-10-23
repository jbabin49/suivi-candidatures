"""
Creation d'un utilisateur en mode auth locale, depuis la ligne de commande.

Utile pour creer le premier compte sans passer par les variables
ADMIN_EMAIL / ADMIN_PASSWORD, ou pour ajouter un utilisateur ensuite.

Usage (depuis la racine du projet) :
    python creer_utilisateur.py <email> <nom_affichage>

Le mot de passe est demande de maniere interactive (non affiche).

En Docker :
    docker compose exec app python creer_utilisateur.py <email> <nom>
"""

from __future__ import annotations

import getpass
import sys

from sqlalchemy import select

from app.auth.local import hash_password
from app.database import SessionLocal, init_db
from app.models import User


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage : python creer_utilisateur.py <email> <nom_affichage>")
        sys.exit(1)

    email, nom = sys.argv[1], sys.argv[2]
    mot_de_passe = getpass.getpass("Mot de passe : ")
    if not mot_de_passe:
        print("Mot de passe vide, abandon.")
        sys.exit(1)

    init_db()
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            print(f"Un utilisateur avec l'email {email} existe deja.")
            sys.exit(1)
        db.add(
            User(
                email=email,
                nom_affichage=nom,
                password_hash=hash_password(mot_de_passe),
            )
        )
        db.commit()
        print(f"Utilisateur {email} cree.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
