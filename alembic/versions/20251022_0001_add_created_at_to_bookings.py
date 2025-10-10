"""add created_at to bookings

Revision ID: 20251022_0001
Revises: 20251021_0001
Create Date: 2025-10-22 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251022_0001'
down_revision: Union[str, None] = '20251021_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bookings', sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))
    # Backfill existing rows with the start_date as a reasonable default
    op.execute('UPDATE bookings SET created_at = start_date WHERE created_at IS NULL')
    # Now, make the column non-nullable
    op.alter_column('bookings', 'created_at', nullable=False)


def downgrade() -> None:
    op.drop_column('bookings', 'created_at')
