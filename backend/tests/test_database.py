from contextlib import contextmanager

import pytest

from backend.app.database.connection import DatabaseConfigurationError, DatabaseConnection
from backend.app.database.migration_runner import MIGRATIONS, apply_migrations
from backend.app.database.migrations.v005_business_id_sequence import UP as BUSINESS_ID_SEQUENCE_UP


class FakeConnection:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.statements = []
        self.applied = set()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True

    def execute(self, statement: str, params=()):
        self.statements.append((statement, params))
        if statement.startswith("SELECT version FROM schema_migrations"):
            return FakeResult([{"version": value} for value in self.applied])
        if statement.startswith("INSERT INTO schema_migrations"):
            self.applied.add(params[0])
        return FakeResult()


class FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def fetchall(self):
        return self.rows


def test_connection_context_commits_and_closes(monkeypatch) -> None:
    db = DatabaseConnection()
    conn = FakeConnection()
    monkeypatch.setattr(db, "connect", lambda: conn)

    with db.connection() as opened:
        assert opened is conn

    assert conn.committed
    assert conn.closed
    assert not conn.rolled_back


def test_business_id_migration_adds_preserving_sequence_default_and_zero_revenue_constraint():
    sql = "\n".join(BUSINESS_ID_SEQUENCE_UP)
    versions = [version for version, _statements in MIGRATIONS]
    assert versions[-1] == "005_business_id_sequence"
    assert "CREATE SEQUENCE IF NOT EXISTS businesses_business_id_seq" in sql
    assert "START WITH 1" in sql
    assert "MAX(business_id)" in sql
    assert "ALTER TABLE businesses ALTER COLUMN business_id SET DEFAULT nextval" in sql
    assert "CHECK (previous_year_revenue >= 0)" in sql


def test_connection_context_rolls_back_on_error(monkeypatch) -> None:
    db = DatabaseConnection()
    conn = FakeConnection()
    monkeypatch.setattr(db, "connect", lambda: conn)

    with pytest.raises(RuntimeError, match="database write"):
        with db.connection():
            raise RuntimeError("database write")

    assert conn.rolled_back
    assert conn.closed
    assert not conn.committed


def test_missing_database_settings_are_reported(monkeypatch, tmp_path) -> None:
    for key in ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        monkeypatch.delenv(key, raising=False)
    db = DatabaseConnection(tmp_path / "missing.env")

    with pytest.raises(DatabaseConfigurationError, match="PGHOST"):
        db._parameters()


def test_migrations_run_once_and_commit(monkeypatch) -> None:
    db = DatabaseConnection()
    conn = FakeConnection()
    monkeypatch.setattr(db, "connect", lambda: conn)

    apply_migrations(db)
    first_count = len(conn.statements)
    apply_migrations(db)

    assert conn.applied == {version for version, _ in MIGRATIONS}
    assert len(conn.statements) == first_count + 2  # ledger DDL and version lookup only
    assert conn.committed
    assert conn.closed


def test_four_core_migration_is_additive_and_preserves_legacy_outcomes() -> None:
    _, statements = MIGRATIONS[1]
    migration = "\n".join(statements).lower()
    assert "drop table" not in migration
    assert "risk_predicted_score" not in migration
    assert "approval_result" in migration
    assert "final_decision" in migration
    assert "rename column loan_application_id to application_id" in migration
    assert "delete from" not in migration


def test_integer_followup_migration_is_reversible_without_dropping_data() -> None:
    version, statements = MIGRATIONS[2]
    migration = "\n".join(statements).lower()
    assert version == "003_integer_missed_payments"
    assert "type integer" in migration
    assert "drop table" not in migration
    assert "delete from" not in migration


def test_company_identity_migration_preserves_existing_account_fields():
    version, statements = MIGRATIONS[3]
    migration = "\n".join(statements).lower()
    assert version == "004_company_applicant_identity"
    assert "add column company_name varchar(200)" in migration
    assert "email drop not null" in migration
    assert "phone_number drop not null" in migration
    assert "create unique index users_company_name_ci_key" in migration
    assert "drop table" not in migration
    assert "delete from" not in migration


def test_console_startup_does_not_apply_migrations_automatically() -> None:
    from pathlib import Path

    source = Path("backend/app/console/main.py").read_text(encoding="utf-8")
    assert ".migrate(" not in source
    assert "has_migration" in source
