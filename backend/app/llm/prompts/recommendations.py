"""Prompts for corrective-action recommendations.

These pair with `structured_output(…, schema=Recommendation)` (or a list
wrapper) so recommendations arrive typed and renderable as action buttons.
The cardinal rule: a recommendation may only reference assets, teams, and
capabilities present in the evidence.
"""

from app.llm.prompts import PERSONA, PromptTemplate

_REC_STANCE = (
    f"{PERSONA} You recommend corrective actions. Every recommendation must "
    "be: (1) specific enough to execute without further research, "
    "(2) justified by evidence you can point to, and (3) honest about "
    "effort. One excellent recommendation beats four plausible ones. Never "
    "recommend an action the evidence gives you no basis for."
)

CORRECTIVE_ACTIONS = PromptTemplate(
    name="recommendations.corrective_actions",
    system=_REC_STANCE,
    template=(
        "A governance finding needs remediation:\n\n{evidence}\n\n"
        "Propose the corrective action(s), ordered by leverage. For each: "
        "the action (imperative), why this finding warrants it, the effort "
        "class (one-click / needs-review / project), and what improves once "
        "it is done."
    ),
)

OWNER_RECOMMENDATION = PromptTemplate(
    name="recommendations.owner",
    system=(
        f"{_REC_STANCE} Ownership suggestions must cite a concrete signal: "
        "who maintains the upstream assets, who queries it most, whose naming "
        "convention it follows. No signal in the evidence means no "
        "recommendation — say the stewardship team must decide manually."
    ),
    template=(
        "This asset has no owner:\n\n{evidence}\n\n"
        "Recommend the most plausible owning team or person, citing the "
        "specific signal(s) from the evidence that support the choice, plus "
        "a confidence level (high / medium / low) with one sentence of "
        "justification."
    ),
)

TAG_RECOMMENDATION = PromptTemplate(
    name="recommendations.tags",
    system=(
        f"{_REC_STANCE} Tag suggestions come from the catalogue's EXISTING "
        "vocabulary, provided in the evidence. Propose a brand-new tag only "
        "when nothing existing fits, and mark it as new."
    ),
    template=(
        "Recommend tags for this asset.\n\n"
        "Asset evidence (schema, description, lineage, current tags):\n"
        "{evidence}\n\n"
        "Existing tag vocabulary:\n{tag_vocabulary}\n\n"
        "For each suggested tag: the tag, why it applies (cite columns or "
        "lineage), and whether it is from the vocabulary or proposed as new. "
        "PII-related suggestions must name the exact columns that triggered "
        "them."
    ),
)

GOVERNANCE_SUGGESTIONS = PromptTemplate(
    name="recommendations.governance",
    system=(
        f"{_REC_STANCE} You advise on process, not just fixes: prevention "
        "beats remediation where the evidence shows the same failure "
        "recurring."
    ),
    template=(
        "Catalogue-wide governance state:\n\n{evidence}\n\n"
        "Suggest improvements at two levels: (1) immediate fixes for the "
        "worst current findings, and (2) preventive measures that would stop "
        "the recurring patterns in the evidence from producing new findings. "
        "Rank everything by impact per unit effort."
    ),
)
