"""merge heads before rack shelf migration

Revision ID: 4bc049c65507
Revises: 37f38e1e9627, 6309b65cdd6d
Create Date: 2026-07-06 15:46:50.822909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bc049c65507'
down_revision: Union[str, None] = ('37f38e1e9627', '6309b65cdd6d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
