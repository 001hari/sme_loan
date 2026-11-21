"""Interactively rotate this project's PostgreSQL password without echoing it."""

from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import os
import re
import secrets
import sys
import tempfile
from pathlib import Path

from psycopg import sql


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.connection import DatabaseConnection  # noqa: E402


def make_scram_verifier(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 4096
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    b64 = lambda value: base64.b64encode(value).decode("ascii")
    return (
        f"SCRAM-SHA-256${iterations}:{b64(salt)}$"
        f"{b64(stored_key)}:{b64(server_key)}"
    )


def update_env_password(env_path: Path, password: str) -> None:
    contents = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    replacement = f"PGPASSWORD={password}"
    pattern = re.compile(r"(?m)^(?:export\s+)?PGPASSWORD=.*$")
    if pattern.search(contents):
        contents = pattern.sub(replacement, contents)
    else:
        if contents and not contents.endswith(("\n", "\r")):
            contents += "\n"
        contents += replacement + "\n"

    fd, temp_name = tempfile.mkstemp(prefix=".env-rotate-", dir=env_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(contents)
        os.replace(temp_name, env_path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def main() -> int:
    env_path = PROJECT_ROOT / ".env"
    settings = DatabaseConnection(env_path)._parameters()
    username = settings["user"]

    password = getpass.getpass("Enter the new PostgreSQL password (input hidden): ")
    confirmation = getpass.getpass("Re-enter the new password (input hidden): ")
    if password != confirmation:
        print("Passwords did not match. No changes were made.")
        return 1
    if len(password) < 24 or not re.fullmatch(r"[A-Za-z0-9_-]+", password):
        print("Use at least 24 characters, with letters, digits, _ or - only. No changes were made.")
        return 1

    verifier = make_scram_verifier(password)
    connection = None
    try:
        connection = DatabaseConnection(env_path).connect()
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(username), sql.Literal(verifier)
                )
            )
        connection.commit()
    except Exception:
        if connection is not None:
            connection.rollback()
        print("PostgreSQL rejected the password rotation. Local configuration was not changed.")
        return 1
    finally:
        if connection is not None:
            connection.close()

    try:
        update_env_password(env_path, password)
    except Exception:
        print("The database password changed, but updating .env failed. Keep this window open and contact support.")
        return 2

    os.environ["PGPASSWORD"] = password
    try:
        check = DatabaseConnection(env_path).connect()
        try:
            check.execute("SET TRANSACTION READ ONLY")
            check.execute("SELECT 1").fetchone()
            check.rollback()
        finally:
            check.close()
    except Exception:
        print("The password changed and .env was updated, but read-only verification failed.")
        return 3

    print("Password rotation succeeded. Local configuration updated; read-only verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
