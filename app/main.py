from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import Base, engine, get_db
from app.models import Finding, ScanRun
from app.scanner import scan_path, severity_rank
from app.schemas import ScanRequest, ScanResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Andela Enterprise Security Guardrail Auditor",
    version="0.1.0",
    description="Local-only API-first IaC security scanner with Postgres-backed scan history.",
    lifespan=lifespan,
)
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    latest_scan = _latest_scan(db)
    history = db.scalars(select(ScanRun).order_by(ScanRun.created_at.desc()).limit(8)).all()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "latest_scan": latest_scan,
            "history": history,
            "severity_counts": _severity_counts(latest_scan.findings if latest_scan else []),
        },
    )


@app.post("/api/scans/sample", response_model=ScanResponse)
def run_sample_scan(db: Session = Depends(get_db)) -> ScanRun:
    sample_request = ScanRequest(path="sample_iac", label="Sample local IaC scan")
    return _run_scan(sample_request, db)


@app.post("/api/scans", response_model=ScanResponse)
def run_scan(scan_request: ScanRequest, db: Session = Depends(get_db)) -> ScanRun:
    return _run_scan(scan_request, db)


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


@app.get("/api/scans/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: int, db: Session = Depends(get_db)) -> ScanRun:
    scan = db.scalar(
        select(ScanRun)
        .options(selectinload(ScanRun.findings))
        .where(ScanRun.id == scan_id)
    )
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@app.get("/api/rules")
def rules() -> list[dict[str, str]]:
    return [
        {
            "rule_id": "OPEN_SSH_INGRESS",
            "severity": "critical",
            "description": "Detects security group ingress that exposes SSH to 0.0.0.0/0 or ::/0.",
        },
        {
            "rule_id": "S3_PUBLIC_ACL",
            "severity": "high",
            "description": "Detects S3 ACL settings that make buckets publicly readable or writable.",
        },
        {
            "rule_id": "IAM_WILDCARD_POLICY",
            "severity": "high",
            "description": "Detects wildcard IAM action and resource policies.",
        },
        {
            "rule_id": "DATABASE_ENCRYPTION_DISABLED",
            "severity": "medium",
            "description": "Detects database resources with storage encryption disabled.",
        },
    ]


def _run_scan(scan_request: ScanRequest, db: Session) -> ScanRun:
    target_path = _resolve_scan_target(scan_request.path)
    try:
        result = scan_path(target_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scan = ScanRun(
        label=scan_request.label,
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


def _resolve_scan_target(raw_path: str) -> Path:
    scan_root = settings.app_scan_root.resolve()
    requested = Path(raw_path)
    target = requested if requested.is_absolute() else scan_root / requested
    resolved = target.resolve()
    if scan_root not in (resolved, *resolved.parents):
        raise HTTPException(status_code=400, detail="Scan path must stay under APP_SCAN_ROOT.")
    return resolved


def _latest_scan(db: Session) -> Optional[ScanRun]:
    return db.scalar(
        select(ScanRun)
        .options(selectinload(ScanRun.findings))
        .order_by(ScanRun.created_at.desc())
        .limit(1)
    )


def _severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        key = finding.severity.lower()
        counts[key] = counts.get(key, 0) + 1
    return counts
