"""Add metadata column to documents table

Revision ID: 0001add_metadata
Revises: 30c145fd0efb
Create Date: 2025-11-09 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001add_metadata'
down_revision: Union[str, Sequence[str], None] = '30c145fd0efb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add doc_metadata column to documents table."""
    op.add_column('documents', sa.Column('doc_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - remove doc_metadata column from documents table."""
    op.drop_column('documents', 'doc_metadata')

