import os
import json
import anthropic
from services.retriever import retrieve

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-5"

# ── 25 targeted sub-queries ───────────────────────────────────────────────────
# Grouped by category. Each tuple is (clause_key, question).
# Your code asks all of these automatically — the user never sees them.

CLAUSE_QUERIES = [

    # ── IP OWNERSHIP (4 sub-queries) ─────────────────────────────────────────
    # One broad IP question misses edge cases. Four targeted ones don't.
    (
        "ip_general",
        "Who owns the work product and deliverables created under this contract? "
        "Does ownership transfer to the client or stay with the contractor?"
    ),
    (
        "ip_personal_time",
        "Does the IP assignment clause cover work created on the contractor's "
        "personal time, using personal equipment, or outside of working hours?"
    ),
    (
        "ip_preexisting",
        "Are pre-existing intellectual property rights, tools, frameworks, or "
        "background IP explicitly protected for the contractor?"
    ),
    (
        "ip_moral_rights",
        "Are moral rights, attribution rights, or the right to be credited "
        "for the work addressed anywhere in this contract?"
    ),

    # ── LIABILITY (4 sub-queries) ─────────────────────────────────────────────
    (
        "liability_cap",
        "Is there a cap on the total liability of either party? "
        "What is the maximum dollar amount or formula used to calculate the cap?"
    ),
    (
        "liability_consequential",
        "Does the contract exclude indirect, consequential, incidental, "
        "or punitive damages? Which party is protected by this exclusion?"
    ),
    (
        "liability_uncapped",
        "Are there any carve-outs or exceptions where liability is explicitly "
        "uncapped or unlimited, such as for gross negligence, fraud, or IP breach?"
    ),
    (
        "liability_indemnification",
        "Is there an indemnification clause? Who must indemnify whom, "
        "and what specific events or breaches trigger the indemnification obligation?"
    ),

    # ── PAYMENT TERMS (4 sub-queries) ────────────────────────────────────────
    (
        "payment_schedule",
        "What are the payment terms? When is payment due — Net 30, Net 60, "
        "on delivery, or on a milestone basis?"
    ),
    (
        "payment_late_fees",
        "Are there late payment fees, interest charges, or penalties "
        "if the client does not pay on time?"
    ),
    (
        "payment_disputes",
        "What happens if the client disputes an invoice or withholds payment? "
        "Is there a formal dispute resolution process for payment disagreements?"
    ),
    (
        "payment_expenses",
        "Are expenses, travel costs, or out-of-pocket costs reimbursable? "
        "What is the process for submitting and approving expense claims?"
    ),

    # ── TERMINATION (4 sub-queries) ───────────────────────────────────────────
    (
        "termination_without_cause",
        "Can either party terminate this contract without cause or for convenience? "
        "How much notice is required for termination without cause?"
    ),
    (
        "termination_for_cause",
        "What specific events or breaches allow termination for cause? "
        "Is there a cure period where the breaching party can fix the issue?"
    ),
    (
        "termination_payment",
        "What happens to payment upon termination? Is the contractor paid "
        "for work completed before termination? Are kill fees or cancellation "
        "fees mentioned?"
    ),
    (
        "termination_ip_on_exit",
        "What happens to intellectual property and deliverables if the contract "
        "is terminated early — before the project is complete?"
    ),

    # ── AUTO-RENEWAL (2 sub-queries) ─────────────────────────────────────────
    (
        "auto_renewal",
        "Does this contract automatically renew at the end of the term? "
        "What is the renewal period length?"
    ),
    (
        "auto_renewal_notice",
        "How many days notice is required to cancel or prevent auto-renewal? "
        "What is the deadline and method for providing cancellation notice?"
    ),

    # ── NON-COMPETE AND RESTRICTIONS (3 sub-queries) ─────────────────────────
    (
        "non_compete_scope",
        "Is there a non-compete clause? How long does it last after termination "
        "and what geographic area or industry does it cover?"
    ),
    (
        "non_solicitation",
        "Is there a non-solicitation clause preventing the contractor from "
        "working with the client's customers or hiring their employees?"
    ),
    (
        "exclusivity",
        "Does this contract require exclusivity? Is the contractor prohibited "
        "from working with other clients or competitors during the contract term?"
    ),

    # ── GOVERNING LAW AND DISPUTES (2 sub-queries) ───────────────────────────
    (
        "governing_law",
        "What jurisdiction and governing law applies to this contract? "
        "Which state or country's laws govern disputes?"
    ),
    (
        "dispute_resolution",
        "How are disputes resolved — litigation, arbitration, or mediation? "
        "Is arbitration mandatory? Who pays arbitration costs?"
    ),

    # ── CONFIDENTIALITY (2 sub-queries) ──────────────────────────────────────
    (
        "confidentiality_scope",
        "What information is covered by the confidentiality or NDA clause? "
        "How broadly is confidential information defined?"
    ),
    (
        "confidentiality_duration",
        "How long does the confidentiality obligation last? "
        "Does it survive termination of the contract and for how many years?"
    ),

]


def analyze_contract(contract_id: str) -> dict:
    """
    Run the full RAG analysis pipeline for a contract.
    Runs all 25 sub-queries, groups findings by category,
    and returns a structured risk report.
    """
    findings = []

    for clause_key, query in CLAUSE_QUERIES:
        relevant_chunks = retrieve(query, contract_id, top_k=5)
        context = "\n\n---\n\n".join(relevant_chunks)
        result = _call_claude(clause_key, query, context)
        findings.append(result)

    # Group findings by category for cleaner report structure
    grouped = _group_findings(findings)

    report = {
        "contract_id": contract_id,
        "findings": findings,           # flat list — for frontend to render
        "grouped": grouped,             # by category — for summary sections
        "high_risk_count": sum(1 for f in findings if f.get("risk") == "high"),
        "medium_risk_count": sum(1 for f in findings if f.get("risk") == "medium"),
        "missing_count": sum(1 for f in findings if not f.get("found")),
        "summary": _generate_summary(findings),
    }

    _save_result(contract_id, report)
    return report


def _call_claude(clause_key: str, query: str, context: str) -> dict:
    """
    Grounded prompt — Claude answers ONLY from retrieved contract chunks.
    Forces citation, returns structured JSON, returns NOT_FOUND if absent.
    """
    prompt = f"""You are a contract analyst helping a small business owner understand their contract.

STRICT RULES:
1. Answer ONLY using the CONTRACT TEXT provided below.
2. If the information is not in the text, set "found" to false and "evidence" to "NOT_FOUND".
3. Do NOT use any outside legal knowledge — only what is in the text.
4. Quote the exact clause text as evidence (verbatim, max 2 sentences).
5. plain_english must be under 2 sentences — simple language, no jargon.
6. For "risk": use "high" if the clause is dangerous or heavily one-sided,
   "medium" if it needs attention, "low" if it is standard, "none" if not found.

CONTRACT TEXT:
{context}

QUESTION: {query}

Respond with ONLY a valid JSON object — no markdown, no code blocks, no extra text:
{{
  "clause_key": "{clause_key}",
  "found": true or false,
  "evidence": "exact quote from the contract, or NOT_FOUND",
  "confidence": "high" or "medium" or "low",
  "risk": "high" or "medium" or "low" or "none",
  "plain_english": "one or two plain sentences for a non-lawyer"
}}"""

    try:
        message = _client.messages.create(
            model=MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()

        # Strip markdown fences if Claude adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError:
        return _fallback(clause_key, "Could not parse response as JSON.")
    except Exception as e:
        return _fallback(clause_key, str(e))


def _group_findings(findings: list[dict]) -> dict:
    """
    Group flat findings list into categories for the frontend
    to render as collapsible sections.
    """
    groups = {
        "ip_ownership":    [],
        "liability":       [],
        "payment":         [],
        "termination":     [],
        "auto_renewal":    [],
        "restrictions":    [],
        "governing_law":   [],
        "confidentiality": [],
    }

    prefix_map = {
        "ip_":             "ip_ownership",
        "liability_":      "liability",
        "payment_":        "payment",
        "termination_":    "termination",
        "auto_renewal":    "auto_renewal",
        "non_compete":     "restrictions",
        "non_solicit":     "restrictions",
        "exclusivity":     "restrictions",
        "governing_law":   "governing_law",
        "dispute_":        "governing_law",
        "confidentiality_":"confidentiality",
    }

    for finding in findings:
        key = finding["clause_key"]
        placed = False
        for prefix, group in prefix_map.items():
            if key.startswith(prefix):
                groups[group].append(finding)
                placed = True
                break
        if not placed:
            groups.setdefault("other", []).append(finding)

    return groups


def _generate_summary(findings: list[dict]) -> str:
    """
    Ask Claude to write a 3-sentence plain English summary
    of overall contract risk based on all 25 findings.
    """
    high_risk  = [f["clause_key"] for f in findings if f.get("risk") == "high"]
    medium_risk = [f["clause_key"] for f in findings if f.get("risk") == "medium"]
    missing    = [f["clause_key"] for f in findings if not f.get("found")]

    prompt = f"""Based on a contract analysis with 25 checks:
- High risk clauses: {high_risk if high_risk else 'none'}
- Medium risk clauses: {medium_risk if medium_risk else 'none'}
- Missing clauses (not found in contract): {missing if missing else 'none'}

Write a 3-sentence plain English summary of the overall contract risk
for a non-lawyer freelancer or small business owner.
Be direct. Lead with the biggest risks. 
Mention any missing clauses that should be there.
Return only the summary text — no JSON, no bullet points."""

    try:
        message = _client.messages.create(
            model=MODEL,
            max_tokens=250,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception:
        return "Summary could not be generated. Please review individual findings above."


def _fallback(clause_key: str, reason: str) -> dict:
    return {
        "clause_key": clause_key,
        "found": False,
        "evidence": "NOT_FOUND",
        "confidence": "low",
        "risk": "none",
        "plain_english": "This clause could not be analyzed automatically. Review manually.",
    }


def _save_result(contract_id: str, report: dict) -> None:
    from datetime import datetime, timezone
    os.makedirs("results", exist_ok=True)
    meta_path = f"uploads/{contract_id}.meta.json"
    if os.path.exists(meta_path):
        with open(meta_path) as mf:
            meta = json.load(mf)
        report.setdefault("filename", meta.get("filename"))
    report.setdefault("analyzed_at", datetime.now(timezone.utc).isoformat())
    with open(f"results/{contract_id}.json", "w") as f:
        json.dump(report, f, indent=2)


def load_result(contract_id: str) -> dict:
    path = f"results/{contract_id}.json"
    if not os.path.exists(path):
        raise FileNotFoundError(f"No report found for contract '{contract_id}'.")
    with open(path) as f:
        return json.load(f)