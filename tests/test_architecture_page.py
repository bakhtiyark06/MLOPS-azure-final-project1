# Author: Presentation layer tests
# Purpose: Verify /demo and /demo/flow routes render without changing API behavior

"""Tests for interactive architecture dashboard pages."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client() -> TestClient:
    from src.api.main import create_app

    return TestClient(create_app())


def test_demo_hub_returns_200_with_flow_link(client: TestClient) -> None:
    response = client.get("/demo")
    assert response.status_code == 200
    body = response.text
    assert "Demo Hub" in body
    assert "/demo/flow" in body


def test_demo_flow_returns_200_with_controls(client: TestClient) -> None:
    response = client.get("/demo/flow")
    assert response.status_code == 200
    body = response.text
    assert "Full System Architecture" in body
    assert "Live Flow" in body
    assert "stage-tabs" in body
    assert "arch-sections" in body
    assert "arch-timeline" in body
    assert "arch-edges" in body
    assert 'id="btn-live-flow"' in body
    assert 'id="btn-pause"' in body
    assert 'id="btn-reset"' in body
    assert 'id="btn-prev"' in body
    assert 'id="btn-next"' in body
    assert "architecture.js" in body


def test_demo_flow_includes_rubric_labels_in_json(client: TestClient) -> None:
    json_response = client.get("/static/architecture-nodes.json")
    assert json_response.status_code == 200
    data = json_response.json()
    labels = {n["label"] for n in data["nodes"]}
    assert "Quality Gate" in labels
    assert "Azure ML Registry" in labels
    assert "OpenRouter API" in labels or "OpenRouter" in str(data)


def test_demo_flow_page_has_eight_infrastructure_sections(client: TestClient) -> None:
    json_response = client.get("/static/architecture-nodes.json")
    data = json_response.json()
    sections = data["sections"]
    assert len(sections) == 8
    section_labels = {s["label"] for s in sections}
    assert "USER" in section_labels
    assert "WEBSITE MONITORING" in section_labels
    assert "ML PIPELINE" in section_labels
    assert "CI/CD" in section_labels
    assert "SERVING" in section_labels
    assert "MONITORING" in section_labels
    assert "AI REPORTING" in section_labels


def test_timeline_flow_has_fourteen_steps(client: TestClient) -> None:
    json_response = client.get("/static/architecture-nodes.json")
    data = json_response.json()
    timeline = data["timelineFlow"]
    assert len(timeline) == 14
    assert timeline[0]["label"] == "User"
    assert timeline[-1]["label"] == "OpenRouter"
    assert all("nodeId" in step for step in timeline)


def test_edges_include_typed_connections(client: TestClient) -> None:
    json_response = client.get("/static/architecture-nodes.json")
    data = json_response.json()
    edge_types = {e["type"] for e in data["edges"]}
    assert "data" in edge_types
    assert "deploy" in edge_types
    assert "monitor" in edge_types


def test_architecture_css_has_reduced_motion_rule(client: TestClient) -> None:
    css_response = client.get("/static/architecture.css")
    assert css_response.status_code == 200
    css = css_response.text
    assert "prefers-reduced-motion" in css
    assert "reduced-motion" in css


def test_health_and_dashboard_unchanged(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert "status" in health.json()

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "system-status" in dashboard.text or "Pipeline" in dashboard.text
