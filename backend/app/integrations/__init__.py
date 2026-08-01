"""Adapters for external systems.

One subpackage per upstream (DataHub today; the MCP server and Gemini later).
Each owns its transport, error types, and models, and exposes a single service
class. Nothing here imports FastAPI, so integrations stay usable from the
scheduler and the agent, not just from HTTP handlers.
"""
