"""
Test de demarrage headless du lanceur de bureau (desktop.py).

Verifie qu'avec un DATA_DIR redirige, le serveur uvicorn construit par
desktop.py demarre bien dans un thread, que /healthz repond 200 et que
la base SQLite est creee a l'emplacement redirige.

Le scenario tourne dans un sous-processus. app.config met get_settings en
cache des le premier import, et conftest.py a deja pose son propre
DATA_DIR avant tout import de l'application : poser une autre valeur dans
ce processus n'aurait aucun effet. Un sous-processus repart d'un
interpreteur vierge, donc d'une configuration vraiment redirigee.

webview n'est jamais importe : la CI n'a pas d'affichage. C'est tout
l'interet d'avoir garde l'import du backend graphique dans main() et non
en tete de module.

Le second test couvre le mode smoke-test (SMOKE_TEST=1), celui que la CI
execute sur le binaire gele : il lance desktop.py en entier, point
d'entree compris, et verifie qu'il sort 0 sans fenetre. Ici depuis les
sources, ce qui n'eprouve que le chemin logique ; l'empaquetage lui-meme
ne peut se verifier que sur le binaire, donc en CI.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# Scenario execute dans le sous-processus. Les assertions y sont faites
# sur place : seul le code de retour et la sortie remontent au test.
SCENARIO = """
import os, sys, threading
from pathlib import Path

from desktop import attendre_demarrage, construire_serveur, port_libre

from app.main import app

hote, port = "127.0.0.1", port_libre()
serveur = construire_serveur(app, hote, port)
thread = threading.Thread(target=serveur.run, name="uvicorn", daemon=True)
thread.start()
try:
    base_url = "http://%s:%d" % (hote, port)
    assert attendre_demarrage(base_url + "/healthz"), "demarrage expire"

    import json, urllib.request

    with urllib.request.urlopen(base_url + "/healthz", timeout=5) as reponse:
        assert reponse.status == 200, reponse.status
        assert json.load(reponse) == {"status": "ok"}

    from app.config import get_settings

    settings = get_settings()
    attendu = Path(os.environ["DATA_DIR"])
    assert settings.data_dir == attendu, settings.data_dir
    assert settings.db_path.exists(), settings.db_path
finally:
    serveur.should_exit = True
    thread.join(timeout=10)

print("OK")
"""


def test_demarrage_headless_avec_data_dir_redirige():
    with tempfile.TemporaryDirectory(prefix="candidatures-desktop-") as dossier:
        environnement = {
            **os.environ,
            "DATA_DIR": dossier,
            "AUTH_MODE": "local",
            # Le .env du poste de developpement ne doit pas s'appliquer :
            # il pourrait rediriger DATA_DIR ailleurs (pydantic-settings
            # donne la priorite a l'environnement, mais autant ne pas
            # dependre de son contenu pour les autres variables).
            "PYTHONPATH": str(RACINE),
        }
        resultat = subprocess.run(
            [sys.executable, "-c", SCENARIO],
            cwd=RACINE,
            env=environnement,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert resultat.returncode == 0, resultat.stdout + resultat.stderr
        assert "OK" in resultat.stdout

        # La base est bien dans le DATA_DIR redirige, et nulle part ailleurs.
        assert (Path(dossier) / "candidatures.db").exists()
        assert (Path(dossier) / "uploads").is_dir()


def test_mode_smoke_sort_zero_et_confirme_la_migration():
    """
    SMOKE_TEST=1 : desktop.py va jusqu'au bout de son parcours de
    demarrage sans fenetre, et sort 0 en ayant confirme la migration.

    Le module webview est rendu introuvable (PYTHONPATH pointe sur un
    dossier contenant un webview.py qui leve a l'import) : si le mode
    smoke tentait de l'importer, le test echouerait. C'est la garantie
    que le mode reste utilisable sur un runner sans affichage.
    """
    with tempfile.TemporaryDirectory(prefix="candidatures-smoke-") as dossier:
        piege = Path(dossier) / "piege"
        piege.mkdir()
        (piege / "webview.py").write_text(
            'raise AssertionError("le mode smoke ne doit pas importer webview")',
            encoding="utf-8",
        )
        donnees = Path(dossier) / "donnees"

        resultat = subprocess.run(
            [sys.executable, "desktop.py"],
            cwd=RACINE,
            env={
                **os.environ,
                "SMOKE_TEST": "1",
                "DATA_DIR": str(donnees),
                "AUTH_MODE": "local",
                # Le piege d'abord : il doit masquer un vrai pywebview
                # installe sur le poste.
                "PYTHONPATH": os.pathsep.join([str(piege), str(RACINE)]),
            },
            capture_output=True,
            text=True,
            timeout=120,
        )

        sortie = resultat.stdout + resultat.stderr
        assert resultat.returncode == 0, sortie
        assert "SMOKE OK" in sortie, sortie
        # DATA_DIR n'existait pas : le lanceur l'a cree, migre et peuple.
        assert (donnees / "candidatures.db").exists()
        assert (donnees / "uploads").is_dir()
