"""
Connexion a la base SQLite, gestion des sessions SQLAlchemy et mise a
niveau du schema.

Le mode WAL (Write-Ahead Logging) est active a chaque connexion : il
ameliore nettement la concurrence lecture/ecriture de SQLite, les
lectures ne bloquant plus les ecritures. Suffisant pour un usage solo
ou a quelques utilisateurs.

Le schema n'est plus cree par create_all mais par les migrations
Alembic de migrations/versions, appliquees au demarrage par init_db().
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# Fichier de configuration Alembic, a la racine du projet (un niveau
# au-dessus du paquet app). Chemin absolu : les migrations doivent
# s'appliquer quel que soit le repertoire courant du processus.
ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"

# Premiere revision Alembic, celle qui decrit le schema tel qu'il etait
# cree par create_all. Une base anterieure a l'arrivee d'Alembic est
# estampillee a cette revision, et non a head : head la marquerait comme
# deja a jour de toutes les migrations, donc les migrations posterieures
# a la premiere ne lui seraient jamais appliquees. L'upgrade head qui
# suit le stamp s'en charge.
REVISION_INITIALE = "a263898f2484"

# check_same_thread=False : requis par SQLite avec le pool de connexions
# de SQLAlchemy, FastAPI pouvant servir les requetes sur plusieurs threads.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Active WAL et les contraintes de cles etrangeres a chaque connexion."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _alembic_config() -> Config:
    """
    Configuration Alembic du projet. L'URL de la base n'est pas reprise
    ici : migrations/env.py la lit dans app.config, donc la meme que
    celle du moteur ci-dessus.

    configure_logger a faux : env.py n'applique alors pas la section
    logging de alembic.ini, qui ecraserait les loggers d'uvicorn.
    """
    config = Config(str(ALEMBIC_INI))
    config.attributes["configure_logger"] = False
    return config


def _schema_anterieur_a_alembic() -> bool:
    """
    Vraie pour une base creee par l'ancien create_all : des tables
    existent, mais aucune version Alembic n'est enregistree.
    """
    tables = inspect(engine).get_table_names()
    return bool(tables) and "alembic_version" not in tables


def init_db() -> None:
    """
    Met la base au niveau du dernier schema connu, en appliquant les
    migrations Alembic. Appele au demarrage de l'application.

    Une base absente ou vide est entierement creee par la migration
    initiale. Une base anterieure a l'arrivee d'Alembic a deja ses
    tables, creees par create_all : elle est estampillee a la revision
    initiale, qui decrit exactement ce meme schema, sinon la migration
    tenterait de recreer des tables existantes. Les migrations suivantes
    s'appliquent ensuite normalement, par l'upgrade head.
    """
    config = _alembic_config()
    if _schema_anterieur_a_alembic():
        command.stamp(config, REVISION_INITIALE)
    command.upgrade(config, "head")


def get_db() -> Generator[Session, None, None]:
    """
    Dependance FastAPI : fournit une session par requete et la ferme
    systematiquement a la fin, meme en cas d'erreur.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
