# MaskaStorage — Backend Development Setup

## Prerequisites

- Python 3.11+
- `git`

## Local Setup

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`.
Swagger docs at `http://localhost:8000/docs`.

---

## Environment Variables

All config is in `backend/app/core/config.py`. Override any value via a
`.env` file in `backend/` or by setting environment variables prefixed
with `MASKA_`.

| Variable | Default | Description |
|---|---|---|
| `MASKA_DATABASE_URL` | `sqlite:///./maska_storage.db` | SQLAlchemy DB URL |
| `MASKA_ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `MASKA_SEED_ON_STARTUP` | `True` | Insert seed rows when DB is empty |
| `MASKA_LLM_API_KEY` | *(unset)* | API key for Sriganesh's LLM provider |
| `MASKA_LOG_LEVEL` | `INFO` | Python logging level |
| `MASKA_ALLOWED_ORIGINS` | `["http://localhost:5173", ...]` | CORS origins for Vite dev server |

---

## ⚠️ Schema Change Warning — SQLite + `create_all()`

> **This project currently uses SQLAlchemy `create_all()` instead of
> Alembic migrations.** `create_all()` creates tables that do not yet
> exist but **does not add new columns to existing tables**.

If the backend was started at least once before a schema change (new
column added to `backend/app/database/models.py`), the local
`maska_storage.db` file will be missing those columns. This will cause
startup errors or silent query failures.

**Fix: delete the local DB and restart.**

```bash
# From the backend/ directory:
Remove-Item maska_storage.db   # PowerShell
# or
rm maska_storage.db            # bash / zsh

uvicorn app.main:app --reload
```

The DB will be recreated with the full current schema on next startup.
Any seed data inserted by `seed_mock_resources()` will be repopulated
automatically.

> **Note for Pranav (Tech Lead):** Once the project is ready for staging/production,
> replace `create_all()` with `alembic upgrade head` in the Docker entrypoint.
> See the TODO comments in `backend/app/database/session.py` and `crud.py`.

---

## Running Tests

*(No test suite yet — placeholder for Phase 8 / QA phase.)*

---

## Ownership Boundaries

| Directory | Owner |
|---|---|
| `backend/app/api` | Pannaga |
| `backend/app/services` | Pannaga |
| `backend/app/database` | Pannaga |
| `backend/app/schemas` | Pannaga |
| `backend/app/exceptions` | Pannaga |
| `backend/app/core` | Pannaga |
| `backend/app/ai` | Sriganesh |
| `backend/app/retrieval` | Yeshneil |
| `frontend/` | Frontend team |
