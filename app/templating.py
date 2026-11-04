"""
Instance unique de gabarits Jinja2.

Elle etait auparavant reconstruite a l'identique dans chaque module de
routes. Un seul objet permet d'y attacher des variables globales,
disponibles dans tous les gabarits sans avoir a les passer dans le
contexte de chaque route.

auth_locale est la premiere : base.html s'en sert pour n'afficher les
liens de gestion des comptes qu'en mode local, ou ces routes existent.
En mode OIDC elles ne sont pas montees, les liens pointeraient vers des
404 et la gestion des comptes appartient de toute facon au fournisseur
d'identite.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import get_settings

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["auth_locale"] = get_settings().auth_mode == "local"
