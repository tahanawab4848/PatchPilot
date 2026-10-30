"""Tests for health endpoints."""

from __future__ import annotations


def test_health_liveness(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_readiness(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "database" in data
    assert data["database"]["ok"] is True
    assert "nebius" in data
    assert "sandbox" in data
