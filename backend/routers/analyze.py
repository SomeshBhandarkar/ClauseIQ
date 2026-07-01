import os
import json
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from services.analyzer import analyze_contract, load_result
from services.database import save_job, update_job, get_job, save_contract, get_contract

router = APIRouter()


@router.post("/analyze/{contract_id}")
def analyze(contract_id: str, background_tasks: BackgroundTasks):
    """
    POST /api/analyze/{contract_id}
    Returns immediately with job_id.
    Analysis runs in background — frontend polls /api/status/{job_id}
    """
    # Check vector store exists
    if not os.path.exists(f"vector_store/{contract_id}.index"):
        raise HTTPException(
            status_code=404,
            detail=f"Contract '{contract_id}' not found. Upload it first."
        )

    job_id = str(uuid.uuid4())
    save_job(job_id, contract_id)

    background_tasks.add_task(_run_analysis, job_id, contract_id)

    return {
        "job_id":  job_id,
        "status":  "processing",
        "message": "Analysis started. Poll /api/status/{job_id} for updates.",
    }


@router.get("/status/{job_id}")
def get_status(job_id: str):
    """
    GET /api/status/{job_id}
    Frontend polls this every 2 seconds.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@router.get("/report/{contract_id}")
def get_report(contract_id: str):
    """GET /api/report/{contract_id} — fetch a saved report, DB first, disk as fallback."""
    report = get_contract(contract_id)
    if report:
        return report
    try:
        return load_result(contract_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for contract '{contract_id}'."
        )


def _run_analysis(job_id: str, contract_id: str):
    """
    Background task — runs after /analyze is called.
    Loads raw text from chunks, detects contract type,
    runs the right query set, updates progress per clause.
    """
    from services.retriever import retrieve
    from services.analyzer import (
        QUERIES_BY_TYPE, GENERAL_QUERIES,
        detect_contract_type, _call_claude,
        _group_findings, _generate_summary,
        _save_result
    )

    try:
        # Load raw text from saved chunks for type detection
        chunks_path = f"vector_store/{contract_id}.chunks.json"
        with open(chunks_path) as f:
            chunks = json.load(f)
        raw_text = " ".join(chunks)

        # Step 1 — detect contract type
        update_job(job_id, current_clause="Detecting contract type...")
        contract_type = detect_contract_type(raw_text)
        update_job(job_id, contract_type=contract_type)

        # Step 2 — load right query set
        clause_queries = QUERIES_BY_TYPE.get(contract_type, GENERAL_QUERIES)
        update_job(job_id, total=len(clause_queries))

        # Step 3 — run each query
        findings = []
        for i, (clause_key, query) in enumerate(clause_queries):
            update_job(job_id, progress=i, current_clause=_friendly_name(clause_key))

            relevant_chunks = retrieve(query, contract_id, top_k=5)
            context = "\n\n---\n\n".join(relevant_chunks)
            result  = _call_claude(clause_key, query, context)
            findings.append(result)

        # Step 4 — generate summary
        update_job(job_id, current_clause="Generating summary...", progress=len(clause_queries))

        grouped = _group_findings(findings)
        summary = _generate_summary(findings, contract_type)

        filename = None
        try:
            with open(f"uploads/{contract_id}.meta.json") as mf:
                filename = json.load(mf).get("filename")
        except FileNotFoundError:
            pass

        report = {
            "contract_id":       contract_id,
            "filename":          filename or "Unknown",
            "contract_type":     contract_type,
            "findings":          findings,
            "grouped":           grouped,
            "high_risk_count":   sum(1 for f in findings if f.get("risk") == "high"),
            "medium_risk_count": sum(1 for f in findings if f.get("risk") == "medium"),
            "missing_count":     sum(1 for f in findings if not f.get("found")),
            "summary":           summary,
        }

        _save_result(contract_id, report)
        save_contract(contract_id, None, report)

        update_job(job_id, status="done")

    except Exception as e:
        update_job(job_id, status="error", error=str(e))


def _friendly_name(clause_key: str) -> str:
    """Convert clause_key to readable progress bar text."""
    names = {
        "ip_general":               "Checking IP ownership...",
        "ip_personal_time":         "Checking personal time IP...",
        "ip_preexisting":           "Checking pre-existing IP...",
        "ip_moral_rights":          "Checking moral rights...",
        "liability_cap":            "Checking liability cap...",
        "liability_consequential":  "Checking consequential damages...",
        "liability_uncapped":       "Checking uncapped liability...",
        "liability_indemnification":"Checking indemnification...",
        "payment_schedule":         "Checking payment schedule...",
        "payment_late_fees":        "Checking late fees...",
        "payment_disputes":         "Checking payment disputes...",
        "payment_expenses":         "Checking expense reimbursement...",
        "payment_kill_fee":         "Checking kill fee...",
        "termination_without_cause":"Checking termination rights...",
        "termination_for_cause":    "Checking termination for cause...",
        "termination_payment":      "Checking exit payment...",
        "termination_ip_on_exit":   "Checking IP on termination...",
        "auto_renewal":             "Checking auto-renewal...",
        "auto_renewal_notice":      "Checking renewal notice period...",
        "non_compete_scope":        "Checking non-compete...",
        "non_solicitation":         "Checking non-solicitation...",
        "exclusivity":              "Checking exclusivity...",
        "governing_law":            "Checking governing law...",
        "dispute_resolution":       "Checking dispute resolution...",
        "confidentiality_scope":    "Checking confidentiality scope...",
        "confidentiality_duration": "Checking confidentiality duration...",
        "at_will":                  "Checking at-will employment...",
        "compensation":             "Checking compensation...",
        "equity":                   "Checking equity and vesting...",
        "benefits":                 "Checking benefits...",
        "mutual_or_oneway":         "Checking NDA type...",
        "confidential_info_scope":  "Checking confidentiality scope...",
        "uptime_sla":               "Checking uptime SLA...",
        "data_ownership":           "Checking data ownership...",
        "rent_amount":              "Checking rent amount...",
        "security_deposit":         "Checking security deposit...",
    }
    return names.get(clause_key, f"Checking {clause_key.replace('_', ' ')}...")