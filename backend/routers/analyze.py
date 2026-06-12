import os
import json
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from services.analyzer import analyze_contract, load_result
from models.schemas import AnalysisResponse

router = APIRouter()

# In-memory job store — tracks status of every analysis job
# { job_id: { "status": "processing|done|error", "progress": 0-25, "report": {}, "error": "" } }
jobs: dict = {}


# ── Async analyze — returns immediately with job_id ───────────────────────

@router.post("/analyze/{contract_id}")
def analyze(contract_id: str, background_tasks: BackgroundTasks):
    """
    POST /api/analyze/{contract_id}

    Returns immediately with a job_id.
    Analysis runs in the background.
    Frontend polls GET /api/status/{job_id} every 2 seconds until done.
    """
    # Check contract exists before queuing
    try:
        import os
        if not os.path.exists(f"vector_store/{contract_id}.index"):
            raise HTTPException(
                status_code=404,
                detail=f"Contract '{contract_id}' not found. Upload it first."
            )
    except HTTPException:
        raise

    job_id = str(uuid.uuid4())

    # Register job as pending immediately
    jobs[job_id] = {
        "status": "processing",
        "progress": 0,
        "total": 25,
        "current_clause": "Starting analysis...",
        "report": None,
        "error": None,
    }

    # Queue the analysis to run in the background
    background_tasks.add_task(_run_analysis, job_id, contract_id)

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Analysis started. Poll /api/status/{job_id} for updates.",
    }


# ── Status polling endpoint ───────────────────────────────────────────────

@router.get("/status/{job_id}")
def get_status(job_id: str):
    """
    GET /api/status/{job_id}

    Frontend calls this every 2 seconds.
    Returns current progress and report when done.

    Possible status values:
      processing → still running, check progress
      done       → report is ready
      error      → something failed, check error field
    """
    job = jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found."
        )

    return job


# ── Fetch a saved report directly ────────────────────────────────────────

@router.get("/report/{contract_id}")
def get_report(contract_id: str):
    """
    GET /api/report/{contract_id}
    Returns a previously saved report from disk.
    Used when user navigates back to a past contract.
    """
    try:
        return load_result(contract_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for contract '{contract_id}'."
        )


# ── Background task ───────────────────────────────────────────────────────

def _run_analysis(job_id: str, contract_id: str):
    """
    Runs in the background after /analyze is called.
    Updates jobs[job_id] as each clause is processed
    so the frontend can show a live progress bar.
    """
    from services.retriever import retrieve
    from services.analyzer import CLAUSE_QUERIES, _call_claude, _group_findings, _generate_summary, _save_result
    import json

    try:
        findings = []
        total = len(CLAUSE_QUERIES)

        for i, (clause_key, query) in enumerate(CLAUSE_QUERIES):

            # Update progress so frontend can show "Checking IP ownership... 3/25"
            jobs[job_id]["progress"] = i
            jobs[job_id]["current_clause"] = _friendly_name(clause_key)

            # RAG retrieval + Claude call for this clause
            relevant_chunks = retrieve(query, contract_id, top_k=5)
            context = "\n\n---\n\n".join(relevant_chunks)
            result = _call_claude(clause_key, query, context)
            findings.append(result)

        # All clauses done — generate summary
        jobs[job_id]["current_clause"] = "Generating summary..."
        jobs[job_id]["progress"] = total

        grouped  = _group_findings(findings)
        summary  = _generate_summary(findings)

        report = {
            "contract_id":    contract_id,
            "findings":       findings,
            "grouped":        grouped,
            "high_risk_count":  sum(1 for f in findings if f.get("risk") == "high"),
            "medium_risk_count":sum(1 for f in findings if f.get("risk") == "medium"),
            "missing_count":    sum(1 for f in findings if not f.get("found")),
            "summary":        summary,
        }

        _save_result(contract_id, report)

        # Mark job as done — frontend will stop polling and show the report
        jobs[job_id]["status"] = "done"
        jobs[job_id]["report"] = report

    except Exception as e:
        # Mark job as failed — frontend shows error state
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@router.get("/contracts")
def list_contracts():
    """
    GET /api/contracts
    Returns all past analyses sorted newest-first.
    """
    results_dir = "results"
    if not os.path.exists(results_dir):
        return []
    contracts = []
    for fname in os.listdir(results_dir):
        if not fname.endswith(".json"):
            continue
        contract_id = fname[:-5]
        try:
            with open(os.path.join(results_dir, fname)) as f:
                report = json.load(f)
            contracts.append({
                "contract_id": contract_id,
                "filename": report.get("filename", "Unknown"),
                "analyzed_at": report.get("analyzed_at", ""),
                "high_risk_count": report.get("high_risk_count", 0),
                "medium_risk_count": report.get("medium_risk_count", 0),
                "missing_count": report.get("missing_count", 0),
            })
        except Exception:
            continue
    contracts.sort(key=lambda c: c.get("analyzed_at", ""), reverse=True)
    return contracts


def _friendly_name(clause_key: str) -> str:
    """Convert clause_key to a readable string for the progress bar."""
    names = {
        "ip_general":              "Checking IP ownership...",
        "ip_personal_time":        "Checking personal time IP...",
        "ip_preexisting":          "Checking pre-existing IP...",
        "ip_moral_rights":         "Checking moral rights...",
        "liability_cap":           "Checking liability cap...",
        "liability_consequential": "Checking consequential damages...",
        "liability_uncapped":      "Checking uncapped liability...",
        "liability_indemnification":"Checking indemnification...",
        "payment_schedule":        "Checking payment schedule...",
        "payment_late_fees":       "Checking late fees...",
        "payment_disputes":        "Checking payment disputes...",
        "payment_expenses":        "Checking expense reimbursement...",
        "termination_without_cause":"Checking termination rights...",
        "termination_for_cause":   "Checking termination for cause...",
        "termination_payment":     "Checking exit payment...",
        "termination_ip_on_exit":  "Checking IP on termination...",
        "auto_renewal":            "Checking auto-renewal...",
        "auto_renewal_notice":     "Checking renewal notice period...",
        "non_compete_scope":       "Checking non-compete...",
        "non_solicitation":        "Checking non-solicitation...",
        "exclusivity":             "Checking exclusivity...",
        "governing_law":           "Checking governing law...",
        "dispute_resolution":      "Checking dispute resolution...",
        "confidentiality_scope":   "Checking confidentiality scope...",
        "confidentiality_duration":"Checking confidentiality duration...",
    }
    return names.get(clause_key, f"Checking {clause_key}...")