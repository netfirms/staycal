"""add invitation token to users

Revision ID: 20251023_0001
Revises: 20251022_0001
Create Date: 2025-10-23 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251023_0001'
down_revision: Union[str, None] = '20251022_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('invitation_token', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_invitation_token'), 'users', ['invitation_token'], unique=True)
    op.alter_column('users', 'hashed_password', existing_type=sa.VARCHAR(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'hashed_password', existing_type=sa.VARCHAR(length=255), nullable=False)
    op.drop_index(op.f('ix_users_invitation_token'), table_name='users')
    op.drop_column('users', 'invitation_token')
