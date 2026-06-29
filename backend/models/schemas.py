from pydantic import BaseModel
from typing import Optional


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    contract_id: str
    filename: str
    chunk_count: int
    message: str


# ── Analysis ──────────────────────────────────────────────────────────────────

class ClauseFinding(BaseModel):
    clause_key: str
    found: bool
    evidence: str
    confidence: str           # "high" | "medium" | "low"
    risk: str                 # "high" | "medium" | "low" | "none"
    plain_english: str
    negotiation_tip: str = "" # empty string if low/none risk


class AnalysisResponse(BaseModel):
    contract_id: str
    contract_type: str        # "freelance" | "employment" | "nda" | "saas" | "lease" | "other"
    findings: list[ClauseFinding]
    grouped: dict
    high_risk_count: int
    medium_risk_count: int
    missing_count: int
    summary: str


# ── Async job status ──────────────────────────────────────────────────────────

class JobStartResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    status: str                          # "processing" | "done" | "error"
    progress: int                        # 0-25 clauses completed
    total: int                           # always 25
    current_clause: str                  # "Checking IP ownership..."
    report: Optional[AnalysisResponse]   # populated when status == "done"
    error: Optional[str]                 # populated when status == "error"


# ── Stripe ────────────────────────────────────────────────────────────────────

class CheckoutSessionRequest(BaseModel):
    user_id: str
    email: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str