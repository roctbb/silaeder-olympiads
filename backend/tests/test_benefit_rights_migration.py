import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c38e91a7d420_add_benefit_right_flags.py"
)


def _migration_module():
    spec = importlib.util.spec_from_file_location("benefit_rights_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_benefit_right_flags_migration_backfills_and_downgrades(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    metadata = sa.MetaData()
    sa.Table(
        "benefits",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("benefit_type", sa.String(length=40), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO benefits (id, benefit_type) VALUES "
                "(1, 'bvi'), (2, 'hundred_points'), (3, 'other'), (4, 'prize')"
            )
        )
        context = MigrationContext.configure(
            connection,
            opts={"render_as_batch": True},
        )
        migration = _migration_module()
        migration.op = Operations(context)

        assert migration.down_revision == "b91e2a4d7c10"
        migration.upgrade()

        columns = {
            column["name"]: column
            for column in sa.inspect(connection).get_columns("benefits")
        }
        assert columns["has_bvi"]["nullable"] is False
        assert columns["has_hundred_points"]["nullable"] is False
        assert columns["has_bvi"]["default"] is None
        assert columns["has_hundred_points"]["default"] is None

        rows = connection.execute(
            sa.text(
                "SELECT id, has_bvi, has_hundred_points "
                "FROM benefits ORDER BY id"
            )
        ).mappings()
        assert [
            (row["id"], bool(row["has_bvi"]), bool(row["has_hundred_points"]))
            for row in rows
        ] == [
            (1, True, False),
            (2, False, True),
            (3, False, False),
            (4, False, False),
        ]

        migration.downgrade()
        remaining_columns = {
            column["name"] for column in sa.inspect(connection).get_columns("benefits")
        }
        assert remaining_columns == {"id", "benefit_type"}
