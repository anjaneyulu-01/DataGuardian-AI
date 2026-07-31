# Architecture

System design records for DataGuardian AI. Diagrams and decision records live
here; user-facing guides live in [`../docs/`](../docs/).

## Contents

| File | Purpose |
| --- | --- |
| `system-overview.md` | Component diagram and request/data flow — _to be written_ |
| `agent-design.md` | LangGraph state machine, nodes, and tool surface — _to be written_ |
| `data-model.md` | PostgreSQL schema and entity relationships — _to be written_ |
| `decisions/` | Architecture Decision Records (ADRs), one file per decision — _to be created_ |

## Current shape

```
Browser (React + Vite)
        │  HTTP  /api/v1/*
        ▼
FastAPI  ── APScheduler (periodic metadata scans)
        │
        ├── PostgreSQL   (findings, run history, audit trail)
        ├── DataHub GMS  (metadata source and remediation target)  [not wired up]
        └── LangGraph    (agent workflow) → Gemini                 [not wired up]
```

## Decisions made so far

- **Versioned API prefix (`/api/v1`).** Routers are aggregated in
  `backend/app/api/v1/router.py`, so adding a feature never touches `main.py`.
- **Services own the logic, routers stay thin.** Nothing under
  `app/services/` imports FastAPI, which keeps the domain testable without
  spinning up HTTP.
- **Settings are validated once at import.** `app/config/settings.py` is the
  only place that reads the environment; a missing or malformed value fails
  loudly at startup rather than deep inside a request.
- **Lazy database engine.** Importing `app.core.database` does not open a
  connection, so tests and the API root run without PostgreSQL.
