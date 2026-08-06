# Deployment — Render

Deploys two services from this repository:

| Service | Type | What it runs |
| --- | --- | --- |
| `dataguardian-api` | Web Service | FastAPI + LangGraph agent |
| `dataguardian-web` | Static Site | React workspace |

Roughly 15 minutes end to end. **No database is required** — see
[Why no Postgres](#why-no-postgres).

---

## Read this first: three things that will bite you

**1. Vite inlines `VITE_API_URL` at BUILD time.** Changing it in the Render
dashboard does nothing until you rebuild. Use *Manual Deploy → Clear build
cache & deploy*.

**2. CORS is the classic failure.** The build goes green, the health check
passes, and every browser request dies at pre-flight. The backend now logs a
loud error at startup when this is misconfigured — check the logs.

**3. There is a chicken-and-egg problem.** The backend needs the frontend's URL
for CORS; the frontend needs the backend's URL for the API. Neither exists
before its first deploy. The order below resolves it.

---

## Option A — Blueprint (recommended)

[`render.yaml`](../render.yaml) declares both services.

### 1. Push to GitHub

```bash
git add -A && git commit -m "Add Render deployment configuration"
git push origin main
```

### 2. Create the Blueprint

Render Dashboard → **New** → **Blueprint** → select this repository.

Render reads `render.yaml` and prompts for the `sync: false` secrets:

| Variable | Value | Required? |
| --- | --- | --- |
| `GROQ_API_KEY` | From <https://console.groq.com/keys> | For AI features |
| `GEMINI_API_KEY` | From <https://aistudio.google.com/apikey> | Optional — enables fail-over |
| `XAI_API_KEY` | From <https://console.x.ai> | Optional |
| `CORS_ORIGINS` | Leave blank for now — step 4 | **Yes** |
| `DATAHUB_GMS_URL` | Your public DataHub, or blank | See [DataHub](#datahub-is-not-publicly-reachable) |
| `DATAHUB_TOKEN` | DataHub PAT | Only if DataHub is secured |

Click **Apply**. First build takes 5–10 minutes.

`VITE_API_URL` is wired automatically via `fromService` — you do not set it.

### 3. Note the URLs

```
https://dataguardian-api.onrender.com
https://dataguardian-web.onrender.com
```

### 4. Close the CORS loop ← the step everyone forgets

`dataguardian-api` → **Environment** → set:

```
CORS_ORIGINS = https://dataguardian-web.onrender.com
```

No trailing slash. Must match the frontend origin exactly. Save — Render
redeploys automatically.

### 5. Verify

```bash
python scripts/smoke_test.py \
  --api https://dataguardian-api.onrender.com \
  --web https://dataguardian-web.onrender.com
```

---

## Option B — Manual

<details>
<summary>If you prefer clicking through the dashboard</summary>

### Backend — Web Service

| Field | Value |
| --- | --- |
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install --no-cache-dir -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health Check Path | `/api/v1/health` |

Environment: `PYTHON_VERSION=3.12.10`, `APP_ENV=production`,
`LLM_PROVIDER=auto`, `SCHEDULER_ENABLED=false`, `GROQ_API_KEY=…`,
`CORS_ORIGINS=…` (after the frontend exists).

### Frontend — Static Site

| Field | Value |
| --- | --- |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |

Environment: `NODE_VERSION=22`,
`VITE_API_URL=https://dataguardian-api.onrender.com`

**Redirect/Rewrite** (required — without it a refresh on `/governance` 404s):

| Source | Destination | Action |
| --- | --- | --- |
| `/*` | `/index.html` | Rewrite |

</details>

---

## DataHub is not publicly reachable

Render cannot see a DataHub running on your laptop. Three options:

### 1. Deploy without DataHub (fastest, fine for a demo)

Leave `DATAHUB_GMS_URL` blank. The API boots, reports DataHub unreachable, and
the frontend falls back to **Demo Mode** with a visible banner and a
deterministic 25-asset catalogue.

This is a legitimate demo path — the agent, risk engine, and UI all work. Only
live metadata is missing, and the UI says so rather than pretending.

### 2. Managed DataHub

[Acryl Cloud](https://www.acryldata.io/) gives a public GMS URL and a token.
Set both and the deployment is fully live.

### 3. Tunnel a local instance (demo only)

```bash
ngrok http 8080
# then: DATAHUB_GMS_URL=https://<subdomain>.ngrok-free.app
```

Fine for a recorded demo; the tunnel dies with your laptop.

---

## Why no Postgres

`DATABASE_URL` appears in configuration but **nothing uses it today**. There is
no ORM model and no endpoint opens a session — the engine is built lazily and
never touched.

Do not provision a Render Postgres for this deploy. It becomes necessary when
persisted scan history lands (see the roadmap), which is also what turns the
three demo-tagged trend panels into live ones.

---

## Verification checklist

Run the smoke test first; it covers most of this automatically.

**Backend**

- [ ] `GET /api/v1/health` → 200, `environment: production`
- [ ] `/docs` renders Swagger
- [ ] `GET /api/v1/health/datahub` → `reachable: true` *(or a clear reason)*
- [ ] `GET /api/v1/health/llm` → `configured: true, reachable: true`
- [ ] `POST /api/v1/agent/analyze` returns findings and a trace
- [ ] Logs show `environment=production, debug=False`
- [ ] Logs contain **no** CORS misconfiguration error

**Frontend**

- [ ] Loads at the static site URL
- [ ] Top bar: Backend and LLM green
- [ ] Hard-refresh on `/governance` works *(SPA rewrite)*
- [ ] AI Investigator returns a real answer
- [ ] No CORS errors in the browser console
- [ ] Demo toggle works

---

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Every panel shows **Demo**, console says "Cannot reach the API" | `VITE_API_URL` unset or wrong | Set it, then **Clear build cache & deploy** |
| Console: "blocked by CORS policy" | Frontend origin not in `CORS_ORIGINS` | Set it exactly, no trailing slash |
| First request takes ~50s | Free-tier cold start | Expected. Warm it before a demo |
| Refresh on a sub-route 404s | Missing SPA rewrite | Add `/*` → `/index.html` |
| Backend deploy fails: "no open ports" | Start command ignores `$PORT` | Use the exact start command above |
| `502 Bad Gateway` | Process crashed on boot | Check logs — usually a bad env value |
| DataHub always unreachable | Private URL | See [DataHub](#datahub-is-not-publicly-reachable) |
| LLM `configured: false` | No API key | Set `GROQ_API_KEY` and redeploy |

**Warm the service before demoing.** A free-tier cold start in front of judges
is avoidable:

```bash
curl https://dataguardian-api.onrender.com/api/v1/health
```

---

## Rollback

**Fastest** — Render Dashboard → service → **Events** → find the last good
deploy → **Rollback**. Takes about a minute.

**Via git**

```bash
git revert <bad-commit> && git push origin main   # preferred, keeps history
# or
git reset --hard <last-good> && git push --force origin main
```

**Config-only mistakes** don't need a rollback. Environment changes redeploy on
save — except `VITE_*`, which needs *Clear build cache & deploy*.

Disable `autoDeploy` in `render.yaml` before a demo if you want to freeze the
running version.

---

## Post-deploy

- [ ] Add the live URL to the README and Devpost
- [ ] Tag the release: `git tag -a v1.0.0 -m "Hackathon submission" && git push --tags`
- [ ] Capture screenshots from production ([docs/screenshots.md](screenshots.md))
- [ ] Warm both services ~10 minutes before presenting
