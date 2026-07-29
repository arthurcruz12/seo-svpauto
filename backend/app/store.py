from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4


STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
DATABASE_PATH = Path(os.getenv("SEO_DATABASE_PATH", STORAGE_DIR / "seo.sqlite3"))
FILE_STORAGE_DIR = Path(os.getenv("SEO_FILE_STORAGE_PATH", STORAGE_DIR / "files"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS ai_conversations (
                id TEXT PRIMARY KEY, company_id TEXT NOT NULL, owner_email TEXT NOT NULL,
                title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS ai_messages (
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id) ON DELETE CASCADE
            )"""
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tax_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL DEFAULT 'default-company',
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL DEFAULT 'system',
                at TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS mfa_challenges (
                id TEXT PRIMARY KEY, email TEXT NOT NULL, code_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS rate_limit_attempts (
                id TEXT PRIMARY KEY, limit_key TEXT NOT NULL, attempted_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reconciliation_issues (
                id INTEGER PRIMARY KEY,
                company_id TEXT NOT NULL DEFAULT 'default-company',
                owner_email TEXT NOT NULL,
                document TEXT NOT NULL,
                source TEXT NOT NULL,
                value TEXT NOT NULL,
                issue TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_items (
                ref TEXT PRIMARY KEY,
                company_id TEXT NOT NULL DEFAULT 'default-company',
                owner_email TEXT NOT NULL,
                product TEXT NOT NULL,
                stock INTEGER NOT NULL,
                last_sale_days INTEGER NOT NULL,
                margin INTEGER NOT NULL,
                alert TEXT NOT NULL,
                movement_type TEXT NOT NULL DEFAULT 'Existente',
                movement_quantity INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS debt_items (
                id INTEGER PRIMARY KEY,
                company_id TEXT NOT NULL DEFAULT 'default-company',
                owner_email TEXT NOT NULL,
                invoice TEXT NOT NULL DEFAULT '-',
                entity TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                issue_date TEXT NOT NULL DEFAULT '-',
                due_date TEXT NOT NULL DEFAULT '-',
                due_days INTEGER NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_snapshots (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                owner_email TEXT NOT NULL,
                period TEXT NOT NULL,
                label TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                company_id TEXT PRIMARY KEY,
                plan TEXT NOT NULL,
                status TEXT NOT NULL,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                current_period_end TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_events (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                owner_email TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                category TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                content BLOB NOT NULL,
                storage_path TEXT,
                uploaded_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS operational_states (
                company_id TEXT PRIMARY KEY,
                owner_email TEXT NOT NULL,
                source_name TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                document_intelligence_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        migrate_column(connection, "users", "company_id", "TEXT NOT NULL DEFAULT 'default-company'")
        migrate_column(connection, "reconciliation_issues", "company_id", "TEXT NOT NULL DEFAULT 'default-company'")
        migrate_column(connection, "inventory_items", "company_id", "TEXT NOT NULL DEFAULT 'default-company'")
        migrate_column(connection, "inventory_items", "unit", "TEXT NOT NULL DEFAULT 'Não identificado'")
        migrate_column(connection, "inventory_items", "stock_type", "TEXT NOT NULL DEFAULT 'Não identificado'")
        migrate_column(connection, "inventory_items", "warehouse", "TEXT NOT NULL DEFAULT ''")
        migrate_column(connection, "inventory_items", "system_quantity", "INTEGER NOT NULL DEFAULT 0")
        migrate_column(connection, "inventory_items", "physical_quantity", "INTEGER NOT NULL DEFAULT 0")
        migrate_column(connection, "inventory_items", "difference_quantity", "INTEGER NOT NULL DEFAULT 0")
        migrate_column(connection, "inventory_items", "unit_cost", "REAL NOT NULL DEFAULT 0")
        migrate_column(connection, "inventory_items", "stock_value", "REAL NOT NULL DEFAULT 0")
        migrate_column(connection, "inventory_items", "location", "TEXT NOT NULL DEFAULT ''")
        migrate_column(connection, "inventory_items", "validation_state", "TEXT NOT NULL DEFAULT 'Validado'")
        migrate_column(connection, "inventory_items", "confidence", "INTEGER NOT NULL DEFAULT 100")
        migrate_column(connection, "inventory_items", "movement_type", "TEXT NOT NULL DEFAULT 'Existente'")
        migrate_column(connection, "inventory_items", "movement_quantity", "INTEGER NOT NULL DEFAULT 0")
        migrate_column(connection, "debt_items", "company_id", "TEXT NOT NULL DEFAULT 'default-company'")
        migrate_column(connection, "debt_items", "invoice", "TEXT NOT NULL DEFAULT '-'")
        migrate_column(connection, "debt_items", "issue_date", "TEXT NOT NULL DEFAULT '-'")
        migrate_column(connection, "debt_items", "due_date", "TEXT NOT NULL DEFAULT '-'")
        migrate_column(connection, "metric_snapshots", "report_date", "TEXT")
        migrate_column(connection, "audit_events", "company_id", "TEXT NOT NULL DEFAULT 'system'")
        migrate_column(connection, "uploaded_files", "storage_path", "TEXT")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_at ON audit_events (at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_reconciliation_company ON reconciliation_issues (company_id, status)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_inventory_company ON inventory_items (company_id, product)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_debt_company ON debt_items (company_id, state, due_days)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_company ON metric_snapshots (company_id, period, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_company ON uploaded_files (company_id, uploaded_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_company ON audit_events (company_id, at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_key ON rate_limit_attempts (limit_key, attempted_at)")


def save_operational_state(
    company_id: str,
    owner_email: str,
    source_name: str,
    summary: dict,
    document_intelligence: dict,
) -> dict:
    init_db()
    updated_at = utc_now()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO operational_states
            (company_id, owner_email, source_name, summary_json, document_intelligence_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id) DO UPDATE SET
                owner_email = excluded.owner_email,
                source_name = excluded.source_name,
                summary_json = excluded.summary_json,
                document_intelligence_json = excluded.document_intelligence_json,
                updated_at = excluded.updated_at
            """,
            (
                company_id,
                owner_email.strip().lower(),
                source_name,
                json.dumps(summary, ensure_ascii=False),
                json.dumps(document_intelligence, ensure_ascii=False),
                updated_at,
            ),
        )
    return {
        "sourceName": source_name,
        "summary": summary,
        "documentIntelligence": document_intelligence,
        "updatedAt": updated_at,
    }


def get_operational_state(company_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute(
            """
            SELECT source_name, summary_json, document_intelligence_json, updated_at
            FROM operational_states
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "sourceName": row["source_name"],
        "summary": json.loads(row["summary_json"]),
        "documentIntelligence": json.loads(row["document_intelligence_json"]),
        "updatedAt": row["updated_at"],
    }


def company_numeric_scope(company_id: str) -> int:
    digest = hashlib.sha1(company_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 1_000_000


def scoped_int_id(company_id: str, value: int) -> int:
    return company_numeric_scope(company_id) * 100_000 + int(value)


def public_int_id(company_id: str, value: int) -> int:
    scope_base = company_numeric_scope(company_id) * 100_000
    return int(value) - scope_base if int(value) >= scope_base else int(value)


def scoped_ref(company_id: str, ref: str) -> str:
    return f"{company_id}:{ref}"


def public_ref(company_id: str, ref: str) -> str:
    prefix = f"{company_id}:"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def migrate_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = [row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_company(name: str, company_id: str = "default-company", tax_id: str | None = None) -> dict:
    init_db()
    existing = get_company(company_id)
    if existing:
        return existing
    now = utc_now()
    company = {
        "id": company_id,
        "name": name.strip(),
        "tax_id": tax_id,
        "created_at": now,
        "updated_at": now,
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO companies (id, name, tax_id, created_at, updated_at)
            VALUES (:id, :name, :tax_id, :created_at, :updated_at)
            """,
            company,
        )
    return company


def create_company(name: str, tax_id: str | None = None) -> dict:
    init_db()
    company_id = str(uuid4())
    return ensure_company(name=name, company_id=company_id, tax_id=tax_id)


def get_company(company_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute(
            "SELECT id, name, tax_id, created_at, updated_at FROM companies WHERE id = ?",
            (company_id,),
        ).fetchone()
    return dict(row) if row else None


def ensure_user(name: str, email: str, role: str, password_hash: str, company_id: str = "default-company") -> dict:
    init_db()
    normalized_email = email.strip().lower()
    existing = get_user_by_email(normalized_email)
    if existing:
        return existing
    return create_user(name=name, email=normalized_email, role=role, password_hash=password_hash, company_id=company_id)


def create_user(name: str, email: str, role: str, password_hash: str, company_id: str) -> dict:
    init_db()
    now = utc_now()
    user = {
        "id": str(uuid4()),
        "company_id": company_id,
        "name": name.strip(),
        "email": email.strip().lower(),
        "role": role,
        "password_hash": password_hash,
        "created_at": now,
        "updated_at": now,
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO users (id, company_id, name, email, role, password_hash, created_at, updated_at)
            VALUES (:id, :company_id, :name, :email, :role, :password_hash, :created_at, :updated_at)
            """,
            user,
        )
    return user


def get_user_by_email(email: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute(
            "SELECT id, company_id, name, email, role, password_hash, created_at, updated_at FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    return dict(row) if row else None


def add_audit_event(company_id: str, actor: str, action: str, details: str) -> dict:
    init_db()
    payload = {
        "id": str(uuid4()),
        "company_id": company_id,
        "at": utc_now(),
        "actor": actor,
        "action": action,
        "details": details,
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO audit_events (id, company_id, at, actor, action, details)
            VALUES (:id, :company_id, :at, :actor, :action, :details)
            """,
            payload,
        )
    return payload


def list_audit_events(company_id: str | None = None, limit: int = 100) -> list[dict]:
    init_db()
    safe_limit = max(1, min(limit, 500))
    with connect() as connection:
        if company_id:
            rows = connection.execute(
                """SELECT id, at, actor, action, details FROM audit_events
                   WHERE company_id = ? ORDER BY at DESC LIMIT ?""",
                (company_id, safe_limit),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT id, at, actor, action, details FROM audit_events ORDER BY at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def consume_rate_limit(limit_key: str, limit: int, cutoff: str) -> bool:
    """Atomically record an attempt and report whether it is within the limit."""
    init_db()
    with connect() as connection:
        connection.execute(
            "DELETE FROM rate_limit_attempts WHERE limit_key = ? AND attempted_at <= ?",
            (limit_key, cutoff),
        )
        count = connection.execute(
            "SELECT COUNT(*) FROM rate_limit_attempts WHERE limit_key = ?",
            (limit_key,),
        ).fetchone()[0]
        if count >= limit:
            return False
        connection.execute(
            "INSERT INTO rate_limit_attempts (id, limit_key, attempted_at) VALUES (?, ?, ?)",
            (str(uuid4()), limit_key, utc_now()),
        )
    return True


def save_mfa_challenge(challenge_id: str, email: str, code_hash: str, expires_at: str) -> None:
    init_db()
    with connect() as connection:
        connection.execute("DELETE FROM mfa_challenges WHERE expires_at <= ?", (utc_now(),))
        connection.execute(
            """INSERT INTO mfa_challenges (id, email, code_hash, expires_at, attempts, created_at)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (challenge_id, email.strip().lower(), code_hash, expires_at, utc_now()),
        )


def get_mfa_challenge(challenge_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute(
            "SELECT id, email, code_hash, expires_at, attempts FROM mfa_challenges WHERE id = ?",
            (challenge_id,),
        ).fetchone()
    return dict(row) if row else None


def increment_mfa_attempt(challenge_id: str) -> int:
    init_db()
    with connect() as connection:
        connection.execute(
            "UPDATE mfa_challenges SET attempts = attempts + 1 WHERE id = ?",
            (challenge_id,),
        )
        row = connection.execute(
            "SELECT attempts FROM mfa_challenges WHERE id = ?",
            (challenge_id,),
        ).fetchone()
    return int(row["attempts"]) if row else 0


def delete_mfa_challenge(challenge_id: str) -> None:
    init_db()
    with connect() as connection:
        connection.execute("DELETE FROM mfa_challenges WHERE id = ?", (challenge_id,))


def replace_operational_dataset(company_id: str, owner_email: str, inventory: list[dict], debts: list[dict], issues: list[dict]) -> None:
    init_db()
    normalized_owner = owner_email.strip().lower()
    now = utc_now()
    with connect() as connection:
        connection.execute("DELETE FROM reconciliation_issues WHERE company_id = ?", (company_id,))
        connection.execute("DELETE FROM inventory_items WHERE company_id = ?", (company_id,))
        connection.execute("DELETE FROM debt_items WHERE company_id = ?", (company_id,))

        connection.executemany(
            """
            INSERT INTO reconciliation_issues
            (id, company_id, owner_email, document, source, value, issue, status, created_at, updated_at)
            VALUES (:id, :company_id, :owner_email, :document, :source, :value, :issue, :status, :created_at, :updated_at)
            """,
            [
                {
                    **item,
                    "id": scoped_int_id(company_id, item["id"]),
                    "company_id": company_id,
                    "owner_email": normalized_owner,
                    "created_at": now,
                    "updated_at": now,
                }
                for item in issues
            ],
        )
        connection.executemany(
            """
            INSERT INTO inventory_items
            (ref, company_id, owner_email, product, stock, last_sale_days, margin, alert,
             unit, stock_type, movement_type, movement_quantity, warehouse, system_quantity, physical_quantity, difference_quantity,
             unit_cost, stock_value, location, validation_state, confidence, created_at, updated_at)
            VALUES (:ref, :company_id, :owner_email, :product, :stock, :lastSaleDays, :margin, :alert,
             :unit, :stockType, :movementType, :movementQuantity, :warehouse, :systemQuantity, :physicalQuantity, :differenceQuantity,
             :unitCost, :stockValue, :location, :validationState, :confidence, :created_at, :updated_at)
            """,
            [
                {
                    **item,
                    "ref": scoped_ref(company_id, str(item["ref"])),
                    "company_id": company_id,
                    "owner_email": normalized_owner,
                    "created_at": now,
                    "updated_at": now,
                }
                for item in inventory
            ],
        )
        connection.executemany(
            """
            INSERT INTO debt_items
            (id, company_id, owner_email, invoice, entity, type, amount, issue_date, due_date, due_days, state, created_at, updated_at)
            VALUES (:id, :company_id, :owner_email, :invoice, :entity, :type, :amount, :issueDate, :dueDate, :dueDays, :state, :created_at, :updated_at)
            """,
            [
                {
                    **item,
                    "id": scoped_int_id(company_id, item["id"]),
                    "company_id": company_id,
                    "owner_email": normalized_owner,
                    "created_at": now,
                    "updated_at": now,
                }
                for item in debts
            ],
        )


def append_reconciliation_issues(company_id: str, owner_email: str, issues: list[dict]) -> None:
    init_db()
    normalized_owner = owner_email.strip().lower()
    now = utc_now()
    with connect() as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO reconciliation_issues
            (id, company_id, owner_email, document, source, value, issue, status, created_at, updated_at)
            VALUES (:id, :company_id, :owner_email, :document, :source, :value, :issue, :status, :created_at, :updated_at)
            """,
            [
                {
                    **item,
                    "id": scoped_int_id(company_id, item["id"]),
                    "company_id": company_id,
                    "owner_email": normalized_owner,
                    "created_at": now,
                    "updated_at": now,
                }
                for item in issues
            ],
        )


def list_reconciliation_issues(company_id: str) -> list[dict]:
    init_db()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, document, source, value, issue, status
            FROM reconciliation_issues
            WHERE company_id = ?
            ORDER BY id
            """,
            (company_id,),
        ).fetchall()
    return [{**dict(row), "id": public_int_id(company_id, row["id"])} for row in rows]


def resolve_reconciliation_issue(company_id: str, issue_id: int) -> dict | None:
    init_db()
    now = utc_now()
    with connect() as connection:
        connection.execute(
            """
            UPDATE reconciliation_issues
            SET status = 'Resolvido', updated_at = ?
            WHERE company_id = ? AND id = ?
            """,
            (now, company_id, scoped_int_id(company_id, issue_id)),
        )
        row = connection.execute(
            """
            SELECT id, document, source, value, issue, status
            FROM reconciliation_issues
            WHERE company_id = ? AND id = ?
            """,
            (company_id, scoped_int_id(company_id, issue_id)),
        ).fetchone()
    return {**dict(row), "id": public_int_id(company_id, row["id"])} if row else None


def resolve_all_reconciliation_issues(company_id: str) -> list[dict]:
    init_db()
    now = utc_now()
    with connect() as connection:
        connection.execute(
            """
            UPDATE reconciliation_issues
            SET status = 'Resolvido', updated_at = ?
            WHERE company_id = ?
            """,
            (now, company_id),
        )
    return list_reconciliation_issues(company_id)


def list_inventory_items(company_id: str) -> list[dict]:
    init_db()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT ref, product, stock, last_sale_days AS lastSaleDays, margin, alert,
                   unit, stock_type AS stockType, movement_type AS movementType, movement_quantity AS movementQuantity, warehouse, system_quantity AS systemQuantity,
                   physical_quantity AS physicalQuantity, difference_quantity AS differenceQuantity,
                   unit_cost AS unitCost, stock_value AS stockValue, location,
                   validation_state AS validationState, confidence
            FROM inventory_items
            WHERE company_id = ?
            ORDER BY product
            """,
            (company_id,),
        ).fetchall()
    return [{**dict(row), "ref": public_ref(company_id, row["ref"])} for row in rows]


def register_inventory_sale(company_id: str, ref: str) -> dict | None:
    init_db()
    now = utc_now()
    stored_ref = scoped_ref(company_id, ref)
    with connect() as connection:
        row = connection.execute(
            """
            SELECT ref, product, stock, last_sale_days AS lastSaleDays, margin, alert,
                   unit, stock_type AS stockType, movement_type AS movementType, movement_quantity AS movementQuantity, warehouse, system_quantity AS systemQuantity,
                   physical_quantity AS physicalQuantity, difference_quantity AS differenceQuantity,
                   unit_cost AS unitCost, stock_value AS stockValue, location,
                   validation_state AS validationState, confidence
            FROM inventory_items
            WHERE company_id = ? AND ref IN (?, ?)
            """,
            (company_id, stored_ref, ref),
        ).fetchone()
        if not row:
            return None
        current = dict(row)
        matched_ref = current["ref"]
        next_stock = max(0, int(current["stock"]) - 1)
        next_physical = max(0, int(current["physicalQuantity"]) - 1)
        next_difference = next_physical - int(current["systemQuantity"])
        next_value = round(next_physical * float(current["unitCost"]), 2)
        next_alert = "Stock crítico" if next_stock <= 1 else current["alert"]
        connection.execute(
            """
            UPDATE inventory_items
            SET stock = ?, physical_quantity = ?, difference_quantity = ?, stock_value = ?,
                movement_type = 'Venda', movement_quantity = -1, last_sale_days = 0, alert = ?, updated_at = ?
            WHERE company_id = ? AND ref = ?
            """,
            (next_stock, next_physical, next_difference, next_value, next_alert, now, company_id, matched_ref),
        )
        updated = connection.execute(
            """
            SELECT ref, product, stock, last_sale_days AS lastSaleDays, margin, alert,
                   unit, stock_type AS stockType, movement_type AS movementType, movement_quantity AS movementQuantity, warehouse, system_quantity AS systemQuantity,
                   physical_quantity AS physicalQuantity, difference_quantity AS differenceQuantity,
                   unit_cost AS unitCost, stock_value AS stockValue, location,
                   validation_state AS validationState, confidence
            FROM inventory_items
            WHERE company_id = ? AND ref = ?
            """,
            (company_id, matched_ref),
        ).fetchone()
    return {**dict(updated), "ref": public_ref(company_id, updated["ref"])} if updated else None


def list_debt_items(company_id: str) -> list[dict]:
    init_db()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, invoice, entity, type, amount, issue_date AS issueDate, due_date AS dueDate, due_days AS dueDays, state
            FROM debt_items
            WHERE company_id = ?
            ORDER BY state, due_days DESC
            """,
            (company_id,),
        ).fetchall()
    return [{**dict(row), "id": public_int_id(company_id, row["id"])} for row in rows]


def mark_debt_paid(company_id: str, debt_id: int) -> dict | None:
    init_db()
    now = utc_now()
    with connect() as connection:
        connection.execute(
            """
            UPDATE debt_items
            SET state = 'Pago', updated_at = ?
            WHERE company_id = ? AND id = ?
            """,
            (now, company_id, scoped_int_id(company_id, debt_id)),
        )
        row = connection.execute(
            """
            SELECT id, invoice, entity, type, amount, issue_date AS issueDate, due_date AS dueDate, due_days AS dueDays, state
            FROM debt_items
            WHERE company_id = ? AND id = ?
            """,
            (company_id, scoped_int_id(company_id, debt_id)),
        ).fetchone()
    return {**dict(row), "id": public_int_id(company_id, row["id"])} if row else None


def save_metric_snapshot(company_id: str, owner_email: str, period: str, label: str, metrics: dict, report_date: str | None = None) -> dict:
    init_db()
    payload = {
        "id": str(uuid4()),
        "company_id": company_id,
        "owner_email": owner_email.strip().lower(),
        "period": period,
        "label": label.strip() or period,
        "metrics_json": json.dumps(metrics, ensure_ascii=False, sort_keys=True),
        "created_at": utc_now(),
        "report_date": report_date or datetime.now(timezone.utc).date().isoformat(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO metric_snapshots (id, company_id, owner_email, period, label, metrics_json, created_at, report_date)
            VALUES (:id, :company_id, :owner_email, :period, :label, :metrics_json, :created_at, :report_date)
            """,
            payload,
        )
    return format_snapshot(payload)


def list_metric_snapshots(company_id: str, period: str | None = None, limit: int = 24, report_date: str | None = None) -> list[dict]:
    init_db()
    safe_limit = max(1, min(limit, 120))
    params: list[object] = [company_id]
    period_filter = ""
    if period:
        period_filter = "AND period = ?"
        params.append(period)
    date_filter = ""
    if report_date:
        date_filter = "AND COALESCE(report_date, substr(created_at, 1, 10)) = ?"
        params.append(report_date)
    params.append(safe_limit)
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, company_id, owner_email, period, label, metrics_json, created_at,
                   COALESCE(report_date, substr(created_at, 1, 10)) AS report_date
            FROM metric_snapshots
            WHERE company_id = ? {period_filter} {date_filter}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [format_snapshot(dict(row)) for row in rows]


def format_snapshot(row: dict) -> dict:
    return {
        "id": row["id"],
        "companyId": row["company_id"],
        "period": row["period"],
        "label": row["label"],
        "metrics": json.loads(row["metrics_json"]),
        "createdAt": row["created_at"],
        "reportDate": row.get("report_date") or str(row["created_at"])[:10],
    }


def upsert_subscription(
    company_id: str,
    plan: str,
    status: str,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    current_period_end: str | None = None,
) -> dict:
    init_db()
    payload = {
        "company_id": company_id,
        "plan": plan,
        "status": status,
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": stripe_subscription_id,
        "current_period_end": current_period_end,
        "updated_at": utc_now(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO subscriptions
            (company_id, plan, status, stripe_customer_id, stripe_subscription_id, current_period_end, updated_at)
            VALUES (:company_id, :plan, :status, :stripe_customer_id, :stripe_subscription_id, :current_period_end, :updated_at)
            ON CONFLICT(company_id) DO UPDATE SET
                plan = excluded.plan,
                status = excluded.status,
                stripe_customer_id = COALESCE(excluded.stripe_customer_id, subscriptions.stripe_customer_id),
                stripe_subscription_id = COALESCE(excluded.stripe_subscription_id, subscriptions.stripe_subscription_id),
                current_period_end = COALESCE(excluded.current_period_end, subscriptions.current_period_end),
                updated_at = excluded.updated_at
            """,
            payload,
        )
    return get_subscription(company_id) or payload


def get_subscription(company_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute(
            """
            SELECT company_id AS companyId, plan, status, stripe_customer_id AS stripeCustomerId,
                   stripe_subscription_id AS stripeSubscriptionId, current_period_end AS currentPeriodEnd,
                   updated_at AS updatedAt
            FROM subscriptions
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()
    return dict(row) if row else None


def add_payment_event(company_id: str, provider: str, event_type: str, payload: dict) -> dict:
    init_db()
    event = {
        "id": str(uuid4()),
        "company_id": company_id,
        "provider": provider,
        "event_type": event_type,
        "payload_json": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "created_at": utc_now(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO payment_events (id, company_id, provider, event_type, payload_json, created_at)
            VALUES (:id, :company_id, :provider, :event_type, :payload_json, :created_at)
            """,
            event,
        )
    return event


def save_uploaded_file(company_id: str, owner_email: str, filename: str, content_type: str, category: str, content: bytes) -> dict:
    init_db()
    file_id = str(uuid4())
    target_dir = FILE_STORAGE_DIR / company_id
    target_dir.mkdir(parents=True, exist_ok=True)
    storage_path = target_dir / f"{file_id}.bin"
    temporary_path = storage_path.with_suffix(".tmp")
    temporary_path.write_bytes(content)
    temporary_path.replace(storage_path)
    payload = {
        "id": file_id,
        "company_id": company_id,
        "owner_email": owner_email.strip().lower(),
        "filename": filename[:240],
        "content_type": content_type[:120] or "application/octet-stream",
        "category": category[:40],
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "content": b"",
        "storage_path": str(storage_path),
        "uploaded_at": utc_now(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO uploaded_files
            (id, company_id, owner_email, filename, content_type, category, size_bytes, sha256, content, storage_path, uploaded_at)
            VALUES (:id, :company_id, :owner_email, :filename, :content_type, :category, :size_bytes, :sha256, :content, :storage_path, :uploaded_at)
            """,
            payload,
        )
    from .azure_storage import upload_document
    upload_document(company_id, payload["id"], filename, content, content_type)
    return format_uploaded_file(payload)


def list_uploaded_files(company_id: str, limit: int = 100) -> list[dict]:
    init_db()
    safe_limit = max(1, min(limit, 500))
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, filename, content_type, category, size_bytes, sha256, uploaded_at
            FROM uploaded_files WHERE company_id = ? ORDER BY uploaded_at DESC LIMIT ?
            """,
            (company_id, safe_limit),
        ).fetchall()
    return [format_uploaded_file(dict(row)) for row in rows]


def get_uploaded_file(company_id: str, file_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, filename, content_type, category, size_bytes, sha256, content, storage_path, uploaded_at
            FROM uploaded_files WHERE company_id = ? AND id = ?
            """,
            (company_id, file_id),
        ).fetchone()
    if not row:
        return None
    payload = dict(row)
    storage_path = payload.get("storage_path")
    if storage_path:
        candidate = Path(storage_path)
        if candidate.is_file() and candidate.resolve().is_relative_to(FILE_STORAGE_DIR.resolve()):
            payload["content"] = candidate.read_bytes()
    return payload


def format_uploaded_file(row: dict) -> dict:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "contentType": row["content_type"],
        "category": row["category"],
        "sizeBytes": row["size_bytes"],
        "sha256": row["sha256"],
        "uploadedAt": row["uploaded_at"],
    }


def save_ai_exchange(company_id: str, owner_email: str, conversation_id: str | None, question: str, answer: str) -> str:
    init_db()
    now = utc_now()
    conversation_id = conversation_id or str(uuid4())
    with connect() as connection:
        existing = connection.execute("SELECT id FROM ai_conversations WHERE id = ? AND company_id = ?", (conversation_id, company_id)).fetchone()
        if not existing:
            conversation_id = str(uuid4()) if conversation_id else conversation_id
            connection.execute("INSERT INTO ai_conversations (id, company_id, owner_email, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (conversation_id, company_id, owner_email, question[:80], now, now))
        connection.execute("UPDATE ai_conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
        connection.executemany("INSERT INTO ai_messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)", [(str(uuid4()), conversation_id, "user", question, now), (str(uuid4()), conversation_id, "assistant", answer, now)])
    return conversation_id


def get_ai_messages(company_id: str, conversation_id: str | None) -> list[dict]:
    if not conversation_id:
        return []
    init_db()
    with connect() as connection:
        rows = connection.execute("SELECT m.role, m.content, m.created_at FROM ai_messages m JOIN ai_conversations c ON c.id = m.conversation_id WHERE c.company_id = ? AND c.id = ? ORDER BY m.created_at", (company_id, conversation_id)).fetchall()
    return [dict(row) for row in rows]
