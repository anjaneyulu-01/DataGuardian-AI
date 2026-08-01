"""Prompts for explaining governance findings.

Every template receives `{evidence}` — structured JSON assembled by the Tool
layer and rule engine. The LLM explains what the deterministic layer found;
it never re-derives or extends it.
"""

from app.llm.prompts import PERSONA, PromptTemplate

RISK_EXPLANATION = PromptTemplate(
    name="governance.risk_explanation",
    system=(
        f"{PERSONA} You write for a data steward who must decide, in under a "
        "minute, whether to act today. The severity has already been computed "
        "by deterministic rules — your job is to make its consequences vivid "
        "and concrete, not to re-assess it."
    ),
    template=(
        "A governance scan flagged the asset below. Explain the risk.\n\n"
        "Evidence (ground truth, computed by the rule engine):\n{evidence}\n\n"
        "Cover: what is wrong, why it matters to the business, what the "
        "downstream exposure is (use only the lineage in the evidence), and "
        "what happens if nobody acts. Be specific; no filler."
    ),
)

GOVERNANCE_ANALYSIS = PromptTemplate(
    name="governance.analysis",
    system=(
        f"{PERSONA} You write a catalogue-level assessment for a head of data "
        "platform. Patterns and priorities, not asset-by-asset listings."
    ),
    template=(
        "Here is the current governance state of the catalogue:\n\n"
        "{evidence}\n\n"
        "Analyze it: where is risk concentrated, what systemic patterns "
        "explain the findings (team gaps, platform gaps, process gaps), and "
        "which THREE actions would improve the posture most per unit effort? "
        "Rank them."
    ),
)

MISSING_OWNER_ANALYSIS = PromptTemplate(
    name="governance.missing_owner",
    system=(
        f"{PERSONA} You help route ownership decisions. Candidate owners can "
        "only come from signals present in the evidence — lineage neighbours, "
        "query history, team naming conventions. If the evidence supports no "
        "candidate, say so plainly."
    ),
    template=(
        "The following assets have no owner:\n\n{evidence}\n\n"
        "For each: explain the operational risk of it staying unowned given "
        "its downstream consumers, and — only where the evidence contains a "
        "signal — suggest the most plausible owning team with the signal that "
        "supports it."
    ),
)

LINEAGE_EXPLANATION = PromptTemplate(
    name="governance.lineage",
    system=(
        f"{PERSONA} You translate lineage graphs into narratives a "
        "non-engineer can follow. Hop counts and asset names come from the "
        "evidence only."
    ),
    template=(
        "Lineage for {asset_name}:\n\n{evidence}\n\n"
        "Explain in plain language: where this data comes from, what depends "
        "on it, and which downstream surfaces (dashboards, ML features, "
        "certified marts) would be affected by a bad load. End with a one-"
        "sentence blast-radius statement."
    ),
)

PII_EXPLANATION = PromptTemplate(
    name="governance.pii",
    system=(
        f"{PERSONA} You explain personal-data exposure to a privacy-conscious "
        "but non-legal audience. Flag risk factually; do not give legal advice "
        "or cite specific regulations as if providing counsel."
    ),
    template=(
        "A scan detected probable untagged PII:\n\n{evidence}\n\n"
        "Explain: which columns look like personal data and why (pattern "
        "matches are in the evidence), how the exposure propagates through "
        "the listed downstream consumers, and what the tagging fix involves. "
        "Keep it factual and calm."
    ),
)
