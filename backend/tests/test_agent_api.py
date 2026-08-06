"""Agent endpoint tests.

Drive the real FastAPI app over HTTP with the agent's dependencies overridden
by doubles, so routing, validation, DI, and response serialisation are all
exercised.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.agents import GovernanceAgent, Planner
from app.api.deps import get_governance_agent
from app.integrations.datahub import DataHubEntityNotFoundError
from app.llm.exceptions import LLMTimeoutError
from tests.agent_doubles import StubLLM, make_dataset, make_toolkit


@contextmanager
def api(**toolkit_kwargs) -> Iterator[TestClient]:
    """App with the agent replaced by one wired to doubles."""
    from app.main import app

    llm = toolkit_kwargs.pop("llm", None) or StubLLM()
    agent = GovernanceAgent(
        toolkit=make_toolkit(**toolkit_kwargs),
        llm=llm,
        planner=Planner(llm=None),
    )
    app.dependency_overrides[get_governance_agent] = lambda: agent
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


class TestAnalyzeEndpoint:
    def test_returns_the_documented_json_contract(self) -> None:
        with api(datasets=[make_dataset(owned=False, documented=False)]) as client:
            response = client.post(
                "/api/v1/agent/analyze",
                json={"question": "Find datasets without owners."},
            )

        assert response.status_code == 200
        body = response.json()
        for key in (
            "summary",
            "risk_level",
            "risk_score",
            "findings",
            "recommendations",
            "evidence",
        ):
            assert key in body

        assert body["risk_score"] > 0
        assert body["intent"] == "find_missing_owners"
        assert any(f["rule"] == "missing_owner" for f in body["findings"])

    def test_response_includes_the_execution_trace(self) -> None:
        # The trace is what makes a multi-step agent auditable from the UI.
        with api(datasets=[make_dataset(owned=False)]) as client:
            body = client.post(
                "/api/v1/agent/analyze",
                json={"question": "Find datasets without owners."},
            ).json()

        assert body["trace"]
        assert body["trace"][0]["node"] == "planner"
        assert all("duration_ms" in entry for entry in body["trace"])
        assert "planner" in body["tools_used"]

    @pytest.mark.parametrize(
        "payload",
        [{}, {"question": ""}, {"question": "ab"}, {"wrong_key": "hello"}],
    )
    def test_invalid_input_is_rejected_with_422(self, payload: dict) -> None:
        with api() as client:
            assert client.post("/api/v1/agent/analyze", json=payload).status_code == 422

    def test_degraded_run_is_200_not_5xx(self) -> None:
        # A partial answer is a result, not a transport failure. The caller
        # reads `degraded`; reserving non-2xx for real request problems keeps
        # the contract honest.
        with api(dataset_error=DataHubEntityNotFoundError("gone")) as client:
            response = client.post(
                "/api/v1/agent/analyze",
                json={"question": "Find datasets without owners."},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["degraded"] is True
        assert body["errors"]

    def test_llm_outage_still_returns_findings(self) -> None:
        with api(
            datasets=[make_dataset(owned=False)],
            llm=StubLLM(error=LLMTimeoutError("providers down")),
        ) as client:
            body = client.post(
                "/api/v1/agent/analyze",
                json={"question": "Find datasets without owners."},
            ).json()

        assert body["degraded"] is True
        # Deterministic parts survive because they never needed the LLM.
        assert body["risk_score"] > 0
        assert body["findings"]

    def test_endpoint_is_documented_in_openapi(self) -> None:
        with api() as client:
            schema = client.get("/openapi.json").json()

        assert "/api/v1/agent/analyze" in schema["paths"]
        assert "post" in schema["paths"]["/api/v1/agent/analyze"]
