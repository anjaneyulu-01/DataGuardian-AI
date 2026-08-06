# Governance Agent

A multi-step reasoning agent built on LangGraph. It plans which tools to use,
gathers evidence, scores risk deterministically, and only then asks an LLM to
explain what was found.

---

## 1. Graph architecture

```
START
  │
  ▼
planner ──────────────────────────────────────────────┐
  │  classifies intent, selects tools                 │
  ▼                                                   │
datasets ─→ owners ─→ lineage ─→ statistics ─→ risk ──┤  every edge is
  (each edge consults state["plan"] and skips         │  CONDITIONAL
   any node the plan does not contain)                │
                                        risk          │
                                          │           │
                                          ▼           │
                                      reasoning ──────┘
                                          │
                              ┌───────────┴──────────┐
                              ▼                      ▼
                       recommendation             report
                              │                      │
                              └────────→ END ◄───────┘
```

Routing lives in **data**, not control flow. The planner writes
`state["plan"]` — a list of node names — and every edge asks "what is the next
node in the pipeline that appears in the plan?" Adding an intent is an entry
in a mapping, not a rewrite of the pipeline.

Compiled once per agent instance (`GovernanceAgent.__init__`), not per
request: compilation validates the whole topology.

---

## 2. Node responsibilities

| Node | Does | Never does |
| --- | --- | --- |
| `planner` | Classifies intent, picks tools, extracts a target URN/name | Fetch data |
| `datasets` | `DatasetTool` — one lookup, a search, or a bounded scan | Touch DataHub directly |
| `owners` | `OwnerTool` — one asset's owners, or the catalogue aggregation | Decide if unowned is *bad* |
| `lineage` | `LineageTool` — upstream + downstream from the highest-signal asset | Run when not planned |
| `statistics` | `StatisticsTool` — flat, prompt-sized profile summary | Treat absence as zero |
| `risk` | `RiskEngine` — the verdict, plus the evidence payload | Call an LLM (ever) |
| `reasoning` | LLM — executive summary + business impact | Compute or dispute the score |
| `recommendation` | LLM — corrective actions bounded by the findings | Invent a problem |
| `report` | LLM — formats an executive report | Introduce new facts |

Every node is a **factory** (`make_<name>_node(dependency)`) so dependencies
bind once at graph-build time, and every body is wrapped by
`executor.run_node`, which supplies timing, logging, failure containment, and
the trace entry — nine times, written once.

---

## 3. State flow

`AgentState` is a `TypedDict`; nodes return only the keys they changed and
LangGraph merges them. `trace` and `errors` use an append reducer so history
accumulates instead of being overwritten.

The state is deliberately partitioned by *who wrote it*:

```
question, intent, plan          ← planner
datasets, owners, lineage,      ← Tool layer   (facts)
  statistics
risk_score, risk_level,         ← RiskEngine   (deterministic verdict)
  findings, evidence
summary, business_impact,       ← LLM          (interpretation only)
  recommendations, next_steps
trace, errors, degraded         ← executor     (observability)
```

Anyone reading a response can tell which parts were derived and which were
generated. That is the point.

---

## 4. Tool selection

| Question | Tools run | Skipped |
| --- | --- | --- |
| "Find datasets without owners" | datasets, owners | lineage, statistics |
| "What is downstream of X?" | datasets, lineage | owners, statistics |
| "Which datasets are highest risk?" | datasets, owners, lineage | statistics |
| "Analyze governance health" | datasets, owners, statistics | lineage |
| "Create a governance report" | datasets, owners, statistics, + report | lineage |

Classification is **rules first, LLM second**: a keyword pass handles common
phrasings instantly and for free; the LLM is consulted only when scoring is a
near-tie, and if it is unreachable the rule verdict stands. Naming a specific
asset pulls lineage into the plan, because blast radius is the first question
anyone asks about a single table.

---

## 5. Why this is an agent, not a chatbot

| | Chatbot | This agent |
| --- | --- | --- |
| Tool use | Fixed, or none | **Chooses** tools per question |
| Steps | One turn | Multi-step graph with routing |
| Facts | Model recalls/invents | Fetched from DataHub via tools |
| Risk | Model asserts | Computed by rules, reproducibly |
| Failure | Errors out | Degrades, reports what is missing |
| Auditability | Opaque | Full node trace with timings |

Concretely: ask "find datasets without owners" and it *decides* not to call
lineage. Ask about downstream impact and it *decides* to. Both answers carry a
risk score that is byte-identical across runs because no sampled model
produced it.

The LLM is responsible for reasoning, explaining, summarising, documenting,
reporting, and recommending. It is **not** responsible for calculating risk,
checking owners, finding datasets, querying DataHub, or determining lineage.

---

## 6. Risk engine

| Rule | Points | Severity |
| --- | --- | --- |
| `untagged_pii` | 40 | critical |
| `missing_owner` | 30 | high |
| `missing_documentation` | 20 | medium |
| `large_downstream_impact` | 20 | high |
| `deprecated_in_use` | 15 | high |
| `schema_drift` | 15 | medium |

Bands: `≥70 critical · ≥40 high · ≥20 medium · else low`. Capped at 100.
Catalogue-wide scoring takes the **worst asset**, not the sum — summing would
make a large tidy catalogue look worse than a small dangerous one.

Two deliberate restraints:

* PII detection is word-boundary anchored, so `emailer_job_id` is not flagged
  as PII. A false positive erodes trust in every other finding.
* `schema_drift` fires only on an explicit signal. Real drift detection needs
  a stored previous schema (Phase 3); guessing would be worse than missing it.

---

## 7. Error handling

`executor.run_node` contains every node failure. The graph continues on
partial evidence and the result carries `degraded: true` plus the errors.

| Failure | Behaviour |
| --- | --- |
| One tool fails | Node marked FAILED, graph continues, `degraded` set |
| DataHub down | All tool nodes fail, findings empty, answer says so |
| LLM times out | Deterministic summary from the findings; score unaffected |
| Provider rate-limited | Fails over to the next configured provider |
| Whole graph fails | Still returns the contract, never raises to the API |

The endpoint returns **HTTP 200 for a degraded run**. A partial answer is a
result, not a transport failure; non-2xx is reserved for bad requests.

---

## 8. API

```http
POST /api/v1/agent/analyze
{ "question": "Find datasets without owners." }
```

```json
{
  "summary": "…",
  "risk_level": "high",
  "risk_score": 50,
  "findings": [{ "rule": "missing_owner", "points": 30, "asset_name": "fct_payments", … }],
  "recommendations": [{ "action": "…", "priority": "high" }],
  "evidence": [ … ],
  "business_impact": "…",
  "next_steps": [ … ],
  "trace": [{ "node": "planner", "status": "ok", "duration_ms": 0.4 }, … ],
  "degraded": false,
  "tools_used": ["planner", "datasets", "owners", "risk", "reasoning", "recommendation"]
}
```

---

## 9. Connecting the frontend

The response was shaped for the existing UI, so wiring is mostly deleting mock
data:

| UI surface | Field |
| --- | --- |
| `AIResponse` reasoning steps | `trace` (node names + timings) |
| `AIResponse` risk block | `risk_level`, `risk_score` |
| `AIResponse` evidence table | `evidence`, `findings` |
| `AIResponse` recommendation + actions | `business_impact`, `recommendations`, `next_steps` |
| Overview critical findings | `findings` filtered to `severity: critical` |
| Risk Center distribution | `findings` grouped by `severity` |

Steps:

1. Add `analyzeQuestion(question)` to `frontend/src/services/` posting to
   `/api/v1/agent/analyze`.
2. Replace `resolveAnswer()` in `InvestigatorPage.tsx` with that call — the
   `THINK_MS` timeout becomes real latency.
3. Map `AgentResult` → the existing `AIAnswer` type (a near 1:1 mapping).
4. Show `degraded` as a banner so a partial answer is never mistaken for a
   complete one.

Everything else in `mockData.ts` stays until the corresponding scan-history
endpoints exist.
