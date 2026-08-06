# Assets

Images referenced by the root [README](../README.md).

Every path below is already linked from the README, so dropping a file in with
the exact name makes it appear — no markdown edits needed.

```
assets/
├── github/
│   ├── banner.svg          1280×320  Hero banner    ✅ shipped
│   └── logo.svg              256×256  Square mark   ✅ shipped
└── screenshots/
    ├── overview.png
    ├── investigator.png
    ├── execution-timeline.png    ← the one that matters most
    ├── governance.png
    ├── lineage.png
    ├── risk-center.png
    ├── documentation.png
    └── architecture.png
```

## Capture settings

Use the same settings for all screenshots so the README reads as one set:

| Setting | Value |
| --- | --- |
| Theme | Dark |
| Browser width | 1440px |
| Zoom | 100% |
| Demo Mode | On — 25 assets across six domains, deterministic |

Demo Mode data never changes, so a screenshot retaken next week still matches
the others.

Full shot list, framing notes, and Devpost ordering:
**[docs/screenshots.md](../docs/screenshots.md)**

## Until the screenshots exist

GitHub shows broken-image icons for the eight screenshots. That is expected
before capture — it is not a broken build. Each image has descriptive alt text
that GitHub renders in place of the missing file, so the section still reads as
captions rather than gaps.

The hero is **not** affected: `banner.svg` and `logo.svg` are real, committed
files, so a fresh clone renders correctly from the first second.

## Banner and logo

Both are hand-written SVG rather than PNG, for three reasons: they render on
GitHub from a relative path, they stay a few KB, and they need no build step or
binary in git. Brand tokens match `frontend/src/index.css` — dark canvas
`#0f1219`, gradient `#5b8cff` → `#4dd8e8`.

The banner carries only **verified** counts (9 agent nodes, 6 risk rules, 5 LLM
providers, 12 GraphQL documents, 293 tests). If any of those change, update the
SVG — a banner that contradicts the README is worse than no banner.

To swap in a product shot instead, export the Overview page at 1280×320 and
save it as `github/banner.svg`'s replacement, updating the `<img src>` in the
root README. [`frontend/public/og-image.svg`](../frontend/public/og-image.svg)
is the matching 1200×630 social card.
