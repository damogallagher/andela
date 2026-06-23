from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScanRequest(BaseModel):
    path: str = Field(default="sample_iac", description="Path under the configured local scan root.")
    label: str = Field(default="Manual local scan", max_length=120)


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: str
    title: str
    severity: str
    file_path: str
    line_number: int
    resource: str
    evidence: str
    recommendation: str


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    target_path: str
    risk_score: int
    files_scanned: int
    findings_count: int
    created_at: datetime
    findings: list[FindingResponse] = []


class ScanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    risk_score: int
    findings_count: int
    created_at: datetime


class SeverityDelta(BaseModel):
    severity: str
    base: int
    head: int
    delta: int
    new: int
    resolved: int


class ScanComparisonResponse(BaseModel):
    base_scan: ScanSummary
    head_scan: ScanSummary
    risk_score_delta: int
    findings_count_delta: int
    new_findings_count: int
    resolved_findings_count: int
    severity_deltas: list[SeverityDelta]
    regression_summary: str
    new_findings: list[FindingResponse]
    resolved_findings: list[FindingResponse]
