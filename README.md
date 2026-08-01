# DataGuardian AI

> Autonomous AI agent that monitors DataHub metadata, detects governance
> issues, explains the risk in plain language, and recommends or performs
> corrective action.

Built for **Build with DataHub: The Agent Hackathon**.

> **Status: foundation only.** The repository structure, tooling, and a running
> frontend/backend skeleton are in place. No governance logic, DataHub
> integration, or AI workflow has been implemented yet — see the
> [Roadmap](#roadmap).

---

## The problem

Data catalogues decay quietly. Ownership goes stale when people change teams,
PII lands in tables nobody tagged, descriptions never get written, and
deprecated datasets keep feeding live dashboards. The metadata that should make
a platform governable becomes the thing nobody trusts.

Catalogues are good at *recording* this state. They are not good at *acting* on
it — someone still has to notice, judge whether it matters, and fix it.

## The approach

DataGuardian AI closes that loop. It periodically reads metadata from DataHub,
evaluates it against governance rules, and uses an LLM to turn each violation
into something a data steward can act on:

1. **Monitor** — scheduled scans pull metadata from DataHub through its MCP
   server.
2. **Detect** — deterministic rules flag missing ownership, untagged PII, absent
   documentation, stale or deprecated assets, and schema drift.
3. **Explain** — Gemini, orchestrated by LangGraph, describes the risk and its
   blast radius using lineage, in language a non-engineer can act on.
4. **Recommend** — each finding carries a concrete remediation.
5. **Act** — approved remediations are written back to DataHub, with every
   action recorded in an audit trail.

Deterministic rules decide *what* is wrong; the LLM explains *why it matters*
and *what to do*. Keeping that boundary sharp is what makes the output
trustworthy — the agent does not invent violations.

---

## Architecture overview

```
┌──────────────────────────────────────────────┐
│  Frontend — React + TypeScript + Vite        │
│  Dashboard · Assets · Issues · Lineage       │
└───────────────────────┬──────────────────────┘
                        │  HTTP  /api/v1/*
┌───────────────────────▼──────────────────────┐
│  Backend — FastAPI (Python 3.12)             │
│                                              │
│  api/       versioned routers                │
│  services/  governance rules, DataHub access │
│  agents/    LangGraph workflow               │
│  scheduler/ APScheduler periodic scans       │
│  models/    SQLAlchemy ORM                   │
└───┬───────────────┬──────────────────┬───────┘
    │               │                  │
┌───▼────────┐ ┌────▼───────────┐ ┌────▼───────┐
│ PostgreSQL │ │ DataHub (MCP)  │ │  Gemini    │
│ findings,  │ │ metadata +     │ │  reasoning │
│ audit log  │ │ remediation    │ │            │
└────────────┘ └────────────────┘ └────────────┘
```

Design notes and decision records: [`architecture/`](architecture/).

### Principles

- **Routers stay thin.** HTTP handlers validate and delegate; the logic lives in
  `app/services/` and never imports FastAPI, so it is testable without a server.
- **One source of configuration.** `app/config/settings.py` reads and validates
  the environment once. Malformed config fails at startup, not mid-request.
- **Versioned API surface.** Feature routers are registered in
  `app/api/v1/router.py`, so `main.py` does not change as the API grows.
- **Typed at both ends.** Pydantic models define the contract; the mirrored
  TypeScript types live in `frontend/src/types/`.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS 4, React Router 8, Axios, React Flow (`@xyflow/react`), Recharts |
| **Backend** | FastAPI, Python 3.12, SQLAlchemy 2, Alembic, Pydantic v2, APScheduler, httpx |
| **Database** | PostgreSQL 16 |
| **AI** | LangGraph, Google Gemini |
| **Data platform** | DataHub, DataHub MCP Server, Agent Context Kit |
| **Tooling** | Ruff, mypy, pytest, oxlint, GitHub Actions |
| **Deployment** | Docker, Docker Compose |

---

## Folder structure

```
DataGuardian-AI/
├── frontend/                  React + TypeScript client
│   ├── src/
│   │   ├── components/        Reusable presentational components
│   │   ├── pages/             One component per route
│   │   ├── layouts/           Persistent app shell
│   │   ├── hooks/             Custom React hooks
│   │   ├── services/          Axios client and API calls
│   │   ├── types/             Shared TypeScript types
│   │   ├── utils/             Framework-agnostic helpers
│   │   ├── assets/            Images, icons, fonts
│   │   ├── App.tsx            Route table
│   │   └── main.tsx           Entry point
│   ├── public/                Served verbatim
│   └── package.json
│
├── backend/                   FastAPI service
│   ├── app/
│   │   ├── api/v1/            Versioned routers
│   │   ├── agents/            LangGraph workflow          (empty)
│   │   ├── services/          Business logic              (empty)
│   │   ├── models/            SQLAlchemy ORM models       (empty)
│   │   ├── schemas/           Pydantic request/response models
│   │   ├── scheduler/         APScheduler jobs
│   │   ├── core/              Database, logging, exceptions
│   │   ├── prompts/           LLM prompt templates        (empty)
│   │   ├── utils/             Shared helpers              (empty)
│   │   ├── config/            Typed settings
│   │   └── main.py            Application entry point
│   ├── tests/                 pytest suite
│   ├── requirements.txt
│   └── .env.example
│
├── datahub/                   Ingestion recipes, MCP config  (placeholder)
├── docker/                    Dockerfiles
├── docs/                      User and contributor guides
├── architecture/              Diagrams and decision records
├── scripts/                   Developer convenience scripts
├── .github/workflows/         CI pipeline
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
```

---

## Local setup

### Prerequisites

- **Python 3.12+**
- **Node.js 20+** (developed against 22)
- **PostgreSQL 16** — optional for now; nothing queries the database yet
- **Docker Desktop** — optional, for the Compose stack

### Quick start

```bash
# Windows
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

# macOS / Linux
bash scripts/setup.sh
```

Then run the two services in separate terminals — or follow the manual steps
below to do the same thing by hand.

### Backend

```bash
cd backend

python -m venv .venv
# Windows:        .\.venv\Scripts\Activate.ps1
# macOS / Linux:  source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env

uvicorn app.main:app --reload
```

| URL | What |
| --- | --- |
| <http://localhost:8000/> | `{"project":"DataGuardian AI","status":"running"}` |
| <http://localhost:8000/api/v1/health> | Liveness payload |
| <http://localhost:8000/docs> | Swagger UI |
| <http://localhost:8000/redoc> | ReDoc |

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open <http://localhost:5173>. The status badge in the header turns green once it
reaches the backend — the dev server proxies `/api` to
`http://localhost:8000`, so both must be running.

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Starts PostgreSQL, the backend, and the frontend. DataHub is **not** included —
run it from its own quickstart, see [`datahub/README.md`](datahub/README.md).

### Checks

```bash
# Backend
cd backend && ruff check . && pytest -q

# Frontend
cd frontend && npm run lint && npm run build
```

Both run automatically on every push and pull request via
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Roadmap

### Phase 1 — Foundation ✅

- [x] Repository structure and tooling
- [x] Vite + React + TypeScript + Tailwind frontend shell with routing
- [x] FastAPI backend with typed settings, logging, and error handling
- [x] Database, scheduler, and CI scaffolding
- [x] Docker Compose skeleton

### Phase 2 — DataHub integration

- [x] GraphQL integration layer (`backend/app/integrations/datahub/`) — typed
      client, queries, models, mapper, and service
- [x] Read endpoints: datasets, owners, domains, lineage, statistics
- [x] Connectivity probe at `/api/v1/health/datahub`
- [ ] **Validate the GraphQL documents against a live DataHub** — built and
      tested against a mock transport; see the `TODO(datahub)` comments in
      `queries.py`
- [ ] Connect to the DataHub MCP server
- [ ] Ingest sample metadata for the demo
- [ ] Model assets, findings, and audit records in PostgreSQL
- [ ] Alembic migrations
- [ ] Asset browsing UI

### Phase 3 — Detection

- [ ] Governance rule engine (missing ownership, untagged PII, absent
      documentation, stale assets, schema drift)
- [ ] Severity scoring
- [ ] Scheduled scans via APScheduler
- [ ] Findings list and detail views

### Phase 4 — AI reasoning

- [ ] LangGraph agent workflow
- [ ] Gemini-backed risk explanation and impact analysis
- [ ] Remediation recommendations
- [ ] Lineage-based blast-radius analysis (React Flow)

### Phase 5 — Autonomous action

- [ ] Write remediations back to DataHub
- [ ] Human-in-the-loop approval flow
- [ ] Audit trail of every agent action
- [ ] Trend dashboards (Recharts)

### Phase 6 — Polish

- [ ] End-to-end tests
- [ ] Deployment guide
- [ ] Demo script and recording

---

## License

[MIT](LICENSE).
