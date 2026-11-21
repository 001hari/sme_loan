"""Explicit PostgreSQL migration command; never imported by app startup."""

import argparse

from backend.app.database.connection import DatabaseConnection
from backend.app.database.migration_runner import MIGRATIONS, rollback_migration


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply or explicitly roll back SME project database migrations.")
    parser.add_argument("--rollback", choices=[version for version, _ in MIGRATIONS])
    args = parser.parse_args()
    database = DatabaseConnection()
    try:
        if args.rollback:
            rollback_migration(database, args.rollback)
            print(f"Rolled back {args.rollback}. Existing records and columns were retained.")
        else:
            database.migrate()
            print("All pending database migrations applied successfully.")
        return 0
    except Exception:
        print("Migration command failed and the transaction was rolled back. No partial schema changes were committed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
