from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command


def test_migration_on_fresh_database(tmp_path: Path) -> None:
    """Verify Alembic migration creates all tables and indexes on an empty database."""
    db_file = tmp_path / "fresh_migration.db"
    assert not db_file.exists()

    ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file}")

    command.upgrade(cfg, "head")

    assert db_file.exists()

    # Verify tables created
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "schema_bootstrap" in tables
    assert "conversations" in tables
    assert "messages" in tables
    assert "support_requests" in tables
    assert "audit_events" in tables


def test_migration_on_existing_g01_database(tmp_path: Path) -> None:
    """Verify Alembic migration upgrades an existing G01 database without data loss."""
    db_file = tmp_path / "g01_existing.db"

    # Seed initial G01 database with schema_bootstrap
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE schema_bootstrap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component VARCHAR(50) NOT NULL UNIQUE,
            version VARCHAR(20) NOT NULL,
            initialized_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("INSERT INTO schema_bootstrap (component, version) VALUES ('core', '0.1.0')")
    conn.commit()
    conn.close()

    # Now run Alembic upgrade
    ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file}")

    command.upgrade(cfg, "head")

    # Verify G01 bootstrap record is intact
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("SELECT component, version FROM schema_bootstrap WHERE component='core'")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0] == ("core", "0.1.0")


def test_migration_idempotency(tmp_path: Path) -> None:
    """Verify running upgrade multiple times succeeds cleanly."""
    db_file = tmp_path / "idempotent.db"
    ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file}")

    command.upgrade(cfg, "head")
    # Run a second time
    command.upgrade(cfg, "head")

    assert db_file.exists()
