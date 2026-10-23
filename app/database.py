"""
Connexion a la base SQLite et gestion des sessions SQLAlchemy.

Le mode WAL (Write-Ahead Logging) est active a chaque connexion : il
ameliore nettement la concurrence lecture/ecriture de SQLite, les
lectures ne bloquant plus les ecritures. Suffisant pour un usage solo
ou a quelques utilisateurs.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base

settings = get_settings()

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


def init_db() -> None:
    """
    Cree les tables si elles n'existent pas. Appele au demarrage de
    l'application. Suffisant tant que le schema n'evolue pas ; une
    gestion de migrations (Alembic) pourra etre ajoutee plus tard.
    """
    Base.metadata.create_all(bind=engine)


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
