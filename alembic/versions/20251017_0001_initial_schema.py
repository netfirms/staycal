"""Create initial schema

Revision ID: 20251017_0001
Revises: 
Create Date: 2025-10-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '20251017_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _has_table(bind, name: str) -> bool:
    try:
        insp = inspect(bind)
        return insp.has_table(name)
    except Exception:
        return False

def upgrade() -> None:
    # ### Create all tables and ENUM types ###
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # Define ENUM types for use in table creation
    planname_enum = sa.Enum('free', 'basic', 'pro', name='planname')
    subscriptionstatus_enum = sa.Enum('ACTIVE', 'CANCELLED', 'EXPIRED', name='subscriptionstatus')
    bookingstatus_enum = sa.Enum('TENTATIVE', 'CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT', 'CANCELLED', name='bookingstatus')


    # Create users table
    if not _has_table(bind, 'users'):
        op.create_table('users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=20), server_default='owner', nullable=False),
            sa.Column('homestay_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('currency', sa.String(length=8), server_default='USD', nullable=False),
            sa.Column('is_verified', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('verification_token', sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
        op.create_index(op.f('ix_users_verification_token'), 'users', ['verification_token'], unique=True)

    # Create plans table and seed it
    if not _has_table(bind, 'plans'):
        plans_table = op.create_table('plans',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('price_monthly', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('price_yearly', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('room_limit', sa.Integer(), nullable=False),
            sa.Column('user_limit', sa.Integer(), nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index(op.f('ix_plans_id'), 'plans', ['id'], unique=False)
        op.create_index(op.f('ix_plans_name'), 'plans', ['name'], unique=True)

        op.bulk_insert(plans_table, [
            {'name': 'free', 'price_monthly': 0, 'price_yearly': 0, 'room_limit': 2, 'user_limit': 1, 'is_active': True},
            {'name': 'basic', 'price_monthly': 249, 'price_yearly': 2490, 'room_limit': 10, 'user_limit': 5, 'is_active': True},
            {'name': 'pro', 'price_monthly': 699, 'price_yearly': 6990, 'room_limit': 1000, 'user_limit': 1000, 'is_active': True},
        ])

    # Create subscriptions table
    if not _has_table(bind, 'subscriptions'):
        op.create_table('subscriptions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('owner_id', sa.Integer(), nullable=False),
            sa.Column('status', subscriptionstatus_enum, server_default='ACTIVE', nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('owner_id')
        )
        op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)

    # Create homestays table
    if not _has_table(bind, 'homestays'):
        op.create_table('homestays',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('owner_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('address', sa.String(length=300), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_homestays_id'), 'homestays', ['id'], unique=False)

    # Create rooms table
    if not _has_table(bind, 'rooms'):
        op.create_table('rooms',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('homestay_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('capacity', sa.Integer(), server_default='2', nullable=False),
            sa.Column('default_rate', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.Column('ota_ical_url', sa.String(length=500), nullable=True),
            sa.ForeignKeyConstraint(['homestay_id'], ['homestays.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_rooms_id'), 'rooms', ['id'], unique=False)

    # Create bookings table
    if not _has_table(bind, 'bookings'):
        op.create_table('bookings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('room_id', sa.Integer(), nullable=False),
            sa.Column('guest_name', sa.String(length=200), nullable=False),
            sa.Column('guest_contact', sa.String(length=200), nullable=True),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('status', bookingstatus_enum, server_default='TENTATIVE', nullable=False),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_bookings_end_date'), 'bookings', ['end_date'], unique=False)
        op.create_index(op.f('ix_bookings_id'), 'bookings', ['id'], unique=False)
        op.create_index(op.f('ix_bookings_room_id'), 'bookings', ['room_id'], unique=False)
        op.create_index(op.f('ix_bookings_start_date'), 'bookings', ['start_date'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    op.drop_table('bookings')
    op.drop_table('rooms')
    op.drop_table('homestays')
    op.drop_table('subscriptions')
    op.drop_table('plans')
    op.drop_table('users')

    # Drop ENUM types for PostgreSQL
    if dialect_name == 'postgresql':
        sa.Enum(name='bookingstatus').drop(bind, checkfirst=True)
        sa.Enum(name='subscriptionstatus').drop(bind, checkfirst=True)
        sa.Enum(name='planname').drop(bind, checkfirst=True)
