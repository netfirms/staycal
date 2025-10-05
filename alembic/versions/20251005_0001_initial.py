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
from datetime import datetime

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

    # Create enums for Postgres (if needed)
    if dialect_name == 'postgresql':
        try:
            sa.Enum('free', 'basic', 'pro', name='planname').create(bind, checkfirst=True)
        except Exception:
            pass
        try:
            sa.Enum('active', 'cancelled', 'expired', name='subscriptionstatus').create(bind, checkfirst=True)
        except Exception:
            pass
        try:
            sa.Enum('tentative', 'confirmed', 'checked_in', 'checked_out', 'cancelled', name='bookingstatus').create(bind, checkfirst=True)
        except Exception:
            pass

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
        status_type = sa.Enum(
            'tentative', 'confirmed', 'checked_in', 'checked_out', 'cancelled',
            name='bookingstatus'
        )
        # on SQLite, Enum maps to VARCHAR by default safely
        op.create_table(
            'bookings',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('room_id', sa.Integer(), nullable=False),
            sa.Column('guest_name', sa.String(length=200), nullable=False),
            sa.Column('guest_contact', sa.String(length=200), nullable=True),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column('price', sa.Numeric(10, 2), nullable=True),
            sa.Column('status', status_type, nullable=False, server_default='tentative'),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.ForeignKeyConstraint(['room_id'], ['rooms.id']),
        )
        op.create_index('ix_bookings_room_id', 'bookings', ['room_id'])
        op.create_index('ix_bookings_start_date', 'bookings', ['start_date'])
        op.create_index('ix_bookings_end_date', 'bookings', ['end_date'])
        # composite index to speed overlaps
        op.create_index('ix_bookings_room_start_end', 'bookings', ['room_id', 'start_date', 'end_date'])

    # subscriptions
    if not _has_table(bind, 'subscriptions'):
        plan_type = sa.Enum('free', 'basic', 'pro', name='planname')
        status_type = sa.Enum('active', 'cancelled', 'expired', name='subscriptionstatus')
        op.create_table(
            'subscriptions',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('owner_id', sa.Integer(), nullable=False),
            sa.Column('plan_name', plan_type, nullable=False, server_default='free'),
            sa.Column('status', status_type, nullable=False, server_default='active'),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        )
        # unique owner per subscription (enforced by index for portability)
        op.create_unique_constraint('uq_subscription_owner', 'subscriptions', ['owner_id'])

    # Ensure FKs if tables pre-existed without them (best-effort: skip to avoid errors)
    # Indexes already handled above.


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # Drop in dependency order
    if _has_table(bind, 'subscriptions'):
        try:
            op.drop_constraint('uq_subscription_owner', 'subscriptions', type_='unique')
        except Exception:
            pass
        op.drop_table('subscriptions')

    if _has_table(bind, 'bookings'):
        try:
            op.drop_index('ix_bookings_room_start_end', table_name='bookings')
            op.drop_index('ix_bookings_end_date', table_name='bookings')
            op.drop_index('ix_bookings_start_date', table_name='bookings')
            op.drop_index('ix_bookings_room_id', table_name='bookings')
        except Exception:
            pass
        op.drop_table('bookings')

    if _has_table(bind, 'rooms'):
        op.drop_table('rooms')

    if _has_table(bind, 'homestays'):
        op.drop_table('homestays')

    if _has_table(bind, 'users'):
        try:
            op.drop_index('ix_users_email', table_name='users')
            op.drop_index('ix_users_id', table_name='users')
        except Exception:
            pass
        op.drop_table('users')

    # Drop enums on Postgres
    if dialect_name == 'postgresql':
        for enum_name in ('bookingstatus', 'subscriptionstatus', 'planname'):
            try:
                sa.Enum(name=enum_name).drop(bind, checkfirst=True)
            except Exception:
                pass
