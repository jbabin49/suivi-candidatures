"""
Environnement Alembic.

La configuration de l'application n'est pas dupliquee ici : l'URL de la
base vient de app.config (donc de DATA_DIR) et les metadonnees cibles de
app.models. Un seul endroit decrit le schema, un seul decrit ou il vit.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

from app.config import get_settings
from app.models import Base

config = context.config

# Logging decrit dans alembic.ini. Ignore quand les migrations sont
# appelees par programme depuis init_db() : reconfigurer les loggers au
# demarrage ecraserait ceux d'uvicorn.
if config.config_file_name is not None and config.attributes.get(
    "configure_logger", True
):
    fileConfig(config.config_file_name)

# Metadonnees cibles de l'autogeneration (alembic revision --autogenerate).
target_metadata = Base.metadata

# render_as_batch : SQLite ne sait pas modifier une colonne existante
# (ALTER TABLE ... ALTER COLUMN n'existe pas). En mode batch, Alembic
# reecrit la table (table temporaire, copie, renommage) a la place.
# Indispensable pour les futures migrations, sans effet sur les simples
# creations de tables.
BATCH = True


def _database_url() -> str:
    """
    URL de la base, prise dans la configuration de l'application et
    jamais dans alembic.ini : les migrations suivent ainsi DATA_DIR,
    y compris la base temporaire des tests.
    """
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Genere le SQL des migrations sans se connecter a la base."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=BATCH,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Applique les migrations sur la base."""
    connectable = create_engine(
        _database_url(),
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=BATCH,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
