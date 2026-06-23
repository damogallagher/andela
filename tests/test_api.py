import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.migrations import reset_database
from app.scanner import RULES, RULES_BY_ID


@pytest.fixture()
def client() -> TestClient:
    reset_database()
    with TestClient(app) as test_client:
        yield test_client
    reset_database()


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
