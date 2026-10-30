"""Tests for job lifecycle API."""

from __future__ import annotations


def test_create_job(client):
    payload = {
        "repo_name": "my-repo",
        "repo_source": "upload",
        "archive_path": "uploads/abc123.zip",
        "bug_description": "The add function returns the wrong result for negative numbers.",
    }
    resp = client.post("/api/v1/jobs", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "queued"
    assert body["repo_name"] == "my-repo"
    assert "id" in body


def test_list_jobs(client):
    # Create a job first
    client.post("/api/v1/jobs", json={
        "repo_name": "list-test",
        "repo_source": "demo",
        "bug_description": "Bug description that is long enough.",
    })
    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_job(client):
    create_resp = client.post("/api/v1/jobs", json={
        "repo_name": "get-test",
        "repo_source": "demo",
        "bug_description": "Some detailed bug report here.",
    })
    job_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


def test_get_nonexistent_job(client):
    resp = client.get("/api/v1/jobs/nonexistent-id-xyz")
    assert resp.status_code == 404


def test_cancel_job(client):
    create_resp = client.post("/api/v1/jobs", json={
        "repo_name": "cancel-test",
        "repo_source": "demo",
        "bug_description": "Test job for cancellation flow.",
    })
    job_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_cancel_already_cancelled(client):
    create_resp = client.post("/api/v1/jobs", json={
        "repo_name": "cancel-twice",
        "repo_source": "demo",
        "bug_description": "Test double-cancel scenario.",
    })
    job_id = create_resp.json()["id"]
    client.post(f"/api/v1/jobs/{job_id}/cancel")
    resp = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code == 409


def test_approve_requires_awaiting_approval(client):
    create_resp = client.post("/api/v1/jobs", json={
        "repo_name": "approve-test",
        "repo_source": "demo",
        "bug_description": "Testing approval gate enforcement.",
    })
    job_id = create_resp.json()["id"]
    resp = client.post(f"/api/v1/jobs/{job_id}/approve", json={"decision": "approved"})
    assert resp.status_code == 409


def test_create_job_invalid_description(client):
    """Bug description must be at least 10 characters."""
    resp = client.post("/api/v1/jobs", json={
        "repo_name": "short",
        "repo_source": "upload",
        "bug_description": "short",
    })
    assert resp.status_code == 422


def test_get_job_events(client):
    create_resp = client.post("/api/v1/jobs", json={
        "repo_name": "events-test",
        "repo_source": "demo",
        "bug_description": "Checking event log endpoint.",
    })
    job_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/jobs/{job_id}/events")
    assert resp.status_code == 200
    assert "events" in resp.json()


def test_download_patch_endpoint(client, db_session):
    from app.services.job_service import JobService
    svc = JobService()
    create_resp = client.post("/api/v1/jobs", json={
        "repo_name": "python_buggy_app",
        "repo_source": "demo",
        "bug_description": "Testing patch download endpoint.",
    })
    job_id = create_resp.json()["id"]
    diff_text = "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1,2 +1,2 @@\n-pass\n+return True"
    svc.set_proposed_patch(db_session, job_id, diff_text)

    resp = client.get(f"/api/v1/jobs/{job_id}/download-patch")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/x-diff")
    assert "attachment;" in resp.headers["content-disposition"]
    assert "calculator" in resp.text


def test_pr_template_endpoint(client, db_session):
    from app.services.job_service import JobService
    svc = JobService()
    create_resp = client.post("/api/v1/jobs", json={
        "repo_name": "fastapi_auth_service",
        "repo_source": "demo",
        "bug_description": "Testing PR template endpoint.",
    })
    job_id = create_resp.json()["id"]
    svc.set_repair_report(db_session, job_id, {
        "job_id": job_id,
        "outcome": "verified",
        "diagnosis_summary": "Inverted token expiration operator",
        "patch_summary": "Fix inverted > comparison in verify_access_token",
        "baseline_test_summary": {"passed": 2, "failed": 2},
        "post_patch_test_summary": {"passed": 4, "failed": 0},
    })
    svc.set_nemotron_critique(db_session, job_id, {
        "verdict": "APPROVED",
        "helpsteer_scores": {"correctness": 5, "coherence": 5, "safety": 5},
        "side_effects_analysis": "No side-effects found.",
        "security_audit": "Clean security profile.",
    })

    resp = client.get(f"/api/v1/jobs/{job_id}/pr-template")
    assert resp.status_code == 200
    data = resp.json()
    assert "title" in data
    assert "body" in data
    assert "PatchPilot" in data["title"]
    assert "NVIDIA" in data["body"]
    assert "Nebius Token Factory" in data["body"]


def test_download_repaired_endpoint(client):
    create_resp = client.post("/api/v1/jobs", json={
        "repo_name": "python_buggy_app",
        "repo_source": "demo",
        "bug_description": "Testing repaired zip download endpoint.",
    })
    job_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/jobs/{job_id}/download-repaired")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "python_buggy_app-repaired.zip" in resp.headers["content-disposition"]


def test_demo_projects_discovery(client):
    resp = client.get("/api/v1/repositories/demos")
    assert resp.status_code == 200
    demos = resp.json().get("demos", [])
    demo_ids = [d["id"] for d in demos]
    assert "python_buggy_app" in demo_ids
    assert "fastapi_auth_service" in demo_ids
    assert "typescript_state_cart" in demo_ids
