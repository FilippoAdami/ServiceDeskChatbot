from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.config import Settings, reset_settings_for_test
from backend.app.db.base import SchemaBootstrap
from backend.app.db.session import check_db_connection, init_db, reset_db_session


def test_sqlite_file_creation_and_persistence(tmp_path: Path) -> None:
    """Verify that SQLite file is created on disk, data persists across restart/reconnection."""
    db_file = tmp_path / "custom_data" / "persistent_test.db"
    assert not db_file.exists()

    # Step 1: Configure settings with the new database file
    settings = Settings(
        DATABASE_URL=f"sqlite:///{db_file}",
        ENVIRONMENT="test",
    )
    reset_settings_for_test(settings)
    reset_db_session()

    # Step 2: Initialize DB and verify file existence
    init_db()
    assert db_file.exists(), "SQLite database file was not created on disk"

    # Step 3: Check initial bootstrap record created by init_db
    engine_1 = create_engine(f"sqlite:///{db_file}")
    with sessionmaker(bind=engine_1)() as session:
        bootstrap = session.execute(
            select(SchemaBootstrap).where(SchemaBootstrap.component == "core")
        ).scalar_one_or_none()
        assert bootstrap is not None
        assert bootstrap.version == settings.APP_VERSION
        init_time = bootstrap.initialized_at

        # Add an additional custom record to verify data integrity
        custom_item = SchemaBootstrap(
            component="custom_check",
            version="1.2.3",
        )
        session.add(custom_item)
        session.commit()

    # Step 4: Simulate application shutdown / restart by disposing engines
    engine_1.dispose()
    reset_db_session()

    # Step 5: Reconnect to the existing database file and verify persistence
    engine_2 = create_engine(f"sqlite:///{db_file}")
    with sessionmaker(bind=engine_2)() as session:
        bootstrap_reloaded = session.execute(
            select(SchemaBootstrap).where(SchemaBootstrap.component == "core")
        ).scalar_one_or_none()
        assert bootstrap_reloaded is not None
        assert bootstrap_reloaded.initialized_at == init_time

        custom_reloaded = session.execute(
            select(SchemaBootstrap).where(SchemaBootstrap.component == "custom_check")
        ).scalar_one_or_none()
        assert custom_reloaded is not None
        assert custom_reloaded.version == "1.2.3"

    engine_2.dispose()
    reset_settings_for_test(None)
    reset_db_session()


def test_check_db_connection_success(tmp_path: Path) -> None:
    """Verify check_db_connection returns True for a healthy database."""
    db_file = tmp_path / "conn_test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    assert check_db_connection(engine) is True
    engine.dispose()


def test_check_db_connection_invalid_engine() -> None:
    """Verify check_db_connection returns False when connection cannot be established."""
    # Using an invalid file path or broken URI
    bad_engine = create_engine("sqlite:////nonexistent_dir_12345/sub/db.sqlite")
    assert check_db_connection(bad_engine) is False
