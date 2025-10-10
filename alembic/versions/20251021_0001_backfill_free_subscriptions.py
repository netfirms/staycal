"""Backfill free subscriptions for existing users

Revision ID: 20251021_0001
Revises: 20251017_0001
Create Date: 2025-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251021_0001'
down_revision: Union[str, None] = '20251017_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Session = sa.orm.sessionmaker(bind=bind)
    session = Session()

    # Get the free plan ID
    free_plan_result = session.execute(sa.text("SELECT id FROM plans WHERE name = 'free'")).fetchone()
    if not free_plan_result:
        # If free plan doesn't exist for some reason, skip the migration
        return

    free_plan_id = free_plan_result[0]

    # Find users without a subscription
    users_without_sub = session.execute(
        sa.text("""
            SELECT users.id FROM users 
            LEFT JOIN subscriptions ON users.id = subscriptions.owner_id 
            WHERE subscriptions.id IS NULL
        """)
    ).fetchall()

    # Create a default subscription for them
    for user in users_without_sub:
        session.execute(
            sa.text("INSERT INTO subscriptions (owner_id, plan_id, status) VALUES (:owner_id, :plan_id, 'ACTIVE')"),
            {"owner_id": user[0], "plan_id": free_plan_id}
        )
    
    session.commit()


def downgrade() -> None:
    # This is a data migration, so a downgrade might not be necessary.
    # However, if you wanted to revert, you could delete the subscriptions that were added.
    pass
