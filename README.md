# Datastraw Support CRM

A small, fully working customer support ticketing system: create tickets, search and filter them, and update status with internal notes — built for the Datastraw assessment.

**Stack:** Python + FastAPI · SQLite · plain HTML/CSS/JS frontend (served by the same app, one deployable service).

## Live demo

- App: _add your deployed URL here_
- Repo: _add your GitHub URL here_
- Demo video: _add your video link here_

## Features

1. **Create tickets** — customer name/email, subject, description. Ticket ID (`TKT-001`, `TKT-002`, …) and timestamp are generated server-side.
2. **List all tickets** — ID, customer, subject, priority, status, created date.
3. **Search** — across name, ticket ID, email, subject, and description, live as you type (debounced).
4. **Filter by status** — Open / In Progress / Closed.
5. **View & update a ticket** — full detail page, change status, and append internal notes (timestamped, append-only).

### Stand-out addition: rule-based priority triage + queue dashboard

Every ticket is auto-tagged **High / Medium / Low** priority at creation time, using a keyword heuristic over the subject and description (e.g. "urgent", "down", "payment failed" → High; "error", "bug", "slow" → Medium; everything else → Low). The home page also shows a small stats strip — open / in-progress / closed counts and a "high priority, unresolved" count — pulled from a `GET /api/stats` endpoint.

**Why this and not something else:** a support team fielding hundreds of tickets a day needs to know *what to look at first*, not just a flat list. Triage is the highest-leverage thing a bare-bones CRM is missing.

**Trade-off:** this is a keyword heuristic, not a trained classifier — it will misfire on phrasing it doesn't recognize (sarcasm, typos, non-English text) and the keyword list is short. A production system would use a small classifier or let agents override the auto-tag manually. I chose the heuristic because it's transparent (you can read exactly why a ticket got tagged), needs no training data or extra infra, and ships in a few lines of code — appropriate for a 2–3 day scope.

## Architecture

```
datastraw-crm/
├── backend/
│   ├── main.py            # FastAPI app: API routes + serves the frontend
│   ├── requirements.txt
│   └── static/             # frontend (plain HTML/CSS/JS, no build step)
│       ├── index.html      # ticket list, search, filter, stats
│       ├── create.html     # new ticket form
│       ├── ticket.html     # ticket detail, status update, notes
│       ├── style.css
│       └── app.js          # shared fetch/formatting helpers
├── .env.example
├── .gitignore
└── README.md
```

**Why one service instead of separate frontend/backend deployments:** the frontend is plain JS with no build step, so FastAPI can serve it directly via `StaticFiles`. That means one URL, one deploy, no CORS headaches for the reviewer — simpler is better for a tool this size.

### Database schema

Two tables, as specified — no over-engineering:

```sql
tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id TEXT UNIQUE,       -- e.g. TKT-001
  customer_name TEXT,
  customer_email TEXT,
  subject TEXT,
  description TEXT,
  status TEXT,                 -- Open | In Progress | Closed
  priority TEXT,               -- High | Medium | Low (auto-assigned)
  created_at TEXT,
  updated_at TEXT
)

notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id TEXT REFERENCES tickets(ticket_id),
  note_text TEXT,
  created_at TEXT
)
```

### API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/tickets` | Create a ticket. Body: `{ customer_name, customer_email, subject, description }`. Returns `{ ticket_id, created_at, priority }`. |
| `GET` | `/api/tickets?status=&search=` | List tickets, optionally filtered by status and/or a search term. |
| `GET` | `/api/tickets/{ticket_id}` | Full ticket detail, including its notes. |
| `PUT` | `/api/tickets/{ticket_id}` | Update status and/or append a note. Body: `{ status?, notes? }`. Returns `{ success, updated_at }`. |
| `GET` | `/api/stats` | Counts by status + high-priority-unresolved count, for the dashboard strip. |

Interactive API docs are available at `/docs` (FastAPI's built-in Swagger UI) once the app is running.

## Running locally

Requires Python 3.10+.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.example .env         # optional — sensible defaults work without it

uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000` — the frontend and API are both served from this one address. A `tickets.db` SQLite file is created automatically on first run.

## Deploying (Railway.app)

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo**, select this repo.
3. Set the **root directory** to `backend`.
4. Set the **start command** to:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Railway auto-detects Python and installs `requirements.txt`. No other environment variables are required — SQLite writes to a local file inside the container.
6. Once deployed, Railway gives you a public URL — that's the app.

*Note on persistence:* SQLite lives on the container's local disk. On Railway's free tier this is fine for a demo/assessment; for real production use you'd either attach a persistent volume or switch to a hosted Postgres (the schema is simple enough that this would be a small change).

## Challenges & what I'd improve with more time

- **Ticket ID generation** uses a simple count-based scheme (`TKT-001`, `TKT-002`, …) with a collision check, rather than `id`-based IDs, to match the spec's format — this is fine at low volume but a UUID or a dedicated counter table would scale better under concurrent writes.
- **Auth** was intentionally skipped for this MVP, per the assignment's guidance — any agent can view/update any ticket. A real deployment would need at minimum an agent login and audit trail on who changed what.
- **Multi-channel / multi-client support** (mentioned in the brief's "what would a real team need") — the schema and UI would need a `client_id`/`channel` field and a way to scope the queue per client. I scoped this out to focus on one well-executed addition (triage) rather than several shallow ones, per the assignment's own guidance.
- **Notes** are append-only with no edit/delete — kept simple since the spec only asked for "add notes/comments."
