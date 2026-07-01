import os
from supabase import create_client, Client

_client = None

def get_db():
    global _client
    if _client is None:
        _client = create_client(
            os.environ.get("SUPABASE_URL"),
            os.environ.get("SUPABASE_SERVICE_KEY")
        )
    return _client

def save_job(job_id, contract_id, user_id="anonymous"):
    get_db().table("jobs").insert({
        "job_id": job_id,
        "contract_id": contract_id,
        "user_id": user_id,
        "status": "processing",
        "progress": 0,
        "total": 25,
        "current_clause": "Starting analysis..."
    }).execute()

def update_job(job_id, **kwargs):
    get_db().table("jobs").update(kwargs).eq("job_id", job_id).execute()

def get_job(job_id):
    result = get_db().table("jobs").select("*").eq("job_id", job_id).execute()
    return result.data[0] if result.data else None

def save_contract(contract_id, user_id, report):
    get_db().table("contracts").upsert({
        "contract_id": contract_id,
        "user_id": user_id,
        "filename": report.get("filename", "Unknown"),
        "contract_type": report.get("contract_type", "other"),
        "high_risk_count": report.get("high_risk_count", 0),
        "medium_risk_count": report.get("medium_risk_count", 0),
        "missing_count": report.get("missing_count", 0),
        "summary": report.get("summary", ""),
        "report_json": report,
    }).execute()

def get_contract(contract_id):
    result = get_db().table("contracts").select("*").eq("contract_id", contract_id).execute()
    return result.data[0].get("report_json") if result.data else None

def list_contracts(user_id):
    result = get_db().table("contracts").select(
        "contract_id, filename, contract_type, high_risk_count, medium_risk_count, analyzed_at"
    ).eq("user_id", user_id).order("analyzed_at", desc=True).execute()
    return result.data or []
