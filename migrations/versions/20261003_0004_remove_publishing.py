"""remove publishing tables"""
from alembic import op
import sqlalchemy as sa

revision = "20261003_0004"
down_revision = "20261002_0003"
branch_labels = None
depends_on = None


def upgrade():
    if "publications" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("publications")


def downgrade():
    op.create_table(
        "publications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("export_id", sa.String(36), sa.ForeignKey("exports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(40), nullable=False),
        sa.Column("external_id", sa.String(200)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("owner_id", sa.String(64), nullable=False),
    )
