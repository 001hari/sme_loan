"""Transactional, explicitly invoked versioned PostgreSQL migrations."""

from backend.app.database.migrations.v001_role_workflow import VERSION as V001, UP as UP001
from backend.app.database.migrations.v002_four_core_schema import VERSION as V002, UP as UP002, DOWN as DOWN002
from backend.app.database.migrations.v003_integer_missed_payments import VERSION as V003, UP as UP003, DOWN as DOWN003
from backend.app.database.migrations.v004_company_applicant_identity import VERSION as V004, UP as UP004, DOWN as DOWN004
from backend.app.database.migrations.v005_business_id_sequence import VERSION as V005, UP as UP005


MIGRATIONS = ((V001, UP001), (V002, UP002), (V003, UP003), (V004, UP004), (V005, UP005))
ROLLBACKS = {V002: DOWN002, V003: DOWN003, V004: DOWN004}


def apply_migrations(database) -> None:
    """Apply unapplied migrations atomically. Called only by the migration CLI."""
    with database.connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(100) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        applied = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for version, statements in MIGRATIONS:
            if version in applied:
                continue
            for statement in statements:
                conn.execute(statement)
            conn.execute("INSERT INTO schema_migrations(version) VALUES (%s)", (version,))
            applied.add(version)


def rollback_migration(database, version: str) -> None:
    """Explicitly reverse a supported migration without dropping data or columns."""
    if version not in ROLLBACKS:
        raise ValueError("No rollback plan is registered for that migration.")
    versions = [item[0] for item in MIGRATIONS]
    if version != versions[-1]:
        raise ValueError("Only the latest applied migration can be rolled back.")
    with database.connection() as conn:
        applied = [row["version"] for row in conn.execute(
            "SELECT version FROM schema_migrations ORDER BY applied_at,version"
        ).fetchall()]
        if not applied or applied[-1] != version:
            raise ValueError("The requested migration is not the latest applied version.")
        for statement in ROLLBACKS[version]:
            conn.execute(statement)
        conn.execute("DELETE FROM schema_migrations WHERE version=%s", (version,))
