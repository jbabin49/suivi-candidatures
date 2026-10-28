"""
Verifications sur les migrations Alembic.

Quatre garde-fous : la base est bien a la derniere revision apres
init_db(), les migrations decrivent exactement les modeles (une
evolution de modeles.py sans migration correspondante echoue ici), une
base anterieure a l'arrivee d'Alembic est rattrapee sans perte, et ce
rattrapage lui applique bien les migrations posterieures a la premiere.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app import database
from app.config import get_settings
from app.database import _alembic_config, engine, init_db
from app.models import Base, User


def test_base_a_la_derniere_revision() -> None:
    """init_db() laisse la base estampillee a head."""
    init_db()

    head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    assert head is not None

    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == head


def test_aucun_ecart_entre_migrations_et_modeles() -> None:
    """
    Le schema migre correspond aux modeles SQLAlchemy : l'autogeneration
    ne detecte plus aucune difference.
    """
    init_db()

    with engine.connect() as connection:
        contexte = MigrationContext.configure(connection)
        assert compare_metadata(contexte, Base.metadata) == []


@pytest.fixture
def base_pre_alembic(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """
    Base SQLite secondaire simulant une installation anterieure a
    Alembic : les 7 tables du schema initial, et aucune table
    alembic_version.

    Ce schema n'est volontairement pas celui de create_all, qui suit les
    modeles d'aujourd'hui et porterait donc deja les colonnes ajoutees
    par les migrations posterieures a la premiere. Il est construit par
    un upgrade jusqu'a la revision initiale, dont alembic_version est
    ensuite effacee : on obtient exactement le schema de l'epoque, celui
    que create_all produisait alors, et sans trace d'Alembic.

    L'isolation demande d'aligner deux choses sur ce fichier temporaire,
    sans quoi init_db() inspecterait une base et migrerait l'autre :
    le moteur de app.database, lu par _schema_anterieur_a_alembic(), et
    DATA_DIR, d'ou migrations/env.py tire l'URL via app.config (dont le
    cache est donc vide). La base de session des autres tests n'est pas
    touchee, et tout est restaure a la sortie.
    """
    repertoire = tempfile.mkdtemp(prefix="candidatures-pre-alembic-")
    monkeypatch.setenv("DATA_DIR", repertoire)
    get_settings.cache_clear()

    moteur = create_engine(
        f"sqlite:///{Path(repertoire) / 'candidatures.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(database, "engine", moteur)

    command.upgrade(_alembic_config(), database.REVISION_INITIALE)
    with moteur.begin() as connection:
        connection.exec_driver_sql("DROP TABLE alembic_version")

    try:
        yield moteur
    finally:
        moteur.dispose()
        get_settings.cache_clear()
        shutil.rmtree(repertoire, ignore_errors=True)


def _revision_courante(moteur: Engine) -> str | None:
    with moteur.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def _colonnes(moteur: Engine, table: str) -> set[str]:
    return {colonne["name"] for colonne in inspect(moteur).get_columns(table)}


def _head() -> str:
    head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    assert head is not None
    return head


def test_base_pre_alembic_est_tamponnee_puis_migree(base_pre_alembic: Engine) -> None:
    """
    Une base existante sans alembic_version est reconnue comme
    anterieure a Alembic, estampillee, puis migree, sans perdre ses
    donnees ni voir ses tables recreees.
    """
    tables_avant = set(inspect(base_pre_alembic).get_table_names())
    assert tables_avant == set(Base.metadata.tables)
    assert "alembic_version" not in tables_avant
    assert database._schema_anterieur_a_alembic() is True
    assert _revision_courante(base_pre_alembic) is None

    # Donnee preexistante : la migration ne doit pas repartir d'une base vide.
    with Session(base_pre_alembic) as db:
        db.add(
            User(
                email="avant-alembic@local",
                nom_affichage="Avant Alembic",
                password_hash="x",
            )
        )
        db.commit()

    database.init_db()

    assert _revision_courante(base_pre_alembic) == _head()
    assert set(inspect(base_pre_alembic).get_table_names()) == tables_avant | {
        "alembic_version"
    }
    with Session(base_pre_alembic) as db:
        assert db.query(User).filter_by(email="avant-alembic@local").count() == 1

    with base_pre_alembic.connect() as connection:
        contexte = MigrationContext.configure(connection)
        assert compare_metadata(contexte, Base.metadata) == []


def test_init_db_est_idempotent_sur_base_pre_alembic(base_pre_alembic: Engine) -> None:
    """
    Deux init_db() de plus apres le rattrapage ne changent rien : la
    base n'est plus vue comme anterieure a Alembic, et reste a head.
    """
    database.init_db()

    database.init_db()
    database.init_db()

    assert database._schema_anterieur_a_alembic() is False
    assert _revision_courante(base_pre_alembic) == _head()
    with base_pre_alembic.connect() as connection:
        contexte = MigrationContext.configure(connection)
        assert compare_metadata(contexte, Base.metadata) == []


def test_base_pre_alembic_recoit_les_migrations_posterieures(
    base_pre_alembic: Engine,
) -> None:
    """
    Garde-fou contre un retour a stamp("head").

    Une base anterieure a Alembic est au niveau de la migration
    initiale, pas de la derniere : la tamponner a head la marquerait
    comme deja a jour de toutes les migrations, et celles posterieures
    a la premiere ne lui seraient jamais appliquees.

    Verification par l'effet : la base part du schema initial, donc sans
    la colonne sans_relance_possible ajoutee par la deuxieme migration.
    Si init_db() tamponnait head, l'upgrade n'aurait rien a appliquer et
    la colonne resterait absente.
    """
    assert "sans_relance_possible" not in _colonnes(
        base_pre_alembic, "candidatures"
    )

    database.init_db()

    assert _revision_courante(base_pre_alembic) == _head()
    assert "sans_relance_possible" in _colonnes(base_pre_alembic, "candidatures")
