import sqlite3
from contextlib import closing
from typing import Any

from .config import DB_PATH, REAL_MODE_DEFAULT_MODEL, ensure_directories


SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    mode TEXT NOT NULL,
    model TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    dataset_path TEXT NOT NULL,
    simulate_failure INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    current_agent TEXT,
    error_message TEXT,
    final_report TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    title TEXT NOT NULL,
    detail TEXT,
    input_summary TEXT,
    output_summary TEXT,
    attempt INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER,
    FOREIGN KEY(run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id)
);
'''


def get_connection() -> sqlite3.Connection:
    ensure_directories()
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.row_factory = sqlite3.Row
    return connection



def ensure_column(table: str, column: str, column_def: str) -> None:
    with get_connection() as connection:
        columns = [row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]
        if column in columns:
            return
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")

def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA_SQL)
    ensure_column('runs', 'model', f"TEXT NOT NULL DEFAULT '{REAL_MODE_DEFAULT_MODEL}'")


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with closing(get_connection()) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with closing(get_connection()) as connection:
        row = connection.execute(query, params).fetchone()
    return dict(row) if row else None


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    with closing(get_connection()) as connection:
        cursor = connection.execute(query, params)
        connection.commit()
        return cursor.lastrowid


def execute_many(query: str, params_list: list[tuple[Any, ...]]) -> None:
    with closing(get_connection()) as connection:
        connection.executemany(query, params_list)
        connection.commit()


