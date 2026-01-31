"""IAMSentry Dashboard Server.

FastAPI-based web dashboard for visualizing IAM recommendations,
risk scores, and remediation status.
"""

import asyncio
import json
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from IAMSentry.constants import VERSION
from IAMSentry.dashboard.auth import (
    get_auth_config,
    verify_authentication,
    get_current_user,
    _parse_basic_auth_header,
)
from IAMSentry.audit import (
    get_audit_logger,
    AuditEvent,
    log_auth,
    log_scan,
    log_iam_change,
    log_event,
)

# Get allowed origins from environment variable (comma-separated)
# Default allows localhost for development; override in production
CORS_ORIGINS = os.environ.get(
    "IAMSENTRY_CORS_ORIGINS",
    "http://localhost:8080,http://localhost:3000,http://127.0.0.1:8080"
).split(",")

# Rate limiting settings (configurable via environment)
RATE_LIMIT_REQUESTS = int(os.environ.get("IAMSENTRY_RATE_LIMIT", "100"))  # requests per window
RATE_LIMIT_WINDOW = int(os.environ.get("IAMSENTRY_RATE_WINDOW", "60"))  # seconds

# Rate limiting storage
_rate_limit_data: Dict[str, List[float]] = defaultdict(list)

# Create FastAPI app
app = FastAPI(
    title="IAMSentry Dashboard",
    description="Web dashboard for GCP IAM security auditing and remediation",
    version=VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware with configurable origins
# Note: When allow_credentials=True, we must specify explicit headers (not "*")
# to prevent security vulnerabilities with credentialed requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Requested-With"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Authentication middleware.

    Checks API key or Basic Auth credentials before processing requests.
    Skips authentication for public endpoints (/, /health, /api/docs).
    """
    # Skip auth for certain paths
    skip_paths = {"/", "/health", "/api/health", "/api/docs", "/api/redoc", "/openapi.json"}
    if request.url.path in skip_paths:
        return await call_next(request)

    config = get_auth_config()
    client_ip = request.client.host if request.client else "unknown"

    # If auth is disabled, proceed
    if not config.enabled:
        request.state.user = "anonymous"
        return await call_next(request)

    # Try to authenticate
    api_key = request.headers.get("X-API-Key")
    auth_header = request.headers.get("Authorization", "")

    user = None

    # Try API Key
    if api_key and config.verify_api_key(api_key):
        import hashlib
        key_id = hashlib.sha256(api_key.encode()).hexdigest()[:12]
        user = f"api_key:{key_id}"

    # Try Basic Auth
    if not user and auth_header.startswith("Basic "):
        parsed = _parse_basic_auth_header(auth_header)
        if parsed:
            username, password = parsed
            if config.verify_basic_auth(username, password):
                user = f"user:{username}"

    if user:
        request.state.user = user
        # Log successful auth (only for non-GET requests to reduce noise)
        if request.method != "GET":
            log_auth(
                success=True,
                username=user,
                client_ip=client_ip,
                user_agent=request.headers.get("User-Agent"),
            )
        return await call_next(request)

    # Authentication failed
    log_auth(
        success=False,
        username="unknown",
        client_ip=client_ip,
        user_agent=request.headers.get("User-Agent"),
        reason="Invalid or missing credentials",
    )

    return JSONResponse(
        status_code=401,
        content={"detail": "Authentication required"},
        headers={"WWW-Authenticate": 'Basic realm="IAMSentry Dashboard"'},
    )


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting middleware.

    Limits requests per IP address within a sliding window.
    Configure via IAMSENTRY_RATE_LIMIT and IAMSENTRY_RATE_WINDOW env vars.
    """
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()

    # Clean old entries outside the window
    _rate_limit_data[client_ip] = [
        t for t in _rate_limit_data[client_ip]
        if current_time - t < RATE_LIMIT_WINDOW
    ]

    # Check rate limit
    if len(_rate_limit_data[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later."}
        )

    # Record this request
    _rate_limit_data[client_ip].append(current_time)

    return await call_next(request)


# Data directory for storing results
DATA_DIR = Path(os.environ.get("IAMSENTRY_DATA_DIR", "./output"))

# In-memory cache for scan results
_scan_cache: Dict[str, Any] = {}
_scan_status: Dict[str, str] = {}


# --- Pydantic Models ---

class ScanRequest(BaseModel):
    """Request to start a new scan."""
    projects: List[str] = ["*"]
    dry_run: bool = True


class ScanStatus(BaseModel):
    """Status of a scan job."""
    id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    projects: List[str] = []
    recommendation_count: int = 0
    error: Optional[str] = None


class Recommendation(BaseModel):
    """IAM recommendation summary."""
    id: str
    project: str
    account_id: str
    account_type: str
    current_role: str
    recommended_action: str
    risk_score: int
    waste_percentage: int
    safe_to_apply_score: int
    priority: str
    state: str


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_recommendations: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    service_accounts: int
    users: int
    groups: int
    projects_scanned: int
    last_scan: Optional[str] = None


class RemediationRequest(BaseModel):
    """Request to remediate a recommendation."""
    recommendation_id: str
    dry_run: bool = True


class RemediationResult(BaseModel):
    """Result of a remediation action."""
    recommendation_id: str
    status: str
    action: str
    details: Dict[str, Any] = {}


# --- API Routes ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard HTML."""
    return get_dashboard_html()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/stats", response_model=DashboardStats)
async def get_stats():
    """Get dashboard statistics."""
    recommendations = await load_recommendations()

    high_risk = sum(1 for r in recommendations if r.get('score', {}).get('risk_score', 0) >= 70)
    medium_risk = sum(1 for r in recommendations if 40 <= r.get('score', {}).get('risk_score', 0) < 70)
    low_risk = sum(1 for r in recommendations if r.get('score', {}).get('risk_score', 0) < 40)

    account_types = {}
    projects = set()
    for r in recommendations:
        proc = r.get('processor', {})
        account_types[proc.get('account_type', 'unknown')] = \
            account_types.get(proc.get('account_type', 'unknown'), 0) + 1
        projects.add(proc.get('project', 'unknown'))

    # Get last scan time
    last_scan = None
    result_files = list(DATA_DIR.glob("*.json"))
    if result_files:
        latest = max(result_files, key=lambda f: f.stat().st_mtime)
        last_scan = datetime.fromtimestamp(latest.stat().st_mtime).isoformat()

    return DashboardStats(
        total_recommendations=len(recommendations),
        high_risk_count=high_risk,
        medium_risk_count=medium_risk,
        low_risk_count=low_risk,
        service_accounts=account_types.get('serviceAccount', 0),
        users=account_types.get('user', 0),
        groups=account_types.get('group', 0),
        projects_scanned=len(projects),
        last_scan=last_scan,
    )


@app.get("/api/recommendations", response_model=List[Recommendation])
async def get_recommendations(
    project: Optional[str] = Query(None, description="Filter by project"),
    account_type: Optional[str] = Query(None, description="Filter by account type"),
    min_risk: int = Query(0, description="Minimum risk score"),
    limit: int = Query(100, description="Maximum results"),
    offset: int = Query(0, description="Results offset"),
):
    """Get IAM recommendations with filtering."""
    all_recommendations = await load_recommendations()

    # Apply filters
    filtered = []
    for r in all_recommendations:
        proc = r.get('processor', {})
        score = r.get('score', {})
        raw = r.get('raw', {})

        # Project filter
        if project and proc.get('project') != project:
            continue

        # Account type filter
        if account_type and proc.get('account_type') != account_type:
            continue

        # Risk score filter
        if score.get('risk_score', 0) < min_risk:
            continue

        filtered.append(Recommendation(
            id=raw.get('name', '').split('/')[-1] if raw.get('name') else 'unknown',
            project=proc.get('project', 'unknown'),
            account_id=proc.get('account_id', 'unknown'),
            account_type=proc.get('account_type', 'unknown'),
            current_role=_extract_role(raw),
            recommended_action=proc.get('recommendation_recommender_subtype', 'unknown'),
            risk_score=score.get('risk_score', 0),
            waste_percentage=score.get('over_privilege_score', 0),
            safe_to_apply_score=score.get('safe_to_apply_recommendation_score', 0),
            priority=raw.get('priority', 'P4'),
            state=raw.get('stateInfo', {}).get('state', 'ACTIVE'),
        ))

    # Sort by risk score descending
    filtered.sort(key=lambda x: x.risk_score, reverse=True)

    # Apply pagination
    return filtered[offset:offset + limit]


@app.get("/api/recommendations/{recommendation_id}")
async def get_recommendation(recommendation_id: str):
    """Get a specific recommendation by ID."""
    recommendations = await load_recommendations()

    for r in recommendations:
        raw = r.get('raw', {})
        rec_id = raw.get('name', '').split('/')[-1] if raw.get('name') else None
        if rec_id == recommendation_id:
            return r

    raise HTTPException(status_code=404, detail="Recommendation not found")


@app.get("/api/projects")
async def get_projects():
    """Get list of projects with recommendation counts."""
    recommendations = await load_recommendations()

    projects = {}
    for r in recommendations:
        project = r.get('processor', {}).get('project', 'unknown')
        if project not in projects:
            projects[project] = {
                'name': project,
                'recommendation_count': 0,
                'high_risk_count': 0,
            }
        projects[project]['recommendation_count'] += 1
        if r.get('score', {}).get('risk_score', 0) >= 70:
            projects[project]['high_risk_count'] += 1

    return list(projects.values())


@app.post("/api/scan", response_model=ScanStatus)
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks, req: Request):
    """Start a new IAM scan."""
    scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Get user from request state (set by auth middleware)
    user = getattr(req.state, "user", "anonymous")
    client_ip = req.client.host if req.client else "unknown"

    _scan_status[scan_id] = "running"

    # Audit log: scan start
    log_scan(
        projects=request.projects,
        actor=user,
        start=True,
        request_id=scan_id,
    )

    background_tasks.add_task(run_scan, scan_id, request.projects, request.dry_run, user)

    return ScanStatus(
        id=scan_id,
        status="running",
        started_at=datetime.utcnow().isoformat(),
        projects=request.projects,
    )


@app.get("/api/scan/{scan_id}", response_model=ScanStatus)
async def get_scan_status(scan_id: str):
    """Get status of a scan job."""
    if scan_id not in _scan_status:
        raise HTTPException(status_code=404, detail="Scan not found")

    cached = _scan_cache.get(scan_id, {})

    return ScanStatus(
        id=scan_id,
        status=_scan_status.get(scan_id, "unknown"),
        started_at=cached.get('started_at'),
        completed_at=cached.get('completed_at'),
        projects=cached.get('projects', []),
        recommendation_count=cached.get('recommendation_count', 0),
        error=cached.get('error'),
    )


@app.post("/api/remediate", response_model=RemediationResult)
async def remediate(request: RemediationRequest, req: Request):
    """Remediate a specific recommendation."""
    recommendations = await load_recommendations()

    # Get user from request state (set by auth middleware)
    user = getattr(req.state, "user", "anonymous")
    client_ip = req.client.host if req.client else "unknown"

    # Find the recommendation
    target = None
    for r in recommendations:
        raw = r.get('raw', {})
        rec_id = raw.get('name', '').split('/')[-1] if raw.get('name') else None
        if rec_id == request.recommendation_id:
            target = r
            break

    if not target:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # Extract info for audit logging
    processor_info = target.get('processor', {})
    project = processor_info.get('project', 'unknown')
    account_id = processor_info.get('account_id', 'unknown')
    action = processor_info.get('recommendation_recommender_subtype', 'unknown')
    role = _extract_role(target.get('raw', {}))

    # Import remediation processor
    try:
        from IAMSentry.plugins.gcp.gcpiam_remediation import GCPIAMRemediationProcessor

        processor = GCPIAMRemediationProcessor(
            mode_remediate=True,
            dry_run=request.dry_run,
        )

        result = None
        for processed in processor.eval(target):
            result = processed.get('remediation', {})
            break

        if result:
            status = result.get('execution_result', {}).get('status', 'unknown')

            # Audit log: IAM change
            log_iam_change(
                project=project,
                account_id=account_id,
                action=action,
                role=role,
                actor=user,
                recommendation_id=request.recommendation_id,
                before_policy=result.get('before_policy'),
                after_policy=result.get('after_policy'),
                success=(status == 'success' or request.dry_run),
                request_id=request.recommendation_id,
                client_ip=client_ip,
            )

            return RemediationResult(
                recommendation_id=request.recommendation_id,
                status=status,
                action=result.get('recommended_action', 'unknown'),
                details=result.get('execution_result', {}),
            )
        else:
            # Audit log: no action taken
            log_event(
                event_type=AuditEvent.IAM_CHANGE_REJECTED,
                action="NO_ACTION",
                resource=f"projects/{project}",
                actor=user,
                details={
                    "recommendation_id": request.recommendation_id,
                    "account_id": account_id,
                    "reason": "No remediation action taken",
                    "dry_run": request.dry_run,
                },
                request_id=request.recommendation_id,
                client_ip=client_ip,
            )

            return RemediationResult(
                recommendation_id=request.recommendation_id,
                status="no_action",
                action="none",
                details={"message": "No remediation action taken"},
            )

    except Exception as e:
        # Audit log: remediation failed
        log_iam_change(
            project=project,
            account_id=account_id,
            action=action,
            role=role,
            actor=user,
            recommendation_id=request.recommendation_id,
            success=False,
            error=str(e),
            request_id=request.recommendation_id,
            client_ip=client_ip,
        )

        return RemediationResult(
            recommendation_id=request.recommendation_id,
            status="error",
            action="none",
            details={"error": str(e)},
        )


@app.get("/api/auth/status")
async def get_auth_status():
    """Get current authentication status."""
    try:
        from IAMSentry.plugins.gcp import util_gcp
        credentials, project_id = util_gcp.get_credentials()

        auth_type = "Application Default Credentials"
        email = None
        if hasattr(credentials, 'service_account_email'):
            auth_type = "Service Account"
            email = credentials.service_account_email

        return {
            "authenticated": True,
            "auth_type": auth_type,
            "default_project": project_id,
            "service_account": email,
        }

    except Exception as e:
        return {
            "authenticated": False,
            "error": str(e),
        }


# --- Helper Functions ---

async def load_recommendations() -> List[Dict]:
    """Load recommendations from result files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_recs = []
    for file_path in DATA_DIR.glob("*.json"):
        try:
            with open(file_path) as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_recs.extend(data)
                elif isinstance(data, dict):
                    all_recs.append(data)
        except Exception:
            continue

    return all_recs


async def run_scan(scan_id: str, projects: List[str], dry_run: bool, actor: str = "anonymous"):
    """Run a scan in the background."""
    _scan_cache[scan_id] = {
        'started_at': datetime.utcnow().isoformat(),
        'projects': projects,
    }

    try:
        from IAMSentry.plugins.gcp.gcpcloud import GCPCloudIAMRecommendations
        from IAMSentry.plugins.gcp.gcpcloudiam import GCPIAMRecommendationProcessor

        results = []

        # Create reader
        reader = GCPCloudIAMRecommendations(projects=projects)

        # Process recommendations
        processor = GCPIAMRecommendationProcessor(mode_scan=True, mode_enforce=False)

        for record in reader.read():
            for processed in processor.eval(record):
                results.append(processed)

        # Save results
        output_file = DATA_DIR / f"{scan_id}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        _scan_cache[scan_id]['completed_at'] = datetime.utcnow().isoformat()
        _scan_cache[scan_id]['recommendation_count'] = len(results)
        _scan_status[scan_id] = "completed"

        # Audit log: scan complete
        log_scan(
            projects=projects,
            actor=actor,
            recommendation_count=len(results),
            start=False,
            request_id=scan_id,
        )

    except Exception as e:
        _scan_cache[scan_id]['error'] = str(e)
        _scan_status[scan_id] = "failed"

        # Audit log: scan failed
        log_event(
            event_type=AuditEvent.SYSTEM_ERROR,
            action="SCAN_FAILED",
            resource=f"scan/{scan_id}",
            actor=actor,
            details={"error": str(e), "projects": projects},
            request_id=scan_id,
        )


def _extract_role(raw: dict) -> str:
    """Extract role from recommendation."""
    try:
        ops = raw.get('content', {}).get('operationGroups', [{}])[0].get('operations', [])
        for op in ops:
            if op.get('action') == 'remove':
                return op.get('pathFilters', {}).get('/iamPolicy/bindings/*/role', 'N/A')
    except Exception:
        pass
    return 'N/A'


def get_dashboard_html() -> str:
    """Return the dashboard HTML."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IAMSentry Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div id="app">
        <!-- Header -->
        <header class="gradient-bg text-white shadow-lg">
            <div class="container mx-auto px-6 py-4">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-3">
                        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
                        </svg>
                        <h1 class="text-2xl font-bold">IAMSentry Dashboard</h1>
                    </div>
                    <div class="flex items-center space-x-4">
                        <span v-if="authStatus.authenticated" class="flex items-center text-sm">
                            <span class="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                            {{ authStatus.default_project || 'Connected' }}
                        </span>
                        <span v-else class="flex items-center text-sm text-red-200">
                            <span class="w-2 h-2 bg-red-400 rounded-full mr-2"></span>
                            Not Authenticated
                        </span>
                        <button @click="startScan" :disabled="scanning"
                            class="bg-white text-purple-600 px-4 py-2 rounded-lg font-medium hover:bg-gray-100 disabled:opacity-50">
                            {{ scanning ? 'Scanning...' : 'New Scan' }}
                        </button>
                    </div>
                </div>
            </div>
        </header>

        <!-- Stats Cards -->
        <div class="container mx-auto px-6 -mt-8">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div class="bg-white rounded-xl shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-gray-500 text-sm">Total Recommendations</p>
                            <p class="text-3xl font-bold text-gray-800">{{ stats.total_recommendations }}</p>
                        </div>
                        <div class="bg-blue-100 p-3 rounded-lg">
                            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                            </svg>
                        </div>
                    </div>
                </div>

                <div class="bg-white rounded-xl shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-gray-500 text-sm">High Risk</p>
                            <p class="text-3xl font-bold text-red-600">{{ stats.high_risk_count }}</p>
                        </div>
                        <div class="bg-red-100 p-3 rounded-lg">
                            <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                            </svg>
                        </div>
                    </div>
                </div>

                <div class="bg-white rounded-xl shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-gray-500 text-sm">Service Accounts</p>
                            <p class="text-3xl font-bold text-gray-800">{{ stats.service_accounts }}</p>
                        </div>
                        <div class="bg-purple-100 p-3 rounded-lg">
                            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                            </svg>
                        </div>
                    </div>
                </div>

                <div class="bg-white rounded-xl shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-gray-500 text-sm">Projects Scanned</p>
                            <p class="text-3xl font-bold text-gray-800">{{ stats.projects_scanned }}</p>
                        </div>
                        <div class="bg-green-100 p-3 rounded-lg">
                            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"></path>
                            </svg>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="container mx-auto px-6 py-8">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Recommendations Table -->
                <div class="lg:col-span-2">
                    <div class="bg-white rounded-xl shadow-md">
                        <div class="p-6 border-b border-gray-200">
                            <div class="flex items-center justify-between">
                                <h2 class="text-xl font-semibold text-gray-800">IAM Recommendations</h2>
                                <div class="flex space-x-2">
                                    <select v-model="filters.accountType"
                                        class="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                                        <option value="">All Types</option>
                                        <option value="serviceAccount">Service Account</option>
                                        <option value="user">User</option>
                                        <option value="group">Group</option>
                                    </select>
                                    <select v-model="filters.minRisk"
                                        class="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                                        <option value="0">All Risk Levels</option>
                                        <option value="70">High Risk (70+)</option>
                                        <option value="40">Medium+ (40+)</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        <div class="overflow-x-auto">
                            <table class="w-full">
                                <thead class="bg-gray-50">
                                    <tr>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Waste</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-200">
                                    <tr v-for="rec in recommendations" :key="rec.id" class="hover:bg-gray-50">
                                        <td class="px-6 py-4">
                                            <div class="text-sm font-medium text-gray-900 truncate max-w-xs" :title="rec.account_id">
                                                {{ rec.account_id.substring(0, 30) }}{{ rec.account_id.length > 30 ? '...' : '' }}
                                            </div>
                                            <div class="text-sm text-gray-500">{{ rec.project }}</div>
                                        </td>
                                        <td class="px-6 py-4">
                                            <span :class="getTypeBadgeClass(rec.account_type)" class="px-2 py-1 rounded-full text-xs font-medium">
                                                {{ rec.account_type }}
                                            </span>
                                        </td>
                                        <td class="px-6 py-4">
                                            <span :class="getRiskBadgeClass(rec.risk_score)" class="px-2 py-1 rounded-full text-xs font-medium">
                                                {{ rec.risk_score }}
                                            </span>
                                        </td>
                                        <td class="px-6 py-4">
                                            <div class="flex items-center">
                                                <div class="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                                    <div class="bg-yellow-500 h-2 rounded-full" :style="{width: rec.waste_percentage + '%'}"></div>
                                                </div>
                                                <span class="text-sm text-gray-600">{{ rec.waste_percentage }}%</span>
                                            </div>
                                        </td>
                                        <td class="px-6 py-4">
                                            <button @click="showRemediateModal(rec)"
                                                class="text-purple-600 hover:text-purple-800 text-sm font-medium">
                                                {{ rec.recommended_action === 'REMOVE_ROLE' ? 'Remove' : 'Replace' }}
                                            </button>
                                        </td>
                                    </tr>
                                    <tr v-if="recommendations.length === 0">
                                        <td colspan="5" class="px-6 py-12 text-center text-gray-500">
                                            No recommendations found. Run a scan to get started.
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Sidebar -->
                <div class="space-y-6">
                    <!-- Risk Distribution Chart -->
                    <div class="bg-white rounded-xl shadow-md p-6">
                        <h3 class="text-lg font-semibold text-gray-800 mb-4">Risk Distribution</h3>
                        <canvas id="riskChart" width="200" height="200"></canvas>
                    </div>

                    <!-- Projects List -->
                    <div class="bg-white rounded-xl shadow-md p-6">
                        <h3 class="text-lg font-semibold text-gray-800 mb-4">Projects</h3>
                        <div class="space-y-3">
                            <div v-for="project in projects" :key="project.name"
                                class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                <div>
                                    <p class="font-medium text-gray-800">{{ project.name }}</p>
                                    <p class="text-sm text-gray-500">{{ project.recommendation_count }} recommendations</p>
                                </div>
                                <span v-if="project.high_risk_count > 0"
                                    class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">
                                    {{ project.high_risk_count }} high risk
                                </span>
                            </div>
                            <p v-if="projects.length === 0" class="text-gray-500 text-center py-4">
                                No projects scanned yet
                            </p>
                        </div>
                    </div>

                    <!-- Last Scan Info -->
                    <div class="bg-white rounded-xl shadow-md p-6">
                        <h3 class="text-lg font-semibold text-gray-800 mb-4">Last Scan</h3>
                        <p v-if="stats.last_scan" class="text-gray-600">
                            {{ formatDate(stats.last_scan) }}
                        </p>
                        <p v-else class="text-gray-500">No scans yet</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Remediation Modal -->
        <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-semibold text-gray-800">Remediate Recommendation</h3>
                    <button @click="showModal = false" class="text-gray-400 hover:text-gray-600">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                <div v-if="selectedRec" class="space-y-4">
                    <div>
                        <p class="text-sm text-gray-500">Account</p>
                        <p class="font-medium">{{ selectedRec.account_id }}</p>
                    </div>
                    <div>
                        <p class="text-sm text-gray-500">Project</p>
                        <p class="font-medium">{{ selectedRec.project }}</p>
                    </div>
                    <div>
                        <p class="text-sm text-gray-500">Recommended Action</p>
                        <p class="font-medium">{{ selectedRec.recommended_action }}</p>
                    </div>
                    <div>
                        <p class="text-sm text-gray-500">Safety Score</p>
                        <p class="font-medium">{{ selectedRec.safe_to_apply_score }}</p>
                    </div>
                    <div class="pt-4 flex space-x-3">
                        <button @click="remediate(true)"
                            class="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700">
                            Simulate (Dry Run)
                        </button>
                        <button @click="remediate(false)"
                            class="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700">
                            Execute
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const { createApp, ref, onMounted, watch, computed } = Vue;

        createApp({
            setup() {
                const stats = ref({
                    total_recommendations: 0,
                    high_risk_count: 0,
                    medium_risk_count: 0,
                    low_risk_count: 0,
                    service_accounts: 0,
                    users: 0,
                    groups: 0,
                    projects_scanned: 0,
                    last_scan: null,
                });

                const recommendations = ref([]);
                const projects = ref([]);
                const authStatus = ref({ authenticated: false });
                const scanning = ref(false);
                const showModal = ref(false);
                const selectedRec = ref(null);
                const filters = ref({
                    accountType: '',
                    minRisk: 0,
                });

                let riskChart = null;

                const fetchStats = async () => {
                    try {
                        const res = await fetch('/api/stats');
                        stats.value = await res.json();
                        updateChart();
                    } catch (e) {
                        console.error('Failed to fetch stats:', e);
                    }
                };

                const fetchRecommendations = async () => {
                    try {
                        const params = new URLSearchParams();
                        if (filters.value.accountType) params.set('account_type', filters.value.accountType);
                        if (filters.value.minRisk) params.set('min_risk', filters.value.minRisk);

                        const res = await fetch('/api/recommendations?' + params);
                        recommendations.value = await res.json();
                    } catch (e) {
                        console.error('Failed to fetch recommendations:', e);
                    }
                };

                const fetchProjects = async () => {
                    try {
                        const res = await fetch('/api/projects');
                        projects.value = await res.json();
                    } catch (e) {
                        console.error('Failed to fetch projects:', e);
                    }
                };

                const fetchAuthStatus = async () => {
                    try {
                        const res = await fetch('/api/auth/status');
                        authStatus.value = await res.json();
                    } catch (e) {
                        console.error('Failed to fetch auth status:', e);
                    }
                };

                const startScan = async () => {
                    scanning.value = true;
                    try {
                        const res = await fetch('/api/scan', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ projects: ['*'], dry_run: true }),
                        });
                        const data = await res.json();

                        // Poll for completion
                        const pollInterval = setInterval(async () => {
                            const statusRes = await fetch('/api/scan/' + data.id);
                            const status = await statusRes.json();
                            if (status.status === 'completed' || status.status === 'failed') {
                                clearInterval(pollInterval);
                                scanning.value = false;
                                fetchStats();
                                fetchRecommendations();
                                fetchProjects();
                            }
                        }, 2000);
                    } catch (e) {
                        console.error('Failed to start scan:', e);
                        scanning.value = false;
                    }
                };

                const showRemediateModal = (rec) => {
                    selectedRec.value = rec;
                    showModal.value = true;
                };

                const remediate = async (dryRun) => {
                    try {
                        const res = await fetch('/api/remediate', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                recommendation_id: selectedRec.value.id,
                                dry_run: dryRun,
                            }),
                        });
                        const result = await res.json();
                        alert(dryRun ? 'Simulation complete: ' + result.status : 'Remediation ' + result.status);
                        showModal.value = false;
                    } catch (e) {
                        console.error('Remediation failed:', e);
                        alert('Remediation failed: ' + e.message);
                    }
                };

                const updateChart = () => {
                    const ctx = document.getElementById('riskChart');
                    if (!ctx) return;

                    if (riskChart) riskChart.destroy();

                    riskChart = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: ['High Risk', 'Medium Risk', 'Low Risk'],
                            datasets: [{
                                data: [
                                    stats.value.high_risk_count,
                                    stats.value.medium_risk_count,
                                    stats.value.low_risk_count,
                                ],
                                backgroundColor: ['#ef4444', '#f59e0b', '#22c55e'],
                            }],
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: {
                                    position: 'bottom',
                                },
                            },
                        },
                    });
                };

                const getRiskBadgeClass = (score) => {
                    if (score >= 70) return 'bg-red-100 text-red-800';
                    if (score >= 40) return 'bg-yellow-100 text-yellow-800';
                    return 'bg-green-100 text-green-800';
                };

                const getTypeBadgeClass = (type) => {
                    if (type === 'serviceAccount') return 'bg-purple-100 text-purple-800';
                    if (type === 'user') return 'bg-blue-100 text-blue-800';
                    return 'bg-gray-100 text-gray-800';
                };

                const formatDate = (dateStr) => {
                    if (!dateStr) return '';
                    return new Date(dateStr).toLocaleString();
                };

                watch(filters, () => {
                    fetchRecommendations();
                }, { deep: true });

                onMounted(() => {
                    fetchAuthStatus();
                    fetchStats();
                    fetchRecommendations();
                    fetchProjects();
                });

                return {
                    stats,
                    recommendations,
                    projects,
                    authStatus,
                    scanning,
                    showModal,
                    selectedRec,
                    filters,
                    startScan,
                    showRemediateModal,
                    remediate,
                    getRiskBadgeClass,
                    getTypeBadgeClass,
                    formatDate,
                };
            },
        }).mount('#app');
    </script>
</body>
</html>'''


def main():
    """Run the dashboard server."""
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="IAMSentry Dashboard Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--data-dir", default="./output", help="Data directory for results")

    args = parser.parse_args()

    # Set data directory
    global DATA_DIR
    DATA_DIR = Path(args.data_dir)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Starting IAMSentry Dashboard on http://{args.host}:{args.port}")
    print(f"Data directory: {DATA_DIR}")
    print("Press Ctrl+C to stop")

    uvicorn.run(
        "IAMSentry.dashboard.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
