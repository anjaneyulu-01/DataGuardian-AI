"""Centralized prompt system.

Every prompt in the product lives in this package as a `PromptTemplate` —
never inline in business logic — so prompts can be reviewed, diffed, and
tuned like the interface they are.

Conventions each template follows:

* **Evidence in, prose out.** The `{evidence}` placeholder always receives
  structured JSON produced by the Tool layer / rule engine. The prompt
  instructs the model to treat it as ground truth and never extend it.
* **The LLM never computes.** Severities, counts, owners, and lineage arrive
  pre-computed. Prompts ask for explanation and judgement about *presentation*,
  not for facts.
* **Audience is named.** Each prompt states who reads the output (steward,
  executive, engineer) — the single highest-leverage lever on tone.
"""

from dataclasses import dataclass, field
from string import Formatter


@dataclass(frozen=True)
class PromptTemplate:
    """A named prompt with a system stance and a user template.

    `render` validates that exactly the declared placeholders are supplied,
    so a renamed variable fails loudly at call time instead of silently
    producing a prompt with a literal `{evidence}` hole in it.
    """

    name: str
    system: str
    template: str
    required: frozenset[str] = field(init=False)

    def __post_init__(self) -> None:
        names = frozenset(
            fname for _, fname, _, _ in Formatter().parse(self.template) if fname
        )
        object.__setattr__(self, "required", names)

    def render(self, **values: str) -> str:
        """Fill the template, failing loudly on missing or unknown keys."""
        missing = self.required - values.keys()
        if missing:
            raise KeyError(
                f"Prompt '{self.name}' missing placeholders: {sorted(missing)}"
            )
        unknown = values.keys() - self.required
        if unknown:
            raise KeyError(
                f"Prompt '{self.name}' got unknown placeholders: {sorted(unknown)}"
            )
        return self.template.format(**values)


# The shared persona line every system prompt starts from. One place to edit
# the product's voice.
PERSONA = (
    "You are DataGuardian, an autonomous metadata governance engineer. "
    "You are precise, calm, and useful. You ground every statement in the "
    "evidence provided and never invent assets, owners, numbers, or lineage."
)

from app.llm.prompts import (  # noqa: E402  (re-exports need PERSONA defined)
    documentation,
    governance,
    recommendations,
    reports,
)

__all__ = [
    "PERSONA",
    "PromptTemplate",
    "documentation",
    "governance",
    "recommendations",
    "reports",
]
