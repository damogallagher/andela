from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import Base, engine, get_db
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
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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

    scan_files_input: list[ScanInputFile] = []
    unsupported_files: list[str] = []
    for upload in files:
        filename = Path(upload.filename or "").name
        if not filename:
            raise HTTPException(status_code=400, detail="Every uploaded file must have a filename.")
        if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
            unsupported_files.append(filename)
            continue
        content = (await upload.read()).decode("utf-8", errors="ignore")
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


def _resolve_scan_target(raw_path: str) -> Path:
    scan_root = settings.app_scan_root.resolve()
    requested = Path(raw_path)
    target = requested if requested.is_absolute() else scan_root / requested
    resolved = target.resolve()
    if scan_root not in (resolved, *resolved.parents):
        raise HTTPException(status_code=400, detail="Scan path must stay under APP_SCAN_ROOT.")
    return resolved
