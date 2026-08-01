# DataHub Integration Layer

Read-only access to DataHub metadata. Everything above this package —
the API routers today, the governance rule engine and the LangGraph agent
tomorrow — depends on `DataHubService` and `models.py`, never on GraphQL
documents or raw dictionaries.

## Layering

Each layer depends only on the ones below it.

| File | Responsibility | Depends on |
| --- | --- | --- |
| `service.py` | Public interface; decides what is an error; cache keys | mapper, queries, graphql, cache |
| `cache.py` | TTL + LRU + single-flight cache; never stores failures | — |
| `mapper.py` | Raw GraphQL dicts → Pydantic models | models |
| `queries.py` | GraphQL documents, composed from fragments | — |
| `graphql.py` | GraphQL envelope validation, error translation | client, exceptions |
| `client.py` | HTTP transport, auth, timeouts, retry loop | config, exceptions, retry |
| `retry.py` | Retryability classification; jittered backoff | exceptions |
| `models.py` | The typed contract | — |
| `exceptions.py` | Typed failures → HTTP status codes | core.exceptions |

Agent-facing wrappers live one package up in `app/tools/`; the full developer
guide is [`docs/datahub.md`](../../../../docs/datahub.md).

## Request flow

```
router  →  DataHubService  →  GraphQLClient  →  DataHubClient  →  DataHub GMS
   ↑            │                   │                │
   │            │                   │                └─ transport errors
   │            │                   └─ envelope errors    (timeout, refused,
   │            │                      (GraphQL errors,    401/403)
   │            │                       non-JSON, no data)
   │            └─ mapper: dicts → models
   └─ typed model, or a typed exception the handlers in app.main render
```

## Error semantics

The distinction matters to callers — retryable versus not:

| Exception | HTTP | Retryable | Cause |
| --- | --- | --- | --- |
| `DataHubConnectionError` | 503 | yes | DNS failure, connection refused/reset |
| `DataHubTimeoutError` | 504 | yes | Connected, no answer in time |
| `DataHubAuthenticationError` | 502 | no | Token missing, expired, or unprivileged |
| `DataHubQueryError` | 502 | no | GraphQL errors — usually a schema mismatch |
| `DataHubResponseError` | 502 | no | Not a valid GraphQL response |
| `DataHubEntityNotFoundError` | 404 | no | The URN does not exist |

Authentication failure is deliberately **not** 401: that would imply the caller
of *our* API is unauthenticated, when the actual problem is our server-side
`DATAHUB_TOKEN`.

## Empty is not an error

The single most important rule in this package. Sparse metadata is what
DataGuardian exists to find, so it must map cleanly rather than blow up:

* A dataset with no owner, description, domain, or tags → a valid model with
  empty fields.
* An asset with no lineage → `Lineage` with zero nodes, not a 404.
* A dataset with no profiling → empty `profiles`, not a 502.
* A blank-string description → normalised to `None`, since for governance
  purposes blank and absent are the same.
* A `lastModified` of `0` (DataHub's "never") → `None`, not 1970.

Only a URN that does not resolve is a 404.

## Health

Two endpoints, deliberately separate:

* `GET /api/v1/health` — liveness. Touches nothing external. Restart on this.
* `GET /api/v1/health/datahub` — DataHub connectivity. Always HTTP 200; read
  the `reachable` field. Never restart on this.

## Verifying against a live DataHub

Nothing in this package has yet run against a real instance — it was built and
tested against `httpx.MockTransport`. Before trusting it:

1. Start DataHub (`datahub docker quickstart`), then confirm
   `GET /api/v1/health/datahub` reports `reachable: true` with a version.
2. Work through the `TODO(datahub)` comments in `queries.py`. Each marks a
   field or operation whose availability depends on the DataHub version.
   Paste each document into GraphiQL at
   `http://localhost:9002/api/graphiql` and confirm it resolves.
3. Replace the hand-written doubles in `tests/fixtures.py` with recorded real
   responses, keeping the degenerate cases. Recorded fixtures catch schema
   drift that hand-written ones cannot.

A query asking for a field the instance does not expose fails the **whole**
query with a GraphQL error rather than returning a partial result, so step 2
is not optional.
