"""SQLite persistence scoped to the browser's signed anonymous session."""
import json
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from flask import current_app, g

from .pipeline import validate_csv


def connection():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def save_dataset(owner, name, as_of, result, state="preview", dataset_id=None):
    dataset_id = dataset_id or secrets.token_hex(16)
    db = connection()
    with db:
        db.execute("INSERT INTO datasets VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (dataset_id, owner, name, as_of.isoformat(), datetime.now(timezone.utc).isoformat(), state, json.dumps(result["quality"])))
        db.executemany("INSERT INTO incidents(dataset_id, incident_id, payload) VALUES (?, ?, ?)",
                       [(dataset_id, r["incident_id"], json.dumps(r)) for r in result["records"]])
    return dataset_id


def get_dataset(dataset_id, owner):
    row = connection().execute("SELECT * FROM datasets WHERE id = ? AND (owner = ? OR owner = 'demo')", (dataset_id, owner)).fetchone()
    if not row:
        return None
    records = connection().execute("SELECT payload FROM incidents WHERE dataset_id = ? ORDER BY incident_id", (dataset_id,)).fetchall()
    return {"id": row["id"], "name": row["name"], "as_of": row["as_of"], "created_at": row["created_at"],
            "state": row["state"], "is_demo": row["owner"] == "demo", "quality": json.loads(row["quality"]),
            "records": [json.loads(r["payload"]) for r in records]}


def activate(dataset_id, owner):
    db = connection()
    with db:
        return db.execute("UPDATE datasets SET state = 'active' WHERE id = ? AND owner = ?", (dataset_id, owner)).rowcount == 1


def prune(owner, active_id="demo"):
    db = connection()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    with db:
        db.execute("DELETE FROM datasets WHERE owner != 'demo' AND created_at < ? AND id != ?", (cutoff, active_id))
        # Previewing must not evict the currently active dataset.
        db.execute("DELETE FROM datasets WHERE owner = ? AND id != ? AND id NOT IN (SELECT id FROM datasets WHERE owner = ? ORDER BY created_at DESC LIMIT 20)", (owner, active_id, owner))


def init_app(app):
    @app.teardown_appcontext
    def close_db(error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = connection()
        db.executescript("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
                as_of TEXT NOT NULL, created_at TEXT NOT NULL, state TEXT NOT NULL, quality TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS datasets_owner ON datasets(owner, created_at);
            CREATE TABLE IF NOT EXISTS incidents (
                dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
                incident_id TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(dataset_id, incident_id)
            );
        """)
        if not get_dataset("demo", "demo"):
            sample = Path(app.root_path).parent / "data" / "demo_incidents.csv"
            result = validate_csv(sample.read_bytes(), date(2026, 9, 24))
            save_dataset("demo", "Operations · September 2026", date(2026, 9, 24), result, "active", "demo")
