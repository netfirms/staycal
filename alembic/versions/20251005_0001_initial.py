"""
Initial schema for StayCal

Revision ID: 20251005_0001
Revises: 
Create Date: 2025-10-05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251005_0001'
down_revision = None
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    try:
        insp = inspect(bind)
        return insp.has_table(name)
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # Define ENUM types for use in table creation
    planname_enum = sa.Enum('free', 'basic', 'pro', name='planname')
    subscriptionstatus_enum = sa.Enum('active', 'cancelled', 'expired', name='subscriptionstatus')
    bookingstatus_enum = sa.Enum('tentative', 'confirmed', 'checked_in', 'checked_out', 'cancelled', name='bookingstatus')

    # users
    if not _has_table(bind, 'users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False, unique=True),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=False, server_default='owner'),
            sa.Column('homestay_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index('ix_users_id', 'users', ['id'])
        op.create_index('ix_users_email', 'users', ['email'])

    # homestays
    if not _has_table(bind, 'homestays'):
        op.create_table(
            'homestays',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('owner_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('address', sa.String(length=300), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        )

    # rooms
    if not _has_table(bind, 'rooms'):
        op.create_table(
            'rooms',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('homestay_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('capacity', sa.Integer(), nullable=False, server_default='2'),
            sa.Column('default_rate', sa.Numeric(10, 2), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.Column('ota_ical_url', sa.String(length=500), nullable=True),
            sa.ForeignKeyConstraint(['homestay_id'], ['homestays.id']),
        )

    # bookings
    if not _has_table(bind, 'bookings'):
        op.create_table(
            'bookings',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('room_id', sa.Integer(), nullable=False),
            sa.Column('guest_name', sa.String(length=200), nullable=False),
            sa.Column('guest_contact', sa.String(length=200), nullable=True),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column('price', sa.Numeric(10, 2), nullable=True),
            sa.Column('status', bookingstatus_enum, nullable=False, server_default='tentative'),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.ForeignKeyConstraint(['room_id'], ['rooms.id']),
        )
        op.create_index('ix_bookings_room_id', 'bookings', ['room_id'])
        op.create_index('ix_bookings_start_date', 'bookings', ['start_date'])
        op.create_index('ix_bookings_end_date', 'bookings', ['end_date'])
        op.create_index('ix_bookings_room_start_end', 'bookings', ['room_id', 'start_date', 'end_date'])

    # subscriptions
    if not _has_table(bind, 'subscriptions'):
        op.create_table(
            'subscriptions',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('owner_id', sa.Integer(), nullable=False),
            sa.Column('plan_name', planname_enum, nullable=False, server_default='free'),
            sa.Column('status', subscriptionstatus_enum, nullable=False, server_default='active'),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        )
        op.create_unique_constraint('uq_subscription_owner', 'subscriptions', ['owner_id'])


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.drop_table('subscriptions')
    op.drop_table('bookings')
    op.drop_table('rooms')
    op.drop_table('homestays')
    op.drop_table('users')

    if dialect_name == 'postgresql':
        sa.Enum(name='bookingstatus').drop(bind, checkfirst=True)
        sa.Enum(name='subscriptionstatus').drop(bind, checkfirst=True)
        sa.Enum(name='planname').drop(bind, checkfirst=True)
