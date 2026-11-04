"""
Lanceur applicatif de bureau (pywebview).

Demarre l'application FastAPI sur un serveur local 127.0.0.1 et l'affiche
dans une fenetre native, pour une utilisation sans Docker ni navigateur.

DATA_DIR est pose vers le dossier de donnees standard de l'utilisateur
(propre a chaque OS) AVANT tout import du paquet app : app.config lit
l'environnement des son chargement (get_settings est mis en cache).
"""

from __future__ import annotations

import os
import socket
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn
from platformdirs import user_data_dir

NOM_APP = "SuiviCandidatures"


def configurer_environnement() -> Path:
    """
    Pose DATA_DIR vers le dossier de donnees utilisateur de l'OS, et force
    l'auth locale (OIDC n'a pas de sens pour une appli de bureau mono-
    utilisateur). setdefault : une valeur deja presente reste prioritaire.
    """
    dossier = Path(user_data_dir(NOM_APP, appauthor=False))
    dossier.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DATA_DIR", str(dossier))
    os.environ.setdefault("AUTH_MODE", "local")
    return Path(os.environ["DATA_DIR"])


def port_libre() -> int:
    """Reserve un port ephemere libre sur la boucle locale."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServeurSansSignaux(uvicorn.Server):
    """
    Uvicorn installe par defaut des gestionnaires de signaux, or Python ne
    l'autorise que depuis le thread principal (reserve ici a la boucle
    graphique pywebview). On neutralise donc cette installation.
    """

    def install_signal_handlers(self) -> None:
        pass


def attendre_demarrage(url_sante: str, delai_max: float = 30.0) -> bool:
    """Interroge /healthz jusqu'a reponse 200, ou expiration du delai."""
    echeance = time.monotonic() + delai_max
    while time.monotonic() < echeance:
        try:
            with urllib.request.urlopen(url_sante, timeout=1) as reponse:
                if reponse.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def construire_serveur(app, hote: str, port: int) -> ServeurSansSignaux:
    """Serveur uvicorn local, un seul process (contrainte SQLite)."""
    config = uvicorn.Config(app, host=hote, port=port, log_level="warning")
    return ServeurSansSignaux(config)


def main() -> None:
    configurer_environnement()

    from app.main import app  # apres avoir pose DATA_DIR
    import webview  # import tardif : charge un backend graphique

    hote, port = "127.0.0.1", port_libre()
    base_url = f"http://{hote}:{port}"

    serveur = construire_serveur(app, hote, port)
    thread = threading.Thread(target=serveur.run, name="uvicorn", daemon=True)
    thread.start()

    if not attendre_demarrage(f"{base_url}/healthz"):
        raise RuntimeError("Le serveur local n'a pas demarre dans le delai imparti.")

    webview.create_window(
        "Suivi de candidatures", base_url,
        width=1200, height=800, min_size=(900, 600),
    )
    webview.start()

    serveur.should_exit = True
    thread.join(timeout=5)


if __name__ == "__main__":
    main()
