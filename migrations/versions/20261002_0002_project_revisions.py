"""project revision history"""
from alembic import op
import sqlalchemy as sa
revision="20261002_0002"; down_revision="20261002_0001"; branch_labels=None; depends_on=None
def upgrade():
    bind=op.get_bind(); inspector=sa.inspect(bind)
    if "project_revisions" not in inspector.get_table_names():
        op.create_table("project_revisions",sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("version",sa.Integer(),nullable=False),sa.Column("snapshot",sa.JSON(),nullable=False),sa.Column("owner_id",sa.String(64),nullable=False),sa.Column("id",sa.String(36),primary_key=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("project_id","version"))
        op.create_index("ix_project_revisions_project_id","project_revisions",["project_id"]); op.create_index("ix_project_revisions_owner_id","project_revisions",["owner_id"])
def downgrade():
    op.drop_table("project_revisions")
