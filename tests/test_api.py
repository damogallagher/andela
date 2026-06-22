import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


def test_create_scan_persists_findings_and_history(client: TestClient) -> None:
    response = client.post(
        "/api/scans",
        json={"path": "sample_iac/scenarios/json_only", "label": "JSON-only fixture scan"},
    )

    assert response.status_code == 200
    scan = response.json()
    assert scan["label"] == "JSON-only fixture scan"
    assert scan["risk_score"] == 50
    assert scan["files_scanned"] == 2
    assert scan["findings_count"] == 2
    assert [finding["rule_id"] for finding in scan["findings"]] == [
        "OPEN_SSH_INGRESS",
        "IAM_WILDCARD_POLICY",
    ]

    history_response = client.get("/api/scans")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["id"] == scan["id"]

    detail_response = client.get(f"/api/scans/{scan['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["target_path"].endswith("sample_iac/scenarios/json_only")


def test_sample_scan_endpoint_scans_all_sample_scenarios(client: TestClient) -> None:
    response = client.post("/api/scans/sample")

    assert response.status_code == 200
    scan = response.json()
    assert scan["label"] == "Sample local IaC scan"
    assert scan["files_scanned"] == 8
    assert scan["findings_count"] == 7
    assert scan["risk_score"] == 0


def test_dashboard_renders_latest_scan(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"path": "sample_iac/scenarios/clean", "label": "Clean fixture scan"},
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "Enterprise Security Guardrail Auditor" in response.text
    assert "Clean fixture scan" in response.text
    assert "100" in response.text


def test_rules_endpoint_lists_supported_rules(client: TestClient) -> None:
    response = client.get("/api/rules")

    assert response.status_code == 200
    rule_ids = {rule["rule_id"] for rule in response.json()}
    assert {
        "OPEN_SSH_INGRESS",
        "S3_PUBLIC_ACL",
        "IAM_WILDCARD_POLICY",
        "DATABASE_ENCRYPTION_DISABLED",
    }.issubset(rule_ids)


def test_scan_rejects_paths_outside_scan_root(client: TestClient) -> None:
    response = client.post("/api/scans", json={"path": "/tmp", "label": "Invalid scan"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Scan path must stay under APP_SCAN_ROOT."


def test_missing_scan_path_returns_404(client: TestClient) -> None:
    response = client.post("/api/scans", json={"path": "sample_iac/missing", "label": "Missing"})

    assert response.status_code == 404

