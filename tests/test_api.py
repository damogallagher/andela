import logging
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import get_db
from app.main import app
from app.migrations import reset_database
from app.scanner import RULES, RULES_BY_ID


@pytest.fixture()
def client() -> TestClient:
    reset_database()
    with TestClient(app) as test_client:
        yield test_client
    reset_database()


def test_health_checks_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_request_id_header_is_generated_when_missing(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    UUID(response.headers["x-request-id"])


def test_request_id_header_is_preserved_when_provided(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "andela-test-request"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "andela-test-request"


def test_request_logging_includes_structured_request_fields(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="andela.api")

    response = client.get("/health", headers={"X-Request-ID": "andela-log-request"})

    assert response.status_code == 200
    request_logs = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "request_completed"
        and getattr(record, "request_id", None) == "andela-log-request"
    ]
    assert request_logs
    assert request_logs[-1].method == "GET"
    assert request_logs[-1].path == "/health"
    assert request_logs[-1].status_code == 200
    assert request_logs[-1].duration_ms >= 0


def test_cors_allows_vite_dev_server_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()


def test_cors_handles_vite_dev_server_preflight(client: TestClient) -> None:
    response = client.options(
        "/api/scans",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "x-request-id" in response.headers["access-control-allow-headers"].lower()


def test_health_returns_unavailable_when_database_check_fails(client: TestClient) -> None:
    class FailingDatabase:
        def execute(self, _: object) -> None:
            raise SQLAlchemyError("database unavailable")

    def failing_db():
        yield FailingDatabase()

    app.dependency_overrides[get_db] = failing_db
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "Database health check failed"


def test_create_scan_persists_findings_and_history(client: TestClient) -> None:
    response = client.post(
        "/api/scans",
        json={"path": "sample_iac/scenarios/json_only", "label": "JSON-only fixture scan"},
    )

    assert response.status_code == 200
    scan = response.json()
    assert scan["label"] == "JSON-only fixture scan"
    assert scan["risk_score"] == 60
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
    assert scan["files_scanned"] == 10
    assert scan["findings_count"] == 67
    assert scan["risk_score"] == 47


def test_scan_sarif_endpoint_exports_code_scanning_results(client: TestClient) -> None:
    scan_response = client.post(
        "/api/scans",
        json={"path": "sample_iac/scenarios/json_only", "label": "JSON-only fixture scan"},
    )
    scan = scan_response.json()

    response = client.get(f"/api/scans/{scan['id']}/sarif")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/sarif+json")
    sarif = response.json()
    assert sarif["version"] == "2.1.0"
    assert sarif["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"

    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "Andela Enterprise Security Guardrail Auditor"
    assert {rule["id"] for rule in run["tool"]["driver"]["rules"]} == {
        "IAM_WILDCARD_POLICY",
        "OPEN_SSH_INGRESS",
    }
    open_ssh_rule = next(rule for rule in run["tool"]["driver"]["rules"] if rule["id"] == "OPEN_SSH_INGRESS")
    assert open_ssh_rule["fullDescription"]["text"] == RULES_BY_ID["OPEN_SSH_INGRESS"].description
    assert open_ssh_rule["help"]["text"] == RULES_BY_ID["OPEN_SSH_INGRESS"].recommendation
    assert run["invocations"][0]["executionSuccessful"] is True
    assert run["invocations"][0]["properties"]["scanId"] == scan["id"]

    results = run["results"]
    assert len(results) == 2
    assert {result["ruleId"] for result in results} == {"IAM_WILDCARD_POLICY", "OPEN_SSH_INGRESS"}
    assert {result["level"] for result in results} == {"error"}
    for result in results:
        location = result["locations"][0]["physicalLocation"]
        assert location["artifactLocation"]["uri"].startswith("sample_iac/scenarios/json_only/")
        assert location["region"]["startLine"] > 0
        assert result["partialFingerprints"]["primaryLocationLineHash"]


def test_compare_scans_reports_new_and_resolved_findings(client: TestClient) -> None:
    base_response = client.post(
        "/api/scans/upload",
        data={"label": "Base PR scan"},
        files=[
            (
                "files",
                (
                    "main.tf",
                    'resource "aws_s3_bucket" "reports" {\n'
                    '  bucket = "andela-pr-reports"\n'
                    '  acl    = "public-read"\n'
                    "}\n",
                    "text/plain",
                ),
            )
        ],
    )
    head_response = client.post(
        "/api/scans/upload",
        data={"label": "Head PR scan"},
        files=[
            (
                "files",
                (
                    "main.tf",
                    'resource "aws_s3_bucket" "reports" {\n'
                    '  bucket = "andela-pr-reports"\n'
                    '  acl    = "public-read"\n'
                    "}\n"
                    '\nresource "null_resource" "credentials" {\n'
                    '  triggers = {\n'
                    '    api_token = "example-token-01"\n'
                    '    client_secret = "example-client-secret-02"\n'
                    "  }\n"
                    "}\n",
                    "text/plain",
                ),
            )
        ],
    )

    base_scan = base_response.json()
    head_scan = head_response.json()

    response = client.get(
        "/api/scans/compare",
        params={"base_scan_id": base_scan["id"], "head_scan_id": head_scan["id"]},
    )

    assert response.status_code == 200
    comparison = response.json()
    assert comparison["base_scan"]["label"] == "Base PR scan"
    assert comparison["head_scan"]["label"] == "Head PR scan"
    assert comparison["new_findings_count"] == 2
    assert comparison["resolved_findings_count"] == 0
    assert comparison["regression_summary"] == "Regression detected: this scan introduced 2 new criticals."
    critical_delta = next(delta for delta in comparison["severity_deltas"] if delta["severity"] == "critical")
    assert critical_delta["base"] == 0
    assert critical_delta["head"] == 2
    assert critical_delta["new"] == 2
    assert {finding["rule_id"] for finding in comparison["new_findings"]} == {"HARDCODED_SECRET"}


def test_compare_scans_requires_two_existing_scans(client: TestClient) -> None:
    response = client.get("/api/scans/compare", params={"base_scan_id": 1, "head_scan_id": 1})

    assert response.status_code == 400
    assert response.json()["detail"] == "Choose two different scans to compare."

    missing_response = client.get("/api/scans/compare", params={"base_scan_id": 1, "head_scan_id": 2})
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Scan not found"


def test_dashboard_renders_latest_scan(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"path": "sample_iac/scenarios/json_only", "label": "JSON-only fixture scan"},
    )

    response = client.get("/")

    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text
    assert "/static/frontend/assets/" in response.text


def test_upload_scan_accepts_multiple_files_and_persists_results(client: TestClient) -> None:
    aws_access_key = "AKIA" + ("1" * 16)
    terraform_content = (
        'resource "aws_s3_bucket" "reports" {\n'
        '  bucket = "andela-upload-demo"\n'
        '  acl    = "public-read"\n'
        '}\n'
        '\nresource "null_resource" "credentials" {\n'
        '  triggers = {\n'
        f'    access_key = "{aws_access_key}"\n'
        '  }\n'
        '}\n'
    )
    json_content = """
{
  "Resources": {
    "AdminSecurityGroup": {
      "Type": "AWS::EC2::SecurityGroup",
      "Properties": {
        "SecurityGroupIngress": [
          {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "CidrIp": "0.0.0.0/0"
          }
        ]
      }
    }
  }
}
"""

    response = client.post(
        "/api/scans/upload",
        data={"label": "Uploaded fixture scan"},
        files=[
            ("files", ("uploaded_bucket.tf", terraform_content, "text/plain")),
            ("files", ("uploaded_security.json", json_content, "application/json")),
        ],
    )

    assert response.status_code == 200
    scan = response.json()
    assert scan["label"] == "Uploaded fixture scan"
    assert scan["target_path"] == "uploaded: uploaded_bucket.tf, uploaded_security.json"
    assert scan["files_scanned"] == 2
    assert scan["findings_count"] == 3
    assert scan["risk_score"] == 52
    assert [finding["rule_id"] for finding in scan["findings"]] == [
        "HARDCODED_SECRET",
        "OPEN_SSH_INGRESS",
        "S3_PUBLIC_ACL",
    ]
    assert all(aws_access_key not in finding["evidence"] for finding in scan["findings"])

    history_response = client.get("/api/scans")
    assert history_response.status_code == 200
    assert history_response.json()[0]["label"] == "Uploaded fixture scan"


def test_upload_scan_rejects_unsupported_file_types(client: TestClient) -> None:
    response = client.post(
        "/api/scans/upload",
        data={"label": "Unsupported upload"},
        files=[("files", ("notes.txt", "not infrastructure", "text/plain"))],
    )

    assert response.status_code == 400
    assert "Unsupported upload type" in response.json()["detail"]


def test_upload_scan_rejects_too_many_files(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "upload_max_files", 1)

    response = client.post(
        "/api/scans/upload",
        data={"label": "Too many files"},
        files=[
            ("files", ("one.tf", 'resource "null_resource" "one" {}\n', "text/plain")),
            ("files", ("two.tf", 'resource "null_resource" "two" {}\n', "text/plain")),
        ],
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Upload at most 1 file per scan."
    assert client.get("/api/scans").json() == []


def test_upload_scan_rejects_oversized_file(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "upload_max_file_size_bytes", 8)

    response = client.post(
        "/api/scans/upload",
        data={"label": "Oversized file"},
        files=[("files", ("oversized.tf", "012345678", "text/plain"))],
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Uploaded file 'oversized.tf' exceeds the 8 byte limit."
    assert client.get("/api/scans").json() == []


def test_rules_endpoint_lists_supported_rules(client: TestClient) -> None:
    response = client.get("/api/rules")

    assert response.status_code == 200
    assert response.json() == [
        {
            "rule_id": rule.rule_id,
            "title": rule.title,
            "severity": rule.severity,
            "description": rule.description,
            "recommendation": rule.recommendation,
        }
        for rule in RULES
    ]


def test_scan_rejects_paths_outside_scan_root(client: TestClient) -> None:
    response = client.post("/api/scans", json={"path": "/tmp", "label": "Invalid scan"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Scan path must stay under APP_SCAN_ROOT."


def test_missing_scan_path_returns_404(client: TestClient) -> None:
    response = client.post("/api/scans", json={"path": "sample_iac/missing", "label": "Missing"})

    assert response.status_code == 404


def test_missing_scan_sarif_returns_404(client: TestClient) -> None:
    response = client.get("/api/scans/999/sarif")

    assert response.status_code == 404
    assert response.json()["detail"] == "Scan not found"
