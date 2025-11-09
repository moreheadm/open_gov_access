"""Merge migration branches

Revision ID: c0a7b6d2edc5
Revises: 0002add_meeting_link, 3b953b8de0dd
Create Date: 2025-11-09 13:20:14.425912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0a7b6d2edc5'
down_revision: Union[str, Sequence[str], None] = ('0002add_meeting_link', '3b953b8de0dd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
