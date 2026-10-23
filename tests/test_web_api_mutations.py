"""WO-P1-694 SF-WEB-4 โ€” Command Gateway mutation endpoint tests."""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest

from a_conductor.web_api import create_app, WebApiConfig
from a_conductor.cockpit_projection import (
    CockpitLaneIdentity, CockpitLaneInputs, CockpitObservations, project_cockpit_snapshot,
)

CONFIRM = "test-confirm-nonce-12345"


def projection():
    return project_cockpit_snapshot(CockpitObservations(
        lanes=(CockpitLaneInputs(CockpitLaneIdentity("WO-P1-694", "task-1")),),
        generated_at="2026-10-21T00:00:00+00:00",
    ))


@pytest.fixture
def client():
    app = create_app(projection, WebApiConfig(port=18956, stream_seconds=.15))
    with TestClient(app, base_url="http://127.0.0.1:18956") as c:
        c.headers["Authorization"] = f"Bearer {app.state.feed.token}"
        c.headers["X-Confirm"] = CONFIRM
        yield c


class TestConfirmationRequired:
    def test_no_confirm_header_rejected(self, client):
        client.headers.pop("X-Confirm", None)
        r = client.post("/api/v1/workers/w1/command", json={"action": "start"})
        assert r.status_code == 428

    def test_short_confirm_rejected(self, client):
        client.headers["X-Confirm"] = "abc"
        r = client.post("/api/v1/workers/w1/command", json={"action": "start"})
        assert r.status_code == 428


class TestActionValidation:
    def test_invalid_action_rejected(self, client):
        r = client.post("/api/v1/workers/w1/command", json={"action": "restart"})
        assert r.status_code == 400

    def test_assign_requires_project(self, client):
        r = client.post("/api/v1/workers/w1/command", json={"action": "assign"})
        assert r.status_code == 400


class TestValidMutations:
    def test_start_accepted(self, client):
        r = client.post("/api/v1/workers/w1/command", json={"action": "start"})
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

    def test_assign_with_project_accepted(self, client):
        r = client.post("/api/v1/workers/w1/command",
                        json={"action": "assign", "project": "C:/test"})
        assert r.status_code == 200


class TestRateLimit:
    def test_rapid_mutations_limited(self, client):
        client.post("/api/v1/workers/w1/command", json={"action": "start"})
        r = client.post("/api/v1/workers/w1/command", json={"action": "start"})
        assert r.status_code == 503
        assert r.json()["error"] == "RATE_LIMITED"

    def test_different_worker_not_limited(self, client):
        client.post("/api/v1/workers/w1/command", json={"action": "start"})
        r = client.post("/api/v1/workers/w2/command", json={"action": "start"})
        assert r.status_code == 200


class TestAuditLog:
    def test_mutations_recorded(self, client):
        client.post("/api/v1/workers/w1/command", json={"action": "start"})
        r = client.get("/api/v1/mutations")
        assert r.status_code == 200
        assert len(r.json()["mutations"]) >= 1


class TestAuthRequired:
    def test_no_bearer_rejected(self):
        app = create_app(projection, WebApiConfig(port=18956, stream_seconds=.15))
        with TestClient(app, base_url="http://127.0.0.1:18956") as c:
            r = c.post("/api/v1/workers/w1/command",
                       headers={"X-Confirm": CONFIRM}, json={"action": "start"})
            assert r.status_code in (401, 403)
