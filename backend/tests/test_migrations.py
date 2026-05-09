import os

import sqlalchemy
from alembic import command
from alembic.config import Config

EXPECTED_TABLES = {
    "courses",
    "materials",
    "material_chunks",
    "concepts",
    "concept_edges",
    "cards",
    "reviews",
    "worked_examples",
    "quiz_questions",
    "quiz_attempts",
    "coaching_sessions",
    "plan_sessions",
    "mock_exams",
}

ALEMBIC_INI = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")


def _make_cfg(db_url: str) -> Config:
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_migrations_upgrade_downgrade(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    cfg = _make_cfg(db_url)

    command.upgrade(cfg, "head")

    engine = sqlalchemy.create_engine(db_url)
    tables = set(sqlalchemy.inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(tables), f"Missing tables: {EXPECTED_TABLES - tables}"
    engine.dispose()

    command.downgrade(cfg, "base")

    engine2 = sqlalchemy.create_engine(db_url)
    tables_after = [t for t in sqlalchemy.inspect(engine2).get_table_names() if t != "alembic_version"]
    engine2.dispose()
    assert tables_after == [], f"Tables still present after downgrade: {tables_after}"
