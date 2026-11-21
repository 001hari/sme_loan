"""Risk Radar console entry point."""

import logging
import sys
from pathlib import Path

from backend.app.console.role_app import RoleBasedConsoleApplication
from backend.app.database.connection import DatabaseConfigurationError, DatabaseConnection
from backend.app.database.migrations.v005_business_id_sequence import VERSION as REQUIRED_SCHEMA_VERSION
from backend.app.repositories.workflow_repository import WorkflowRepository
from backend.app.services.workflow_service import WorkflowService


CREDIT_RADAR_BANNER = (
    "╔══════════════════════════════════════════════════════════════╗\n"
    "║                                                              ║\n"
    "║                         CREDIT RADAR                         ║\n"
    "║                                                              ║\n"
    "║                SME LOAN RISK PREDICTION SYSTEM               ║\n"
    "║                                                              ║\n"
    "╚══════════════════════════════════════════════════════════════╝"
)


def main() -> int:
    log_dir = Path(__file__).resolve().parents[3] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        filename=str(log_dir / "risk_radar.log"),
        encoding="utf-8",
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(CREDIT_RADAR_BANNER)
    database = DatabaseConnection()
    try:
        if not database.has_migration(REQUIRED_SCHEMA_VERSION):
            print("The database schema is not current. Run: python -m backend.app.database.migrate")
            return 1
    except DatabaseConfigurationError as exc:
        print(f"Database configuration error: {exc}")
        print("Copy .env.example to .env and enter your PostgreSQL connection settings.")
        return 1
    except Exception:
        logging.error("Could not connect to PostgreSQL or apply schema migrations.")
        print("Could not connect to PostgreSQL. Check that the server is running and .env is correct.")
        return 1

    application = RoleBasedConsoleApplication(WorkflowService(WorkflowRepository(database)))
    try:
        application.run()
    except (EOFError, KeyboardInterrupt):
        print("\nApplication closed safely.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
