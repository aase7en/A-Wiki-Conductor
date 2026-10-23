"""P2 API contract over the existing app-session connector registry."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from a_conductor.cockpit_projection import CockpitObservations, project_cockpit_snapshot
from a_conductor.system_metrics import SystemMetrics, SystemMetricsSampler
from a_conductor.web_api import WebApiConfig, create_app


@pytest.fixture
def client():
    app = create_app(lambda: project_cockpit_snapshot(CockpitObservations(
        generated_at="2026-10-23T00:00:00+00:00")), WebApiConfig(port=18956))
    with TestClient(app, base_url="http://127.0.0.1:18956") as client:
        client.headers.update({"Authorization": f"Bearer {app.state.feed.token}",
                               "X-Confirm": "p2-confirm-test"})
        yield client


def create_connector(client):
    response = client.post("/api/v1/connectors", json={
        "name": "Original", "project_path": "C:/private", "tunnel_id": "private-tunnel"})
    assert response.status_code == 201, response.text
    return response.json()["connector_id"]


def test_connector_round_trip(client, monkeypatch):
    connector = create_connector(client)
    response = client.patch(f"/api/v1/connectors/{connector}", json={"name": "Renamed"})
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Renamed"
    listing = client.get("/api/v1/connectors")
    assert listing.json() == {"scope": "app-session", "connectors": [
        {"connector_id": connector, "name": "Renamed", "state": "STOPPED"}]}
    assert "private" not in listing.text
    # Both actions share one per-connector mutation window.
    assert client.delete(f"/api/v1/connectors/{connector}").json()["error"] == "RATE_LIMITED"
    import a_conductor.web_api as api
    monotonic = api.time.monotonic
    monkeypatch.setattr(api.time, "monotonic", lambda: monotonic() + 2)
    assert client.delete(f"/api/v1/connectors/{connector}").status_code == 200
    assert client.get("/api/v1/connectors").json()["connectors"] == []
    audit = client.get("/api/v1/mutations").json()["mutations"]
    assert [entry["action"] for entry in audit] == ["create", "rename", "delete"]
    assert all(datetime.fromisoformat(entry["at"]).tzinfo for entry in audit)
    assert listing.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_mutation_requires_auth_and_confirmation(client, method):
    connector = create_connector(client)
    path = f"/api/v1/connectors/{connector}"
    kwargs = {"json": {"name": "Changed"}} if method == "patch" else {}
    client.headers.pop("Authorization")
    assert client.request(method, path, **kwargs).status_code == 401
    client.headers["Authorization"] = f"Bearer {client.app.state.feed.token}"
    client.headers.pop("X-Confirm")
    assert client.request(method, path, **kwargs).status_code == 428
    assert client.get("/api/v1/connectors").json()["connectors"][0]["name"] == "Original"


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_mutation_host_origin_and_missing_connector(client, method):
    kwargs = {"json": {"name": "Changed"}} if method == "patch" else {}
    path = "/api/v1/connectors/missing"
    assert client.request(method, path, headers={"Origin": "https://evil.test"}, **kwargs).status_code == 403
    assert client.request(method, path, headers={"Host": "evil.test"}, **kwargs).status_code == 403
    assert client.request(method, path, **kwargs).status_code == 404


@pytest.mark.parametrize("name", ["", " ", "x" * 129, "bad\nname"])
def test_invalid_rename_preserves_connector(client, name):
    connector = create_connector(client)
    assert client.patch(f"/api/v1/connectors/{connector}", json={"name": name}).status_code == 400
    assert client.get("/api/v1/connectors").json()["connectors"][0]["name"] == "Original"


@pytest.mark.parametrize("state", ["RUNNING", "STARTING", "UNKNOWN", None])
def test_delete_requires_explicit_stopped(client, state):
    connector = create_connector(client)
    # Fault injection at the existing registry seam; no runtime processes involved.
    client.app.state.connectors[connector]["state"] = state
    response = client.delete(f"/api/v1/connectors/{connector}")
    assert response.status_code == 409
    assert response.json()["error"] == "CONNECTOR_NOT_STOPPED"
    assert connector in client.app.state.connectors


def test_client_cannot_supply_stopped_state(client):
    connector = create_connector(client)
    assert client.patch(f"/api/v1/connectors/{connector}", json={
        "name": "Other", "state": "STOPPED"}).status_code == 422


def test_rename_rate_limit_preserves_first_value(client):
    connector = create_connector(client)
    path = f"/api/v1/connectors/{connector}"
    assert client.patch(path, json={"name": "First"}).status_code == 200
    response = client.patch(path, json={"name": "Second"})
    assert response.status_code == 503
    assert response.json()["error"] == "RATE_LIMITED"
    assert client.get("/api/v1/connectors").json()["connectors"][0]["name"] == "First"


def test_metrics_reuses_sampler(client, monkeypatch):
    assert isinstance(client.app.state.metrics_sampler, SystemMetricsSampler)
    monkeypatch.setattr(client.app.state.metrics_sampler, "sample", lambda: SystemMetrics(
        cpu_percent=37.5, memory_used_bytes=1024**3, memory_total_bytes=4 * 1024**3,
        uptime_seconds=10))
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert response.json() == {"cpu_percent": 37.5, "memory_used_bytes": 1024**3,
                               "memory_total_bytes": 4 * 1024**3, "uptime_seconds": 10}
    assert response.headers["cache-control"] == "no-store"


def test_metrics_unavailable_is_not_zero(client, monkeypatch):
    monkeypatch.setattr(client.app.state.metrics_sampler, "sample", lambda: SystemMetrics(
        cpu_percent=None, memory_used_bytes=None, memory_total_bytes=None, uptime_seconds=1))
    assert client.get("/api/v1/metrics").json()["cpu_percent"] is None
    client.headers.pop("Authorization")
    assert client.get("/api/v1/metrics").status_code == 401


def test_patch_is_connector_only(client):
    assert client.patch("/api/v1/workers/worker", json={"name": "x"}).status_code == 405
    assert client.patch("/api/v1/snapshot", json={}).status_code == 405
