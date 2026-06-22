from datetime import datetime

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    path: str = Field(default="sample_iac", description="Path under the configured local scan root.")
    label: str = Field(default="Manual local scan", max_length=120)


class FindingResponse(BaseModel):
    id: int
    rule_id: str
    title: str
    severity: str
    file_path: str
    line_number: int
    resource: str
    evidence: str
    recommendation: str

    class Config:
        from_attributes = True


class ScanResponse(BaseModel):
    id: int
    label: str
    target_path: str
    risk_score: int
    files_scanned: int
    findings_count: int
    created_at: datetime
    findings: list[FindingResponse] = []

    class Config:
        from_attributes = True

