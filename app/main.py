from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.migrations import run_migrations
from app.models import Finding, ScanRun
from app.sarif import build_sarif
from app.scanner import (
    RULES,
    SUPPORTED_EXTENSIONS,
    ScanInputFile,
    ScanResult,
    scan_files,
    scan_path,
    severity_rank,
)
from app.schemas import FindingResponse, ScanComparisonResponse, ScanRequest, ScanResponse, ScanSummary, SeverityDelta

SEVERITIES = ("critical", "high", "medium", "low")
UPLOAD_READ_CHUNK_BYTES = 64 * 1024


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_migrations()
    yield


app = FastAPI(
    title="Andela Enterprise Security Guardrail Auditor",
    version="0.1.0",
    description="Local-only API-first IaC security scanner with Postgres-backed scan history.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database health check failed") from exc
    return {"status": "ok", "database": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard() -> FileResponse:
    frontend_index = Path("app/static/frontend/index.html")
    if not frontend_index.exists():
        raise HTTPException(status_code=503, detail="Frontend build is missing. Run npm --prefix frontend run build.")
    return FileResponse(frontend_index)


@app.post("/api/scans/sample", response_model=ScanResponse)
def run_sample_scan(db: Session = Depends(get_db)) -> ScanRun:
    sample_request = ScanRequest(path="sample_iac", label="Sample local IaC scan")
    return _run_scan(sample_request, db)


@app.post("/api/scans", response_model=ScanResponse)
def run_scan(scan_request: ScanRequest, db: Session = Depends(get_db)) -> ScanRun:
    return _run_scan(scan_request, db)


@app.post("/api/scans/upload", response_model=ScanResponse)
async def upload_scan(
    files: list[UploadFile] = File(...),
    label: str = Form("Uploaded file scan"),
    db: Session = Depends(get_db),
) -> ScanRun:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one infrastructure file.")
    if len(files) > settings.upload_max_files:
        file_label = "file" if settings.upload_max_files == 1 else "files"
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Upload at most {settings.upload_max_files} {file_label} per scan.",
        )

    scan_files_input: list[ScanInputFile] = []
    unsupported_files: list[str] = []
    for upload in files:
        filename = Path(upload.filename or "").name
        if not filename:
            raise HTTPException(status_code=400, detail="Every uploaded file must have a filename.")
        if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
            unsupported_files.append(filename)
            continue
        content = await _read_upload_content(upload, filename)
        scan_files_input.append(ScanInputFile(file_path=filename, content=content))

    if unsupported_files:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported upload type for: {', '.join(unsupported_files)}. Supported extensions: {supported}.",
        )
    if not scan_files_input:
        raise HTTPException(status_code=400, detail="Upload at least one supported infrastructure file.")

    target_label = "uploaded: " + ", ".join(scan_file.file_path for scan_file in scan_files_input)
    result = scan_files(scan_files_input, target_label)
    return _persist_scan(label, result, db)


async def _read_upload_content(upload: UploadFile, filename: str) -> str:
    chunks: list[bytes] = []
    bytes_read = 0

    while chunk := await upload.read(UPLOAD_READ_CHUNK_BYTES):
        bytes_read += len(chunk)
        if bytes_read > settings.upload_max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded file '{filename}' exceeds the {settings.upload_max_file_size_bytes} byte limit.",
            )
        chunks.append(chunk)

    return b"".join(chunks).decode("utf-8", errors="ignore")


@app.get("/api/scans", response_model=list[ScanResponse])
def list_scans(db: Session = Depends(get_db)) -> list[ScanRun]:
    return list(
        db.scalars(
            select(ScanRun)
            .options(selectinload(ScanRun.findings))
            .order_by(ScanRun.created_at.desc())
            .limit(20)
        )
    )


@app.get("/api/scans/compare", response_model=ScanComparisonResponse)
def compare_scans(base_scan_id: int, head_scan_id: int, db: Session = Depends(get_db)) -> ScanComparisonResponse:
    if base_scan_id == head_scan_id:
        raise HTTPException(status_code=400, detail="Choose two different scans to compare.")

    base_scan = _get_scan_or_404(base_scan_id, db)
    head_scan = _get_scan_or_404(head_scan_id, db)
    new_findings, resolved_findings = _diff_findings(base_scan.findings, head_scan.findings)
    base_counts = Counter(finding.severity.lower() for finding in base_scan.findings)
    head_counts = Counter(finding.severity.lower() for finding in head_scan.findings)
    new_counts = Counter(finding.severity.lower() for finding in new_findings)
    resolved_counts = Counter(finding.severity.lower() for finding in resolved_findings)

    severity_deltas = [
        SeverityDelta(
            severity=severity,
            base=base_counts.get(severity, 0),
            head=head_counts.get(severity, 0),
            delta=head_counts.get(severity, 0) - base_counts.get(severity, 0),
            new=new_counts.get(severity, 0),
            resolved=resolved_counts.get(severity, 0),
        )
        for severity in SEVERITIES
    ]

    return ScanComparisonResponse(
        base_scan=ScanSummary.model_validate(base_scan),
        head_scan=ScanSummary.model_validate(head_scan),
        risk_score_delta=head_scan.risk_score - base_scan.risk_score,
        findings_count_delta=head_scan.findings_count - base_scan.findings_count,
        new_findings_count=len(new_findings),
        resolved_findings_count=len(resolved_findings),
        severity_deltas=severity_deltas,
        regression_summary=_regression_summary(new_counts, resolved_findings),
        new_findings=[FindingResponse.model_validate(finding) for finding in new_findings],
        resolved_findings=[FindingResponse.model_validate(finding) for finding in resolved_findings],
    )


@app.get("/api/scans/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: int, db: Session = Depends(get_db)) -> ScanRun:
    return _get_scan_or_404(scan_id, db)


@app.get("/api/scans/{scan_id}/sarif")
def get_scan_sarif(scan_id: int, db: Session = Depends(get_db)) -> JSONResponse:
    scan = get_scan(scan_id, db)
    return JSONResponse(content=build_sarif(scan), media_type="application/sarif+json")


@app.get("/api/rules")
def rules() -> list[dict[str, str]]:
    return [
        {
            "rule_id": rule.rule_id,
            "title": rule.title,
            "severity": rule.severity,
            "description": rule.description,
            "recommendation": rule.recommendation,
        }
        for rule in RULES
    ]


def _run_scan(scan_request: ScanRequest, db: Session) -> ScanRun:
    target_path = _resolve_scan_target(scan_request.path)
    try:
        result = scan_path(target_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _persist_scan(scan_request.label, result, db)


def _persist_scan(label: str, result: ScanResult, db: Session) -> ScanRun:
    scan = ScanRun(
        label=label,
        target_path=result.target_path,
        risk_score=result.risk_score,
        files_scanned=result.files_scanned,
        findings_count=len(result.findings),
    )
    scan.findings = [
        Finding(
            rule_id=finding.rule_id,
            title=finding.title,
            severity=finding.severity,
            file_path=finding.file_path,
            line_number=finding.line_number,
            resource=finding.resource,
            evidence=finding.evidence,
            recommendation=finding.recommendation,
        )
        for finding in sorted(result.findings, key=lambda item: (severity_rank(item.severity), item.file_path))
    ]
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return get_scan(scan.id, db)


def _get_scan_or_404(scan_id: int, db: Session) -> ScanRun:
    scan = db.scalar(
        select(ScanRun)
        .options(selectinload(ScanRun.findings))
        .where(ScanRun.id == scan_id)
    )
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


def _diff_findings(base_findings: list[Finding], head_findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
    base_counter = Counter(_finding_identity(finding) for finding in base_findings)
    head_counter = Counter(_finding_identity(finding) for finding in head_findings)

    new_findings = []
    remaining_base = base_counter.copy()
    for finding in head_findings:
        key = _finding_identity(finding)
        if remaining_base.get(key, 0):
            remaining_base[key] -= 1
        else:
            new_findings.append(finding)

    resolved_findings = []
    remaining_head = head_counter.copy()
    for finding in base_findings:
        key = _finding_identity(finding)
        if remaining_head.get(key, 0):
            remaining_head[key] -= 1
        else:
            resolved_findings.append(finding)

    return new_findings, resolved_findings


def _finding_identity(finding: Finding) -> tuple[str, str, str, str, int, str]:
    return (
        finding.rule_id,
        finding.severity,
        finding.title,
        finding.file_path,
        finding.line_number,
        finding.resource,
    )


def _regression_summary(new_counts: Counter, resolved_findings: list[Finding]) -> str:
    new_criticals = new_counts.get("critical", 0)
    new_total = sum(new_counts.values())
    if new_criticals:
        critical_label = "critical" if new_criticals == 1 else "criticals"
        return f"Regression detected: this scan introduced {new_criticals} new {critical_label}."
    if new_total:
        finding_label = "finding" if new_total == 1 else "findings"
        return f"Change detected: this scan introduced {new_total} new {finding_label}, with no new criticals."
    if resolved_findings:
        return "No regression detected: this scan only resolved existing findings."
    return "No finding changes detected."


def _resolve_scan_target(raw_path: str) -> Path:
    scan_root = settings.app_scan_root.resolve()
    requested = Path(raw_path)
    target = requested if requested.is_absolute() else scan_root / requested
    resolved = target.resolve()
    if scan_root not in (resolved, *resolved.parents):
        raise HTTPException(status_code=400, detail="Scan path must stay under APP_SCAN_ROOT.")
    return resolved
