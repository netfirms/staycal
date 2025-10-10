"""add password reset columns

Revision ID: 20251024_0001
Revises: 20251023_0001
Create Date: 2025-10-24 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251024_0001'
down_revision: Union[str, None] = '20251023_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_users_password_reset_token'), 'users', ['password_reset_token'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_password_reset_token'), table_name='users')
    op.drop_column('users', 'password_reset_expires_at')
    op.drop_column('users', 'password_reset_token')
