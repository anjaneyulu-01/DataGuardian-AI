# DataHub Integration

Placeholder. Nothing in this folder is configured yet.

This directory will hold everything specific to the DataHub side of the
project, kept separate from application code so it can evolve independently:

- **Ingestion recipes** (`recipes/`) — YAML sources that load sample metadata
  into the local DataHub instance for the demo.
- **MCP server configuration** — connection settings for the DataHub MCP
  server that exposes metadata as agent tools.
- **Agent Context Kit assets** — context packs supplied to the agent.
- **Sample metadata** — a small, reproducible dataset so the demo does not
  depend on a live warehouse.

## Planned local setup

DataHub is run via its own quickstart rather than being inlined into the
project's `docker-compose.yml`, so the two stacks can be started and stopped
independently:

```bash
python -m pip install acryl-datahub
datahub docker quickstart
```

The backend will then reach it at `DATAHUB_GMS_URL` (default
`http://localhost:8080`), authenticating with `DATAHUB_TOKEN`.

> Tracked in the roadmap under **Phase 2 — DataHub Integration**.
