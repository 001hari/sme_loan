"""PostgreSQL connection lifecycle and schema initialization."""

from contextlib import contextmanager
from pathlib import Path
import os
from typing import Iterator

from dotenv import load_dotenv


class DatabaseConfigurationError(RuntimeError):
    """Raised when required PostgreSQL settings are missing."""


class DatabaseConnection:
    def __init__(self, env_file: Path | None = None) -> None:
        self.project_root = Path(__file__).resolve().parents[3]
        self.env_file = env_file or self.project_root / ".env"

    def _parameters(self) -> dict[str, str | int]:
        load_dotenv(self.env_file)
        required = {
            "PGHOST": "host",
            "PGPORT": "port",
            "PGDATABASE": "dbname",
            "PGUSER": "user",
            "PGPASSWORD": "password",
        }
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise DatabaseConfigurationError(
                "Missing PostgreSQL settings in .env: " + ", ".join(missing)
            )
        try:
            port = int(os.environ["PGPORT"])
        except ValueError as exc:
            raise DatabaseConfigurationError("PGPORT must be an integer.") from exc
        if not 1 <= port <= 65535:
            raise DatabaseConfigurationError("PGPORT must be between 1 and 65535.")
        return {
            "host": os.environ["PGHOST"],
            "port": port,
            "dbname": os.environ["PGDATABASE"],
            "user": os.environ["PGUSER"],
            "password": os.environ["PGPASSWORD"],
            "connect_timeout": 5,
        }

    def connect(self):
        """Open a connection; callers should use ``connection()`` for cleanup."""
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(**self._parameters(), row_factory=dict_row)

    @contextmanager
    def connection(self) -> Iterator[object]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def migrate(self) -> None:
        """Apply migrations explicitly; application startup must not call this."""
        from backend.app.database.migration_runner import apply_migrations

        apply_migrations(self)

    def has_migration(self, version: str) -> bool:
        """Read-only check used by application startup to require a schema version."""
        conn = self.connect()
        try:
            conn.execute("SET TRANSACTION READ ONLY")
            row = conn.execute(
                "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version=%s) AS applied",
                (version,),
            ).fetchone()
            return bool(row["applied"])
        except Exception:
            return False
        finally:
            conn.rollback()
            conn.close()
