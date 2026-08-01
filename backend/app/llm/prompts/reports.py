"""Prompts for governance reports.

Reports are generated as `StructuredReport` via `structured_output`, so these
templates pair with that schema: the caller passes aggregated scan data as
`{evidence}` and receives titled sections plus recommendations.
"""

from app.llm.prompts import PERSONA, PromptTemplate

_REPORT_STANCE = (
    f"{PERSONA} You write governance reports that people actually read. "
    "Lead with what changed and what needs a decision. Numbers come from the "
    "evidence verbatim — never rounded up, never extrapolated. If a section "
    "has nothing noteworthy, say 'Nothing significant' in one line rather "
    "than manufacturing content."
)

EXECUTIVE_SUMMARY = PromptTemplate(
    name="reports.executive_summary",
    system=(
        f"{_REPORT_STANCE} Audience: an executive with ninety seconds. "
        "Three short paragraphs maximum. No table names unless a decision "
        "hinges on one."
    ),
    template=(
        "Write an executive summary of the current governance posture.\n\n"
        "Aggregated evidence:\n{evidence}\n\n"
        "Paragraph 1: overall posture and direction of travel. "
        "Paragraph 2: the single most important risk and its business "
        "consequence. Paragraph 3: what you recommend and what it costs."
    ),
)

DAILY_REPORT = PromptTemplate(
    name="reports.daily",
    system=(
        f"{_REPORT_STANCE} Audience: the data platform team's morning "
        "stand-up. Terse and scannable."
    ),
    template=(
        "Write the daily governance report for {report_date}.\n\n"
        "Scan results and deltas since yesterday:\n{evidence}\n\n"
        "Sections: New findings (with severity) · Resolved since yesterday · "
        "Trend one-liner · Today's recommended action (exactly one)."
    ),
)

WEEKLY_REPORT = PromptTemplate(
    name="reports.weekly",
    system=(
        f"{_REPORT_STANCE} Audience: data leadership review. Focus on trend "
        "and systemic causes, not individual assets — except the week's most "
        "consequential finding, which deserves a short narrative."
    ),
    template=(
        "Write the weekly governance report for the week of {week_start}.\n\n"
        "This week's aggregated evidence (counts, deltas, top findings, "
        "resolution times):\n{evidence}\n\n"
        "Sections: Posture vs last week · What drove the change · Story of "
        "the week (one finding, from detection to state today) · Systemic "
        "observations · Priorities for next week (max three, ranked)."
    ),
)
