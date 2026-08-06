/**
 * Human-readable documentation for each deterministic rule.
 *
 * The backend already sends `rule`, `title`, `severity`, `points`, and a
 * per-asset `detail` with every finding — those are the authoritative values
 * and the UI renders them verbatim. What the API does not send is the
 * *policy* behind a rule: why it is weighted the way it is, and which piece
 * of DataHub metadata it reads.
 *
 * That rationale is static documentation, so it lives here rather than being
 * shipped on every response. Keep the keys in step with `RULES` in
 * `backend/app/agents/risk_engine.py`; an unknown key degrades to a generic
 * description rather than breaking the panel.
 */

export interface RuleDoc {
  /** Why this rule carries the weight it does. */
  rationale: string
  /** The DataHub metadata the rule reads to make its decision. */
  metadataUsed: string
  /** The concrete operational consequence of leaving it unfixed. */
  consequence: string
}

export const RULE_DOCS: Record<string, RuleDoc> = {
  untagged_pii: {
    rationale:
      'The heaviest weight in the rule book, because it is the only rule with a regulatory consequence rather than a productivity cost. Column names are matched against personal-data patterns, anchored on word boundaries so `emailer_job_id` is not flagged.',
    metadataUsed: 'Schema field names · classification tags',
    consequence:
      'Personal data is processed without a classification, so it is invisible to retention, access-control, and subject-access workflows.',
  },
  missing_owner: {
    rationale:
      'Weighted second because ownership is the precondition for every other fix. An unowned asset has no one to assign the remaining findings to.',
    metadataUsed: 'Ownership aspect (users and groups)',
    consequence:
      'No accountable responder when this asset breaks, so incidents route to whoever notices first.',
  },
  missing_documentation: {
    rationale:
      'A productivity cost rather than a compliance one, so it is weighted below ownership and PII. It compounds: every consumer re-derives the same knowledge independently.',
    metadataUsed: 'Dataset description · editable properties',
    consequence:
      'Consumers cannot tell what the asset means or whether it fits their use case, so they guess.',
  },
  large_downstream_impact: {
    rationale:
      'Not a defect on its own — it is a multiplier. Blast radius is what separates a backlog ticket from a priority, and it is the reason lineage matters to governance at all. Fires at five or more downstream consumers.',
    metadataUsed: 'Downstream lineage graph',
    consequence:
      'Any defect in this asset propagates to everything built on top of it.',
  },
  deprecated_in_use: {
    rationale:
      'Fires only when an asset is both deprecated AND still consumed. A deprecated asset with no consumers is a tidy retirement, not a finding.',
    metadataUsed: 'Deprecation aspect · downstream lineage',
    consequence:
      'Consumers are reading an asset nobody maintains, so they may be serving silently stale numbers.',
  },
  schema_drift: {
    rationale:
      'Fires only on an explicit upstream signal. Full drift detection needs a stored snapshot of the previous schema, which arrives with scan history — until then the rule never guesses, because a fabricated drift finding is worse than a missed one.',
    metadataUsed: 'Schema metadata · upstream drift signal',
    consequence:
      'The schema changed and downstream models may not have been updated to match.',
  },
}

const GENERIC: RuleDoc = {
  rationale:
    'A deterministic governance rule. Its weight and severity are defined in the backend rule book.',
  metadataUsed: 'DataHub metadata',
  consequence: 'See the finding detail for the specific consequence.',
}

export function ruleDoc(key: string): RuleDoc {
  return RULE_DOCS[key] ?? GENERIC
}
