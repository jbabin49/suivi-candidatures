"""
Lanceur applicatif de bureau (pywebview).

Demarre l'application FastAPI sur un serveur local 127.0.0.1 et l'affiche
dans une fenetre native, pour une utilisation sans Docker ni navigateur.

DATA_DIR est pose vers le dossier de donnees standard de l'utilisateur
(propre a chaque OS) AVANT tout import du paquet app : app.config lit
l'environnement des son chargement (get_settings est mis en cache).

Mode smoke-test (SMOKE_TEST=1)
-----------------------------
Le meme parcours de demarrage, mais sans fenetre : uvicorn est lance,
/healthz interroge, la migration Alembic verifiee, puis le processus
sort (0 si tout va bien, 1 sinon). C'est ce mode que la CI execute sur
le binaire GELE, pour prouver a chaque build que l'empaquetage tient :
resolution de alembic.ini et de migrations/ dans _MEIPASS, creation du
DATA_DIR, demarrage effectif du serveur.

La fenetre reste volontairement hors du test : elle demande un affichage
et un moteur de rendu systeme, absents d'un runner de CI. C'est pourquoi
l'import de webview n'a lieu qu'APRES le point de sortie du mode smoke.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn
from platformdirs import user_data_dir

NOM_APP = "SuiviCandidatures"

# Nom du journal ecrit dans DATA_DIR par le mode smoke-test. Un binaire
# construit avec console=False n'a ni stdout ni stderr sous Windows
# (sys.stderr vaut None) : sans ce fichier, un echec en CI serait muet.
JOURNAL_SMOKE = "smoke-test.log"


def mode_smoke() -> bool:
    """Vrai si SMOKE_TEST demande le demarrage sans fenetre."""
    return os.environ.get("SMOKE_TEST", "") == "1"


def configurer_environnement() -> Path:
    """
    Pose DATA_DIR vers le dossier de donnees utilisateur de l'OS, et force
    l'auth locale (OIDC n'a pas de sens pour une appli de bureau mono-
    utilisateur). setdefault : une valeur deja presente reste prioritaire.

    Un DATA_DIR deja pose dans l'environnement est donc respecte tel quel,
    et c'est lui seul qui est cree : la CI le pointe vers un dossier
    temporaire, inutile d'aller creer en plus le dossier utilisateur de
    l'OS au passage.
    """
    defaut = user_data_dir(NOM_APP, appauthor=False)
    dossier = Path(os.environ.get("DATA_DIR") or defaut)
    dossier.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DATA_DIR", str(dossier))
    os.environ.setdefault("AUTH_MODE", "local")
    return Path(os.environ["DATA_DIR"])


def journaliser(message: str, dossier_donnees: Path | None = None) -> None:
    """
    Trace un message du mode smoke-test sur stderr ET dans un fichier du
    DATA_DIR. Les deux voies sont facultatives : un binaire sans console
    n'a pas de stderr, et le DATA_DIR peut etre inaccessible justement
    quand il y a quelque chose a signaler. Aucune des deux ne doit faire
    echouer le diagnostic qu'elle sert a transmettre.
    """
    if sys.stderr is not None:
        print(message, file=sys.stderr, flush=True)
    if dossier_donnees is None:
        return
    try:
        with (dossier_donnees / JOURNAL_SMOKE).open("a", encoding="utf-8") as fichier:
            fichier.write(message + "\n")
    except OSError:
        pass


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


def attendre_demarrage(
    url_sante: str,
    delai_max: float = 30.0,
    thread: threading.Thread | None = None,
) -> bool:
    """
    Interroge /healthz jusqu'a reponse 200, ou expiration du delai.

    thread, s'il est fourni, est celui qui porte le serveur : sa mort
    signifie qu'uvicorn a leve (migration en echec, port pris...) et que
    plus rien ne repondra. On abandonne alors sans attendre l'echeance,
    pour que le diagnostic arrive tout de suite.
    """
    echeance = time.monotonic() + delai_max
    while time.monotonic() < echeance:
        try:
            with urllib.request.urlopen(url_sante, timeout=1) as reponse:
                if reponse.status == 200:
                    return True
        except Exception:
            if thread is not None and not thread.is_alive():
                return False
            time.sleep(0.15)
    return False


def revision_appliquee() -> str | None:
    """
    Revision Alembic enregistree dans la base, ou None si la table
    alembic_version est absente ou vide.

    Lecture via le moteur de app.database : c'est la meme base que celle
    que l'application vient de migrer, URL et dialecte compris, sans
    reconstruire un chemin de fichier en parallele.
    """
    from sqlalchemy import inspect, text

    from app.database import engine

    if "alembic_version" not in inspect(engine).get_table_names():
        return None
    with engine.connect() as connexion:
        requete = connexion.execute(text("SELECT version_num FROM alembic_version"))
        return requete.scalar()


def revision_attendue() -> str:
    """
    Revision de tete des scripts de migration embarques.

    Passe par _alembic_config() de app.database, donc par le meme
    script_location que l'upgrade du demarrage : dans un binaire gele,
    c'est migrations/ extrait dans _MEIPASS. Echouer ici est en soi un
    defaut d'empaquetage digne d'etre signale.
    """
    from alembic.script import ScriptDirectory

    from app.database import _alembic_config

    return ScriptDirectory.from_config(_alembic_config()).get_current_head()


def construire_serveur(app, hote: str, port: int) -> ServeurSansSignaux:
    """Serveur uvicorn local, un seul process (contrainte SQLite)."""
    config = uvicorn.Config(app, host=hote, port=port, log_level="warning")
    return ServeurSansSignaux(config)


def verifier_smoke(dossier_donnees: Path, base_url: str, demarre: bool) -> int:
    """
    Controles du mode smoke-test, une fois le serveur lance : /healthz a
    repondu 200, et la base porte une revision Alembic (donc les
    migrations ont bien ete trouvees et appliquees). Renvoie le code de
    sortie du processus.
    """
    if not demarre:
        journaliser(
            f"SMOKE ECHEC : {base_url}/healthz n'a pas repondu 200 "
            "dans le delai imparti.",
            dossier_donnees,
        )
        return 1

    try:
        revision = revision_appliquee()
    except Exception as erreur:
        journaliser(
            f"SMOKE ECHEC : lecture de alembic_version impossible ({erreur!r}).",
            dossier_donnees,
        )
        return 1

    if not revision:
        journaliser(
            "SMOKE ECHEC : la base ne porte aucune revision Alembic "
            "(table alembic_version absente ou vide), la migration n'a pas eu lieu.",
            dossier_donnees,
        )
        return 1

    tete = revision_attendue()
    if revision != tete:
        journaliser(
            f"SMOKE ECHEC : base en revision {revision}, tete attendue {tete} : "
            "la base n'est pas a jour du schema embarque.",
            dossier_donnees,
        )
        return 1

    journaliser(
        f"SMOKE OK : healthz 200, DATA_DIR {dossier_donnees}, revision {revision}.",
        dossier_donnees,
    )
    return 0


def main() -> int:
    dossier_donnees = configurer_environnement()

    from app.main import app  # apres avoir pose DATA_DIR

    hote, port = "127.0.0.1", port_libre()
    base_url = f"http://{hote}:{port}"

    serveur = construire_serveur(app, hote, port)
    thread = threading.Thread(target=serveur.run, name="uvicorn", daemon=True)
    thread.start()

    demarre = attendre_demarrage(f"{base_url}/healthz", thread=thread)

    # Point de sortie du mode smoke-test, AVANT tout import graphique :
    # webview charge un backend natif (WebKit, WebView2) qu'un runner de
    # CI headless n'a pas. Le mode smoke doit pouvoir s'en passer.
    if mode_smoke():
        code = verifier_smoke(dossier_donnees, base_url, demarre)
        serveur.should_exit = True
        thread.join(timeout=5)
        return code

    if not demarre:
        raise RuntimeError("Le serveur local n'a pas demarre dans le delai imparti.")

    import webview  # import tardif : charge un backend graphique

    webview.create_window(
        "Suivi de candidatures", base_url,
        width=1200, height=800, min_size=(900, 600),
    )
    webview.start()

    serveur.should_exit = True
    thread.join(timeout=5)
    return 0


def executer_smoke() -> int:
    """
    Enveloppe du mode smoke-test : toute exception devient un message et
    un code 1.

    Indispensable, et pas seulement pour la lisibilite : le binaire est
    construit en mode fenetre (console=False, disable_windowed_traceback
    a faux), donc une exception non rattrapee y ouvre une boite de
    dialogue Windows. Un job de CI, qui n'a personne pour la fermer,
    resterait bloque jusqu'a son delai maximal au lieu d'echouer net.
    """
    dossier_donnees = Path(os.environ.get("DATA_DIR") or ".")
    try:
        return main()
    except BaseException as erreur:  # noqa: BLE001 - diagnostic, puis code 1
        import traceback

        journaliser(
            f"SMOKE ECHEC : exception au demarrage ({erreur!r})\n"
            + traceback.format_exc(),
            dossier_donnees,
        )
        return 1


if __name__ == "__main__":
    sys.exit(executer_smoke() if mode_smoke() else main())
