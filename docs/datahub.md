# DataHub Integration — Developer Guide

How the DataGuardian backend talks to DataHub, and how to work on that code
without breaking the contracts the rest of the system depends on.

- Package: [`backend/app/integrations/datahub/`](../backend/app/integrations/datahub/)
- Agent-facing wrappers: [`backend/app/tools/`](../backend/app/tools/)
- Acceptance harness: [`backend/scripts/validate_datahub.py`](../backend/scripts/validate_datahub.py)

---

## 1. Architecture

```
                       HTTP (FastAPI routers)          AI agent (tomorrow)
                              │                              │
                              ▼                              ▼
                      ┌──────────────┐              ┌──────────────────┐
                      │ api/v1/*.py  │              │ app/tools/*.py   │
                      └──────┬───────┘              └────────┬─────────┘
                             │      both depend only on      │
                             ▼                               ▼
                      ┌─────────────────────────────────────────┐
                      │        DataHubService  (service.py)     │  ← decides what
                      │  + TTLCache (cache.py, 60s, no failures)│    is an error
                      └────────────────────┬────────────────────┘
                                           │
                      ┌────────────────────▼────────────────────┐
                      │  mapper.py   raw dicts → Pydantic models│  ← absorbs schema
                      └────────────────────┬────────────────────┘    changes
                                           │
                      ┌────────────────────▼────────────────────┐
                      │  queries.py  GraphQL documents+fragments │
                      └────────────────────┬────────────────────┘
                      ┌────────────────────▼────────────────────┐
                      │  graphql.py  envelope validation         │  ← GraphQL says
                      └────────────────────┬────────────────────┘    200 on failure
                      ┌────────────────────▼────────────────────┐
                      │  client.py   HTTP, auth, timeout, retry  │
                      └────────────────────┬────────────────────┘
                                           ▼
                                   DataHub GMS  /api/graphql
```

Each layer depends only on the ones below it. The two contracts everything
hangs on:

1. **Callers see `models.py`, never raw GraphQL dicts.** When DataHub changes
   its schema, `mapper.py` (and possibly `queries.py`) change; nothing else.
2. **Empty is not an error.** A dataset with no owner, description, domain, or
   lineage maps cleanly — sparse metadata is the thing this product detects.
   Only an unresolvable URN raises (`DataHubEntityNotFoundError` → 404).

## 2. Authentication

- `DATAHUB_TOKEN` in the repo-root `.env` becomes `Authorization: Bearer <token>` on
  every request (see `DataHubClient._build_headers`).
- No token: works only against a local quickstart with metadata-service auth
  disabled. The app logs a warning at startup in this state.
- Token creation: DataHub UI → Settings → Access Tokens → Generate.
- A 401/403 from GMS raises `DataHubAuthenticationError`, surfaced as **502**
  (not 401 — the caller of *our* API is not the one who is unauthenticated).
  It is never retried and never cached.

## 3. GraphQL endpoint

| Setting | Default | Meaning |
| --- | --- | --- |
| `DATAHUB_GMS_URL` | `http://localhost:8080` | GMS base URL |
| `DATAHUB_GRAPHQL_PATH` | `/api/graphql` | appended to the base |
| `DATAHUB_TIMEOUT_SECONDS` | `30` | per-request timeout |
| `DATAHUB_MAX_RETRIES` | `2` | extra attempts on transient failures |
| `DATAHUB_CACHE_TTL_SECONDS` | `60` | metadata cache TTL |

Going through the DataHub frontend proxy instead: set
`DATAHUB_GMS_URL=http://localhost:9002/api/gms`.

Interactive exploration: **GraphiQL** at `http://localhost:9002/api/graphiql`
(log in to the UI first). This is the fastest way to check whether a field
exists on your DataHub version.

## 4. Folder responsibilities

| File | Owns | Never contains |
| --- | --- | --- |
| `client.py` | pooling, auth header, timeouts, retry loop, 401/403 + transient-5xx translation | GraphQL knowledge |
| `graphql.py` | the `{data, errors}` envelope; typed errors for non-JSON, GraphQL errors, missing data | field names, mapping |
| `queries.py` | every GraphQL document, composed from fragments | runtime logic |
| `models.py` | the Pydantic contract callers depend on | GraphQL naming (camelCase) |
| `mapper.py` | dict→model translation; all null-safety | I/O, HTTP, caching |
| `service.py` | operation choice, pagination clamps, error semantics, cache keys | raw dict handling beyond `as_dict` |
| `cache.py` | TTL + LRU + single-flight; never stores failures | DataHub specifics |
| `retry.py` | what is retryable; jittered backoff | HTTP details |
| `exceptions.py` | typed failures → HTTP status | anything else |

## 5. How metadata flows

`GET /api/v1/datasets?query=*&count=20`:

1. Router validates query params and receives a `DataHubService` from DI
   (`app/api/deps.py` — one shared `DataHubClient` + one shared `TTLCache`
   from `app.state`, both created in the lifespan).
2. Service clamps pagination, builds cache key
   `datasets(count=20,query='*',start=0)`, and asks the cache.
3. On a miss, `GraphQLClient.execute` posts `LIST_DATASETS` with variables
   (URNs and queries always travel as variables, never interpolated).
4. `client.py` sends it with auth and timeout; transient failures are retried
   with jittered exponential backoff (`0.5s → 1s → 2s`, capped, full jitter).
5. `graphql.py` validates the envelope. GraphQL failures arrive as HTTP 200
   with an `errors` array — this layer is why they cannot slip through.
6. `mapper.py` turns the payload into `Page[DatasetSummary]`.
7. The cache stores the success (never a failure), the router returns it, and
   FastAPI serialises the models to snake_case JSON.

## 6. Adding a new query

1. **Prototype in GraphiQL** until it returns what you expect on the running
   DataHub version.
2. Add the document to `queries.py`. Reuse fragments (`FRAGMENT_OWNER`,
   `FRAGMENT_DATASET_SUMMARY`, …) rather than repeating field lists; compose
   with `_document(body, *fragments)`.
3. Add or extend models in `models.py`. Every new field is optional unless it
   is a URN — sparse metadata must not fail validation.
4. Write the mapper function in `mapper.py` using the `_dig`/`_text`/`_int`
   helpers. Never index a raw dict directly.
5. Add the service method in `service.py`: clamp pagination, decide the
   error semantics, and add a cache key if the result is cacheable.
6. Mirror the degenerate cases in `tests/fixtures.py` (null aspects, blank
   strings, missing URNs) and cover mapper + service + endpoint.
7. Run `python scripts/validate_datahub.py --graphql-only` against the live
   instance.

## 7. How tools use services

`app/tools/` wraps `DataHubService` for tomorrow's agent. Each tool adds a
name, an LLM-facing description, primitive-typed methods (an LLM calls tools
with JSON arguments, not model instances), and case-tolerant enum parsing.
They do **not** add error handling — typed exceptions propagate so the agent
can distinguish "retry later" (`DataHubConnectionError`, `DataHubTimeoutError`)
from "this will never work" (`DataHubQueryError`, `DataHubEntityNotFoundError`).

```python
from app.tools import build_tools

tools = build_tools(service)          # one service → shared cache and pool
page = await tools.datasets.list(count=10)
unowned = await tools.datasets.list_unowned()
blast = await tools.lineage.downstream_count(urn)
brief = await tools.statistics.summary(urn)      # flat dict, prompt-sized
manifest = tools.describe()                      # names + descriptions for the LLM
```

Rule of thumb: convenience filters (`list_unowned`) belong in tools;
*judgement* (severity, whether it is a violation) belongs in the rule engine,
which does not exist yet.

## 8. Common debugging steps

**`/health/datahub` says `reachable: false`**
- Read its `error` field first — it names the URL tried and the failure.
- `GMS returned HTTP 404 from /config`: something else is on that port
  (check `Get-NetTCPConnection -LocalPort 8080 -State Listen`).
- Connection refused: containers down — `datahub docker quickstart` and wait
  for healthy.

**502 with `DataHubQueryError ... Cannot query field 'X'`**
- Schema mismatch: your DataHub version does not expose a field a document
  asks for. Reproduce in GraphiQL, trim or gate the field in `queries.py`,
  and note the version dependency in the query's comment.

**502 with `DATAHUB_TOKEN` in the message**
- Token missing/expired/unprivileged. Regenerate in the UI. Restart the API
  after editing `.env` (settings are read once at import).

**Everything slow**
- Check `latency_ms` on `/health/datahub` — that is raw GMS round-trip.
- Confirm the cache is on (startup log line says `cache=60s TTL`).
- `python scripts/validate_datahub.py` prints per-operation latency and flags
  anything over 1s.

**Stale data after re-ingesting metadata**
- The cache TTL is 60s. Wait it out, restart the API, or set
  `DATAHUB_CACHE_ENABLED=false` while iterating on ingestion.

**Every GraphQL query failing at once**
- Almost always the endpoint, not the queries: wrong `DATAHUB_GMS_URL`, or a
  proxy returning HTML (the error message includes a body snippet — HTML
  there means a login or error page, not GMS).
