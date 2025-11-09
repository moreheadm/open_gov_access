"""Add optional meeting link to documents table

Revision ID: 0002add_meeting_link
Revises: 0001add_metadata
Create Date: 2025-11-09 00:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002add_meeting_link'
down_revision: Union[str, Sequence[str], None] = '0001add_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add meeting_id foreign key to documents table."""
    op.add_column('documents', sa.Column('meeting_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_documents_meeting_id'), 'documents', ['meeting_id'], unique=False)
    op.create_foreign_key(
        'fk_documents_meeting_id_meetings',
        'documents',
        'meetings',
        ['meeting_id'],
        ['id']
    )


def downgrade() -> None:
    """Downgrade schema - remove meeting_id foreign key from documents table."""
    op.drop_constraint('fk_documents_meeting_id_meetings', 'documents', type_='foreignkey')
    op.drop_index(op.f('ix_documents_meeting_id'), table_name='documents')
    op.drop_column('documents', 'meeting_id')

