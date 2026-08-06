# Screenshot Plan

Captures for the README and the Devpost submission.

Save to `docs/images/` using the exact filenames below — the README already
references them.

---

## Setup (do this once)

| Setting | Value | Why |
| --- | --- | --- |
| Theme | **Dark** | The product is designed dark-first |
| Browser width | **1440px** | All five top-bar indicators visible; wider looks empty |
| Zoom | **100%** | Anything else softens the type |
| Demo Mode | **On** | 25 assets across six domains reads better than 8 |
| Chrome | Hide bookmarks bar, close devtools, one tab | |

```bash
# Deterministic dataset, no infrastructure needed
cd frontend && npm run dev
# then click "Demo" in the top bar
```

Demo Mode data is fixed, so screenshots stay reproducible — you can retake one
later and it will match the others.

**Capture:** `Win + Shift + S` (Windows) or `Cmd + Shift + 4` (macOS).
Full-window, not full-screen — the OS chrome adds nothing.

---

## Required shots

### 1. `overview.png` — the landing impression

**Route:** `/`
**Wait for:** the health score ring to finish animating (~1.2s)

Frame the metric row, the health score, and the first critical finding. This
is the thumbnail on Devpost, so it carries the most weight.

- [ ] Captured

---

### 2. `investigator.png` — the hero feature

**Route:** `/investigator` → run **"Find datasets without owners"**
**Wait for:** the full answer, all sections rendered

Frame the question, summary, risk badge, and the evidence table. Scroll so the
risk score is visible — that number is the product's claim.

- [ ] Captured

---

### 3. `execution-timeline.png` — the differentiator ⭐

**Route:** same answer, **Execution Timeline expanded**

**The single most important screenshot.** It shows tools being *chosen* — the
skipped lineage and statistics stages are the evidence this is an agent and
not a prompt. Make sure the green/amber colour split is visible; that is the
deterministic-vs-generative boundary in one image.

- [ ] Captured

---

### 4. `governance.png` — the catalogue

**Route:** `/governance`, sorted by **Health ascending**

Worst assets first. Frame enough rows to show the health/documentation/coverage
bars and a mix of severity badges, including at least one **Unowned** pill.

- [ ] Captured

---

### 5. `lineage.png` — blast radius

**Route:** `/lineage` → select `fct_payments` → click the root node

Inspector drawer open. Frame the graph *and* the drawer together — the graph
alone doesn't explain itself, and the drawer alone loses the context.

- [ ] Captured

---

### 6. `risk-center.png` — where risk concentrates

**Route:** `/risk`

Frame the four severity cards and the trend chart. Include a **Demo** tag if
one is in frame — visible honesty about data provenance is a feature.

- [ ] Captured

---

### 7. `architecture.png` — engineering credibility

**Route:** `/architecture`

Frame the "Deterministic rules decide what is wrong" banner and the system
diagram. Proves the design was deliberate rather than accidental.

- [ ] Captured

---

## Optional, high value

### 8. `documentation.png`

`/documentation` → generate a README → preview rendered. Shows AI writing, not
just AI reading.

- [ ] Captured

### 9. `demo-mode-banner.png`

Any page with the amber Demo banner visible. Judges notice teams that label
their sample data.

- [ ] Captured

### 10. `degraded.png`

Stop the backend, reload, run a query. Shows graceful degradation — rare in a
hackathon build and genuinely differentiating.

- [ ] Captured

---

## Devpost gallery order

1. `overview.png` — what it is
2. `investigator.png` — what it does
3. `execution-timeline.png` — why it's trustworthy
4. `lineage.png` — why the finding matters
5. `governance.png` — the scale
6. `architecture.png` — how it's built

Caption each with the *claim*, not the feature name:

> ❌ "Execution timeline"
> ✅ "The agent chose its tools — lineage and statistics were skipped because an ownership question doesn't need them."

---

## Optional: a 30-second GIF

If Devpost allows it, one GIF beats three static shots:

1. Type a question in the Investigator
2. Loading pipeline animates
3. Answer resolves
4. Execution timeline expands

Keep it under 5 MB. [ScreenToGif](https://www.screentogif.com/) (Windows) or
[Kap](https://getkap.co/) (macOS).

- [ ] Captured
