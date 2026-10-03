"""initial schema"""
from alembic import op
from app.core.database import Base
from app import models
revision="20261002_0001"; down_revision=None; branch_labels=None; depends_on=None
def upgrade(): Base.metadata.create_all(bind=op.get_bind(),checkfirst=True)
def downgrade(): Base.metadata.drop_all(bind=op.get_bind(),checkfirst=True)

