"""Shared base for the DataHub tools.

A "tool" here is a thin, agent-facing wrapper around `DataHubService`. It adds
three things the service deliberately does not have:

* **A name and description.** Tomorrow's agent needs to advertise its
  capabilities to an LLM. Keeping that text next to the call it describes is
  the only way it stays accurate.
* **A JSON-safe serialisation helper.** An LLM cannot consume a Pydantic
  model; it needs plain dicts with ISO-8601 dates.
* **A narrow signature.** Tools take primitives, never model instances, so a
  language model can call them from a JSON argument object.

What tools deliberately do NOT do:

* No LangGraph, no framework binding. These are plain classes. Tomorrow's
  agent adapts them; they do not depend on the agent.
* No error swallowing. Typed DataHub exceptions propagate unchanged, because
  the agent needs to distinguish "retry later" from "this will never work".
* No business logic. Deciding a missing owner is a violation stays in the
  rule engine.
"""

from typing import Any

from pydantic import BaseModel

from app.integrations.datahub import DataHubService


class DataHubTool:
    """Base class for every DataHub-backed tool."""

    #: Stable identifier the agent registers this tool under.
    name: str = "datahub_tool"
    #: Human-readable purpose. Becomes the tool description in an LLM prompt,
    #: so it should say what the tool answers, not how it is implemented.
    description: str = "Base DataHub tool."

    def __init__(self, service: DataHubService) -> None:
        self._service = service

    @property
    def service(self) -> DataHubService:
        """The underlying service, for callers that need the full surface."""
        return self._service

    def describe(self) -> dict[str, str]:
        """Metadata for tool registration."""
        return {"name": self.name, "description": self.description}

    @staticmethod
    def serialize(value: Any) -> Any:
        """Convert models to JSON-safe primitives.

        `mode="json"` matters: it renders datetimes as ISO-8601 strings and
        enums as their values, so the result can go straight into a prompt or
        an HTTP response without a custom encoder.
        """
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [DataHubTool.serialize(item) for item in value]
        if isinstance(value, dict):
            return {k: DataHubTool.serialize(v) for k, v in value.items()}
        return value
