"""javascript source option"""
from alembic import op
import sqlalchemy as sa
revision="20261002_0003"; down_revision="20261002_0002"; branch_labels=None; depends_on=None
def upgrade():
    columns={column["name"] for column in sa.inspect(op.get_bind()).get_columns("sources")}
    if "render_javascript" not in columns: op.add_column("sources",sa.Column("render_javascript",sa.Boolean(),nullable=False,server_default=sa.false()))
def downgrade(): op.drop_column("sources","render_javascript")
