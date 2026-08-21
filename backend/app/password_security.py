from __future__ import annotations

import re

from .store import connect, init_db, utc_now


PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


def ensure_auth_version_column() -> None:
    """Add the credential version used to invalidate old JWT sessions."""
    init_db()
    with connect() as connection:
        columns = [row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()]
        if "auth_version" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 1")


def get_auth_version(email: str) -> int:
    ensure_auth_version_column()
    with connect() as connection:
        row = connection.execute(
            "SELECT auth_version FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    return int(row["auth_version"]) if row else 1


def validate_admin_password(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Use pelo menos {PASSWORD_MIN_LENGTH} caracteres.")
    if len(password) > PASSWORD_MAX_LENGTH:
        errors.append(f"Use no máximo {PASSWORD_MAX_LENGTH} caracteres.")
    if not re.search(r"[a-z]", password):
        errors.append("Inclua pelo menos uma letra minúscula.")
    if not re.search(r"[A-Z]", password):
        errors.append("Inclua pelo menos uma letra maiúscula.")
    if not re.search(r"\d", password):
        errors.append("Inclua pelo menos um número.")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Inclua pelo menos um símbolo.")
    return errors


def update_password_hash(email: str, password_hash: str) -> int:
    """Replace only the password hash and invalidate every previously issued JWT."""
    ensure_auth_version_column()
    normalized_email = email.strip().lower()
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE users
            SET password_hash = ?, auth_version = auth_version + 1, updated_at = ?
            WHERE email = ?
            """,
            (password_hash, utc_now(), normalized_email),
        )
        if cursor.rowcount != 1:
            raise ValueError("Conta de administrador não encontrada.")
        row = connection.execute(
            "SELECT auth_version FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
    return int(row["auth_version"])
