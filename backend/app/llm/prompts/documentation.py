"""Prompts for generating documentation drafts.

Output from these templates is always a DRAFT for human review — the write-
back to DataHub happens only after a steward approves. Each prompt receives
the asset's real schema/profile/lineage as `{evidence}` and is told to mark
uncertainty rather than paper over it.
"""

from app.llm.prompts import PERSONA, PromptTemplate

_DOC_STANCE = (
    f"{PERSONA} You draft documentation for human review — accuracy beats "
    "completeness. Where the evidence does not tell you something (a column's "
    "business meaning, a refresh cadence), write '[NEEDS REVIEW: …]' instead "
    "of guessing. Match the tone of well-maintained internal docs: direct, "
    "specific, no marketing."
)

README_GENERATION = PromptTemplate(
    name="documentation.readme",
    system=_DOC_STANCE,
    template=(
        "Draft a README for the dataset below.\n\n"
        "Asset evidence (schema, profile, lineage, current metadata):\n"
        "{evidence}\n\n"
        "Structure: Purpose · Grain (one row is…) · Refresh · Key columns · "
        "Caveats. Derive the grain from the primary keys in the evidence; if "
        "none are present, mark it for review."
    ),
)

DATASET_DOCUMENTATION = PromptTemplate(
    name="documentation.dataset",
    system=_DOC_STANCE,
    template=(
        "Draft column-level documentation for this dataset.\n\n"
        "Schema and profiling evidence:\n{evidence}\n\n"
        "For every column: a one-sentence description inferred from its name, "
        "type, and profile stats (null rate, distinct count, min/max where "
        "present). Flag columns whose names match personal-data patterns. "
        "Return a markdown table: Column | Type | Description."
    ),
)

BUSINESS_DESCRIPTION = PromptTemplate(
    name="documentation.business",
    system=(
        f"{_DOC_STANCE} Your reader is a business stakeholder with no SQL. "
        "No jargon, no column names unless unavoidable."
    ),
    template=(
        "Write a plain-language business description of this dataset.\n\n"
        "Evidence:\n{evidence}\n\n"
        "Cover: what this data is, who relies on it (from the downstream "
        "lineage), and anything a business reader should know about its "
        "current governance state (unowned, undocumented, deprecated…)."
    ),
)

SQL_EXPLANATION = PromptTemplate(
    name="documentation.sql",
    system=(
        f"{PERSONA} You explain SQL to analysts who read queries but did not "
        "write this one. Explain intent, not syntax — and point out real "
        "hazards (silent row drops, fan-out joins, timezone traps) when the "
        "query actually contains them."
    ),
    template=(
        "Explain what this query does, step by step, in plain English:\n\n"
        "```sql\n{sql}\n```\n\n"
        "Context about the tables involved (may be empty):\n{evidence}\n\n"
        "End with a 'Watch out for' list ONLY if the query contains genuine "
        "hazards; omit the section otherwise."
    ),
)
