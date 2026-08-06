# Demo Script — 4 minutes

A tested walkthrough for judges. Timings are generous; the whole thing runs in
about 3:40 at a normal speaking pace.

**The one idea to land:** every other team will show an LLM answering questions
about data. This one shows an LLM that is *not allowed* to decide anything
factual — and that is why its answers can be trusted.

---

## Before you start

**T-10 minutes**

```bash
# 1. DataHub (slowest — start first)
datahub docker quickstart
python datahub/ingest_demo_metadata.py

# 2. Backend
cd backend && uvicorn app.main:app --reload

# 3. Frontend
cd frontend && npm run dev
```

**Pre-flight checklist**

- [ ] <http://localhost:5173> loads
- [ ] Top bar shows **Backend · DataHub · LLM** all green
- [ ] Overview shows **8 assets** (or 25 in Demo Mode)
- [ ] Run one throwaway query so the LLM connection is warm
- [ ] Browser at 100% zoom, notifications silenced, one tab only
- [ ] Dark theme (the product is designed dark-first)

**If anything is red:** click **Demo** in the top bar. The entire demo works
with no backend and no Docker. Say so plainly — "I'm running in Demo Mode so
we're not waiting on infrastructure" reads as competence, not as a failure.

---

## 0:00 — 0:30 · The problem

> "Data catalogues decay quietly. Ownership goes stale when people change
> teams. PII lands in tables nobody tagged. Deprecated datasets keep feeding
> live dashboards.
>
> DataHub is very good at *recording* all of that. It isn't designed to *act*
> on it — someone still has to notice, decide whether it matters, and fix it.
> In practice, nobody does.
>
> DataGuardian AI is an autonomous governance engineer that closes that loop."

*Screen: Overview page.*

---

## 0:30 — 1:00 · The posture

*Point at the metric row, then the health score.*

> "This is a live read of a real DataHub instance. 8 assets, three of them
> unowned, metadata health at 62.
>
> These numbers aren't estimated — they're computed from the metadata DataHub
> actually holds."

*Point at the top bar.*

> "And these are live status indicators. Backend, DataHub, the LLM provider,
> the cache, the scheduler. If anything here were red, you'd know the numbers
> were stale — instead of quietly seeing wrong data."

**Why this beat matters:** it establishes that everything after it is real.

---

## 1:00 — 2:15 · AI Investigator *(the centrepiece)*

*Navigate to AI Investigator. Click the suggested prompt* **Find datasets
without owners**.

While it runs (2–4 seconds):

> "This isn't a chatbot with a search box. It's a multi-step agent. It just
> planned which tools it needs, called them, scored the risk, and then asked a
> language model to explain what it found."

*Answer appears. Walk the sections top to bottom.*

> "Summary first — it named three specific datasets. Risk: HIGH, score 50.
> Then the evidence: each finding with the rule that triggered it and the
> points it carries. Then recommendations, each naming a real asset."

*Expand the **Execution Timeline**.* **← the moment that wins it**

> "Here's what actually happened. Planner. Dataset tool. Owner tool. Risk
> engine. Then the LLM.
>
> Notice what's missing — it never called the lineage tool or the statistics
> tool. It decided they weren't needed for an ownership question. That's the
> difference between an agent and a prompt: it *chose*.
>
> And look at the colours. Green stages are deterministic — rules, no model.
> Amber is generative. The risk score comes from the green path. **The LLM is
> never allowed to decide how risky something is.** It's told the score and
> asked to explain it.
>
> That means if I run this again, I get exactly the same 50. There's a test in
> the suite that proves it — it runs the agent twice with different model
> responses and requires identical findings."

*If time allows, ask a second question:* **Which datasets are highest risk?**

> "Different question, different plan — this time it *does* call lineage,
> because blast radius matters for a risk question."

---

## 2:15 — 2:45 · Lineage Explorer

*Navigate to Lineage Explorer. Pick* `fct_payments`.

> "This is why that unowned table matters. It feeds seventeen downstream
> assets — including the certified revenue rollup and the executive dashboard.
>
> Four node types: datasets, pipelines, dashboards, ML models. Colour is risk."

*Click the root node; the inspector opens.*

> "Owner: unassigned. Description: missing. And an AI summary explaining the
> blast radius in business terms.
>
> This is what turns 'a table has no owner' into 'the number on the CEO's
> dashboard has no accountable maintainer.'"

---

## 2:45 — 3:10 · Governance & Risk Center

*Navigate to Governance.*

> "The full catalogue — sortable on every column, filterable by severity,
> searchable. Health, documentation, and coverage as bars, because a steward
> scans this, they don't read it."

*Sort by Health ascending.*

> "Worst first. That's the work queue."

*Navigate to Risk Center.*

> "Risk distribution, the two-week trend, and the assets driving it."

*Point at a **Demo** tag.*

> "One thing I want to flag: this trend chart is labelled *Demo*. Trends need
> persisted scan history, which isn't built yet — so rather than invent a
> plausible-looking line, it says so. Every panel in the app is tagged Live or
> Demo.
>
> For a product whose whole pitch is trustworthy governance data, showing
> made-up numbers unlabelled would undercut the entire argument."

**This beat is worth the 15 seconds.** Judges have seen a dozen demos with
fabricated data presented as real. Volunteering the distinction is memorable.

---

## 3:10 — 3:40 · Architecture & close

*Navigate to Architecture.*

> "Briefly, how it's built. React and FastAPI. A LangGraph agent with nine
> nodes and conditional routing. A deterministic rule engine — six weighted
> rules. And a model-agnostic LLM layer supporting five providers with
> automatic fail-over.
>
> That fail-over isn't theoretical: during testing Groq hit a rate limit
> mid-run and it rolled over to Gemini without the request failing."

*Land the close.*

> "The reason I built it this way: an LLM asked to score governance risk will
> confidently invent violations that aren't in the data. In governance, a
> fabricated finding is worse than a missed one — it destroys trust in every
> other finding.
>
> So the rules decide what's wrong. The model only explains it. That's what
> makes this deployable rather than a demo.
>
> 293 tests, validated against a live DataHub v1.5.0.6."

---

## Question prep

**"How is this different from asking ChatGPT about your catalogue?"**
> Three things: it reads live DataHub metadata rather than recalling; it
> chooses its own tools per question; and the risk score is computed by rules,
> so it's reproducible. Ask ChatGPT twice and you get two answers. Ask this
> twice and the findings are byte-identical.

**"What happens when DataHub is down?"**
> Try it — the answer still comes back. Tool failures are contained, the run
> is marked `degraded: true`, the errors are listed, and the summary says the
> evidence is incomplete. A partial governance answer is useful; a stack trace
> isn't.

**"What if the LLM is down?"**
> It fails over to the next provider. If all of them are down, you still get
> the findings and the score — those never needed the model — and a
> deterministic summary built from the rules. There's a test for exactly that.

**"How would this scale to 100,000 assets?"**
> The read path already caches with a TTL and single-flight. The gap is
> incremental scanning — right now a scan pages the catalogue. The design has
> the seam for it: scan history lands in PostgreSQL next, which is also what
> unlocks real trend data.

**"Is the PII detection just regex?"**
> Yes, deliberately. It's word-boundary anchored so `emailer_job_id` isn't
> flagged as PII. A false positive costs a steward thirty seconds; a false
> negative is a compliance incident — but a *noisy* detector gets ignored
> entirely, which is worse than both. An LLM classifier is the upgrade path,
> as a *suggestion* layer on top, not as the decider.

---

## Recovery

| Problem | Say this, then do this |
| --- | --- |
| Agent is slow | "It's calling a real model — you can watch the pipeline stages fill in." *(the trace is genuinely interesting)* |
| DataHub red | "Switching to Demo Mode so we're not waiting on infrastructure." *Click Demo.* |
| LLM red | "The findings and score don't need the model — watch." *Run a query; deterministic summary appears.* |
| Anything else | Reload, click **Demo**, continue. The demo is fully functional offline. |

**Never apologise for Demo Mode.** It is a designed feature with a banner, not
a fallback you got caught in.
