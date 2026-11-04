"""identifiant de connexion

Renomme users.email en users.identifiant.

L'identifiant de connexion n'a plus a etre une adresse email :
l'application n'envoie aucun courriel et n'offre aucune procedure de
recuperation, la contrainte de format n'achetait donc rien.

Migration ecrite a la main, et non autogeneree. L'autogeneration ne sait
pas reconnaitre un renommage : elle produit un drop_column suivi d'un
add_column, ce qui VIDERAIT la colonne de tous les comptes existants.
alter_column avec new_column_name preserve les donnees.

Mode batch obligatoire : SQLite ne sait pas renommer une colonne portant
une contrainte UNIQUE par un simple ALTER TABLE. Le mode batch recree la
table avec le nouveau nom, recopie les lignes, puis bascule.

Revision ID: b7c1d4e92f10
Revises: a102759961c9
Create Date: 2026-11-04 09:12:03.118422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1d4e92f10'
down_revision: Union[str, Sequence[str], None] = 'a102759961c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Renomme email en identifiant, en conservant les valeurs."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'email',
            new_column_name='identifiant',
            existing_type=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Retour au nom precedent, egalement sans perte."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'identifiant',
            new_column_name='email',
            existing_type=sa.String(length=255),
            existing_nullable=False,
        )
