# LLM Layer

Model-agnostic reasoning for DataGuardian AI. Grok (xAI) is the default
provider; Gemini, OpenAI, and Claude are registered placeholders that become
real by adding one file each.

---

## 1. Architecture

```
        Tool layer (deterministic)              app/tools/
   DatasetTool · OwnerTool · LineageTool · StatisticsTool
                        │
                        │  structured JSON evidence
                        ▼
        Rule engine (deterministic)      [Phase 3 — not built yet]
        computes severity, coverage, blast radius
                        │
                        │  evidence + pre-computed verdicts
                        ▼
   ┌───────────────────────────────────────────────────────┐
   │  prompts/    governance · documentation · reports ·    │
   │              recommendations   (templates, reviewable) │
   └───────────────────────────┬───────────────────────────┘
                               ▼
   ┌───────────────────────────────────────────────────────┐
   │  BaseLLM (base.py)                                     │
   │  generate() · chat() · summarize() · structured_output()│
   │  · health()                                            │
   └───────────────────────────┬───────────────────────────┘
                               ▼
   ┌───────────────────────────────────────────────────────┐
   │  factory.py — LLM_PROVIDER selects the implementation   │
   └───────────────────────────┬───────────────────────────┘
                               ▼
        providers/grok.py  →  https://api.x.ai/v1
        providers/gemini.py, openai.py, claude.py  (planned)
```

Files:

| File | Responsibility |
| --- | --- |
| `base.py` | The contract. Providers implement `chat` + `health`; everything else is built here so it never diverges between vendors. |
| `factory.py` | `LLM_PROVIDER` → provider instance. The only place that knows concrete classes. |
| `providers/grok.py` | xAI transport: auth, timeouts, retries, response mapping. |
| `prompts/` | Every prompt in the product, as `PromptTemplate` objects. |
| `models.py` | `LLMResponse`, `RiskExplanation`, `Recommendation`, `StructuredReport`, `LLMHealth`. |
| `retry.py` | What is transient; jittered exponential backoff. |
| `exceptions.py` | Typed failures → HTTP status codes. |

---

## 2. Adding a new provider

Three steps. None of them touch business logic.

**1. Implement two methods.**

```python
# app/llm/providers/gemini.py
class GeminiProvider(BaseLLM):
    name = "gemini"

    async def chat(
        self, messages, *, temperature=None, max_tokens=None, json_mode=False
    ) -> LLMResponse: ...

    async def health(self) -> LLMHealth: ...
```

`generate`, `summarize`, and `structured_output` come free from `BaseLLM` —
including JSON extraction, schema validation, and the repair round-trip.

**2. Register it** in `factory.py`:

```python
_REGISTRY["gemini"] = lambda settings: GeminiProvider(settings=settings)
```

**3. Add credentials** to `Settings` and `.env.example`.

Then `LLM_PROVIDER=gemini` switches the whole application. No caller changes,
because no caller ever imported `GrokProvider`.

**Contract for implementers:** translate transport failures into the typed
exceptions in `exceptions.py` (that is how retry classification works),
never raise from `health()`, and put no business logic in the provider.

---

## 3. How prompts work

Prompts are data, not string literals buried in functions:

```python
from app.llm.prompts import governance

prompt = governance.RISK_EXPLANATION.render(evidence=evidence_json)
response = await llm.generate(prompt, system=governance.RISK_EXPLANATION.system)
```

Every template has a `name`, a `system` stance, and a `template` with declared
placeholders. `render()` fails loudly on a missing or unknown placeholder —
a silently unfilled `{evidence}` would otherwise send the model a prompt with
a hole in it.

Three conventions every prompt follows:

- **`{evidence}` is always structured JSON from the Tool layer** and is
  declared ground truth. Enforced by a test: every prompt requires `evidence`.
- **The persona is shared.** All system prompts embed `prompts.PERSONA`, so
  the product's voice is edited in one place. Also test-enforced.
- **The audience is named** in the system prompt — steward, executive,
  engineer. It is the highest-leverage lever on tone.

To tune a prompt, edit the template. No business logic changes.

---

## 4. How the Tool layer talks to the LLM

The pattern for the whole product:

```python
# 1. DETERMINISTIC: gather facts. No LLM involved.
dataset = await tools.datasets.get(urn)
owners = await tools.owners.for_dataset(urn)
lineage = await tools.lineage.impact(urn)
stats = await tools.statistics.summary(urn)

# 2. DETERMINISTIC: compute the verdict. (Rule engine, Phase 3.)
severity = rules.score(dataset, owners, lineage, stats)

# 3. Serialise everything as evidence.
evidence = json.dumps(
    {
        "asset": DataHubTool.serialize(dataset),
        "owners": DataHubTool.serialize(owners),
        "lineage": {"downstream_count": lineage["downstream"].total},
        "statistics": stats,
        "computed_severity": severity,  # the LLM does NOT decide this
    },
    indent=2,
)

# 4. LLM: explain what the deterministic layers already decided.
explanation = await llm.structured_output(
    governance.RISK_EXPLANATION.render(evidence=evidence),
    schema=RiskExplanation,
    system=governance.RISK_EXPLANATION.system,
)
```

The LLM receives JSON. It never receives a DataHub client, a URN to look up,
or permission to fetch anything. `DataHubTool.serialize()` produces the
JSON-safe payload.

---

## 5. Why deterministic logic is separated from reasoning

This is the core design commitment, and it is what makes the output
trustworthy in a governance context.

**The LLM is NOT responsible for:** calculating risk · checking owners ·
finding datasets · querying DataHub · determining lineage.

**The LLM IS responsible for:** reasoning · explaining · summarizing ·
writing documentation · creating reports · making recommendations.

Four reasons this boundary is non-negotiable:

1. **Correctness.** "Does this dataset have an owner?" has one right answer,
   available from an API call. Asking a language model to infer it introduces
   error where none needed to exist.
2. **Auditability.** A steward challenged on a finding needs "the ownership
   aspect is empty and 17 downstream assets consume it" — a reproducible
   fact — not "the model concluded this."
3. **Consistency.** The same catalogue state must always yield the same
   severity. Deterministic rules guarantee that; sampling does not.
4. **Cost and speed.** Scanning 412 assets is one query plus rule evaluation.
   Only the handful of assets that actually failed a rule need an LLM call.

The division also makes failure modes survivable: if the LLM is down, scans
still run and findings are still detected — the product loses its
explanations, not its detection.

---

## 6. Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `grok` | Implemented: `grok`. Placeholders: `gemini`, `openai`, `claude`. |
| `XAI_API_KEY` | — | From <https://console.x.ai>. Absent = app boots, LLM calls fail with a clear error. |
| `XAI_MODEL` | `grok-4-fast-reasoning` | |
| `XAI_BASE_URL` | `https://api.x.ai/v1` | |
| `LLM_TIMEOUT` | `60` | Generous: reasoning models are slow. |
| `LLM_MAX_TOKENS` | `4096` | |
| `LLM_TEMPERATURE` | `0.2` | Low by design — grounded explanation, not creativity. |
| `LLM_MAX_RETRIES` | `2` | Extra attempts on transient failures only. |

Check status: `GET /api/v1/health/llm`. It distinguishes `configured: false`
(no key) from `reachable: false` (key present, provider unreachable or
rejecting), and spends no tokens.

---

## 7. Error semantics

| Exception | HTTP | Retried | Cause |
| --- | --- | --- | --- |
| `LLMConfigurationError` | 503 | no | No API key; unknown model |
| `LLMProviderNotSupportedError` | 503 | no | `LLM_PROVIDER` unimplemented |
| `LLMConnectionError` | 503 | **yes** | Provider unreachable, transient 5xx |
| `LLMTimeoutError` | 504 | **yes** | No answer within `LLM_TIMEOUT` |
| `LLMRateLimitError` | 503 | **yes** | HTTP 429 (backs off harder) |
| `LLMAuthenticationError` | 502 | no | Key rejected |
| `LLMResponseError` | 502 | no* | Malformed/empty output |

\* `structured_output` makes exactly **one** repair round-trip, feeding the
validation errors back. Almost-valid JSON is the most common LLM failure and
one nudge usually fixes it; a second failure propagates rather than poisoning
downstream consumers with bad data.

---

## 8. Notes on implementation choices

**Why httpx, not the xAI SDK.** xAI documents the OpenAI-compatible endpoint
as a first-class interface. httpx is already a project dependency with an
established `MockTransport` testing pattern, so the whole provider is
testable without network or credentials. The SDK can slot in behind
`GrokProvider` later without touching a single caller.

**Streaming.** Not implemented — nothing consumes it yet, and shipping an
unused streaming path would be untested surface area. The design is ready:
`_post_chat` is the single transport seam, and a `stream=True` branch using
`client.stream()` would add an `astream()` method without changing `chat()`
or any caller.

**Why `retry.py` duplicates the DataHub one.** The two classify different
exception families and have different backoff needs (LLM 429s want a longer
wait). Sharing them would mean a DataHub tuning change silently altering LLM
behaviour. The ~40 lines of similarity buys that independence.

---

## 9. Ready for LangGraph

Tomorrow's agent needs exactly two things from this layer, and both exist:

- `BaseLLM` via DI (`LLMDep` in `app/api/deps.py`), so nodes call
  `await llm.structured_output(...)` without knowing the vendor.
- Typed outputs (`RiskExplanation`, `Recommendation`, `StructuredReport`)
  that drop straight into graph state without parsing.

Nothing in this layer imports LangGraph, and nothing needs to change when it
arrives.
