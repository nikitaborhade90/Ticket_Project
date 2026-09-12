"""
Datastraw Support CRM — backend API
FastAPI + SQLite. Single-file backend by design: this is a small
ticketing tool, not a platform, so one module keeps it easy to read.
"""
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "tickets.db"))
STATIC_DIR = BASE_DIR / "static"

VALID_STATUSES = ("Open", "In Progress", "Closed")

# Keyword heuristic used for the auto-priority "stand out" feature.
# See README for the reasoning behind this instead of a full ML classifier.
HIGH_PRIORITY_KEYWORDS = (
    "urgent", "down", "outage", "broken", "crash", "asap",
    "not working", "critical", "data loss", "security", "breach",
    "cannot login", "can't login", "payment failed", "refund",
)
MEDIUM_PRIORITY_KEYWORDS = (
    "error", "bug", "issue", "slow", "delay", "problem", "help",
)


def classify_priority(subject: str, description: str) -> str:
    text = f"{subject} {description}".lower()
    if any(k in text for k in HIGH_PRIORITY_KEYWORDS):
        return "High"
    if any(k in text for k in MEDIUM_PRIORITY_KEYWORDS):
        return "Medium"
    return "Low"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                priority TEXT NOT NULL DEFAULT 'Low',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_ticket_id(conn) -> str:
    row = conn.execute("SELECT COUNT(*) AS c FROM tickets").fetchone()
    n = row["c"] + 1
    candidate = f"TKT-{n:03d}"
    # Guard against gaps from deleted rows causing a collision.
    while conn.execute(
        "SELECT 1 FROM tickets WHERE ticket_id = ?", (candidate,)
    ).fetchone():
        n += 1
        candidate = f"TKT-{n:03d}"
    return candidate


# ---------- Schemas ----------

class TicketCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=120)
    customer_email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=4000)


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None  # a new note to append


# ---------- App ----------

app = FastAPI(title="Datastraw Support CRM", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/api/tickets", status_code=201)
def create_ticket(payload: TicketCreate):
    ts = now_iso()
    priority = classify_priority(payload.subject, payload.description)
    with get_db() as conn:
        ticket_id = next_ticket_id(conn)
        conn.execute(
            """
            INSERT INTO tickets
                (ticket_id, customer_name, customer_email, subject, description,
                 status, priority, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?)
            """,
            (
                ticket_id,
                payload.customer_name.strip(),
                payload.customer_email,
                payload.subject.strip(),
                payload.description.strip(),
                priority,
                ts,
                ts,
            ),
        )
    return {"ticket_id": ticket_id, "created_at": ts, "priority": priority}


@app.get("/api/tickets")
def list_tickets(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    if status and status not in VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {VALID_STATUSES}")

    query = (
        "SELECT ticket_id, customer_name, customer_email, subject, status, "
        "priority, created_at FROM tickets WHERE 1=1"
    )
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        like = f"%{search.strip()}%"
        query += (
            " AND (customer_name LIKE ? OR ticket_id LIKE ? "
            "OR customer_email LIKE ? OR subject LIKE ? OR description LIKE ?)"
        )
        params += [like, like, like, like, like]
    query += " ORDER BY id DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/stats")
def stats():
    """Extra endpoint backing the dashboard summary cards (stand-out feature)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM tickets GROUP BY status"
        ).fetchall()
        high_priority_open = conn.execute(
            "SELECT COUNT(*) AS c FROM tickets WHERE priority = 'High' AND status != 'Closed'"
        ).fetchone()["c"]
    counts = {s: 0 for s in VALID_STATUSES}
    for r in rows:
        counts[r["status"]] = r["c"]
    counts["high_priority_open"] = high_priority_open
    counts["total"] = sum(counts[s] for s in VALID_STATUSES)
    return counts


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    with get_db() as conn:
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        notes = conn.execute(
            "SELECT id, note_text, created_at FROM notes WHERE ticket_id = ? ORDER BY id ASC",
            (ticket_id,),
        ).fetchall()
    result = dict(ticket)
    result["notes"] = [dict(n) for n in notes]
    return result


@app.put("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: str, payload: TicketUpdate):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT 1 FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Ticket not found")

        ts = now_iso()

        if payload.status is not None:
            if payload.status not in VALID_STATUSES:
                raise HTTPException(400, f"status must be one of {VALID_STATUSES}")
            conn.execute(
                "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?",
                (payload.status, ts, ticket_id),
            )

        if payload.notes:
            conn.execute(
                "INSERT INTO notes (ticket_id, note_text, created_at) VALUES (?, ?, ?)",
                (ticket_id, payload.notes.strip(), ts),
            )
            conn.execute(
                "UPDATE tickets SET updated_at = ? WHERE ticket_id = ?", (ts, ticket_id)
            )

    return {"success": True, "updated_at": ts}


# ---------- Static frontend ----------
# Serves the plain HTML/JS frontend from backend/static so the whole
# app is a single deployable service (one URL for API + UI).
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/ticket.html")
    def serve_ticket_page():
        return FileResponse(str(STATIC_DIR / "ticket.html"))

    @app.get("/create.html")
    def serve_create_page():
        return FileResponse(str(STATIC_DIR / "create.html"))
