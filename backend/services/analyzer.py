import os
import json
import anthropic
from services.retriever import retrieve

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-5"


# ══════════════════════════════════════════════════════════════════════════════
# QUERY SETS — one per contract type
# Each tuple is (clause_key, question your code asks automatically)
# The user never sees these — they're internal machinery
# ══════════════════════════════════════════════════════════════════════════════

FREELANCE_QUERIES = [
    ("ip_general",              "Who owns the work product and deliverables created under this contract?"),
    ("ip_personal_time",        "Does the IP assignment cover work created on personal time or using personal equipment?"),
    ("ip_preexisting",          "Are pre-existing tools, frameworks, or background IP protected for the contractor?"),
    ("ip_moral_rights",         "Are moral rights or attribution rights addressed in this contract?"),
    ("liability_cap",           "Is there a cap on total liability? What is the maximum dollar amount?"),
    ("liability_consequential",  "Does the contract exclude indirect or consequential damages?"),
    ("liability_indemnification","Is there an indemnification clause? Who indemnifies whom and for what?"),
    ("payment_schedule",        "What are the payment terms? Net 30, Net 60, milestone, or on delivery?"),
    ("payment_late_fees",       "Are there late payment fees or interest charges if the client does not pay on time?"),
    ("payment_kill_fee",        "Is there a kill fee or cancellation fee if the client cancels the project early?"),
    ("payment_expenses",        "Are expenses or out-of-pocket costs reimbursable?"),
    ("termination_without_cause","Can either party terminate without cause? How much notice is required?"),
    ("termination_for_cause",   "What events allow termination for cause? Is there a cure period?"),
    ("termination_ip_on_exit",  "Who owns deliverables and work in progress if the contract is terminated early?"),
    ("auto_renewal",            "Does this contract automatically renew? What is the renewal period?"),
    ("auto_renewal_notice",     "How many days notice is required to cancel or prevent auto-renewal?"),
    ("non_compete_scope",       "Is there a non-compete clause? How long and how broad geographically?"),
    ("non_solicitation",        "Is there a non-solicitation clause preventing work with the client's customers?"),
    ("exclusivity",             "Does this contract require exclusivity or prevent working with other clients?"),
    ("governing_law",           "What jurisdiction and governing law applies to this contract?"),
    ("dispute_resolution",      "How are disputes resolved — litigation, arbitration, or mediation?"),
    ("confidentiality_scope",   "What information is covered by the confidentiality clause?"),
    ("confidentiality_duration","How long does the confidentiality obligation last after termination?"),
    ("contract_dates",          "What is the start date, end date, and contract term length?"),
    ("warranty",                "Are there any warranties or representations made by the contractor?"),
]

EMPLOYMENT_QUERIES = [
    ("at_will",                 "Is this an at-will employment agreement? Can either party terminate at any time?"),
    ("compensation",            "What is the base salary or compensation? How and when is it paid?"),
    ("equity",                  "Is equity, stock options, or RSUs offered? What is the vesting schedule?"),
    ("benefits",                "What benefits are included — health, dental, vision, 401k, PTO?"),
    ("pto_policy",              "How many days of PTO or vacation are provided? Is unused PTO paid out?"),
    ("termination_notice",      "How much notice is required for termination by either party?"),
    ("severance",               "Is severance pay offered? Under what conditions and how much?"),
    ("non_compete_scope",       "Is there a non-compete clause? How long and how broad after leaving?"),
    ("non_solicitation",        "Is there a non-solicitation clause for clients or other employees?"),
    ("ip_assignment",           "Does the employer claim ownership of all work created during employment?"),
    ("ip_personal_time",        "Does IP assignment extend to work done on personal time or equipment?"),
    ("confidentiality_scope",   "What information must be kept confidential and for how long?"),
    ("arbitration",             "Is mandatory arbitration required for disputes? Are class actions waived?"),
    ("governing_law",           "What state law governs this agreement?"),
    ("probation_period",        "Is there a probationary period? What are the terms during that period?"),
    ("remote_work",             "Are remote work or flexible work arrangements addressed?"),
    ("bonus_structure",         "Is there a bonus or commission structure? What are the terms?"),
    ("expense_reimbursement",   "Are work-related expenses reimbursed? What is the process?"),
    ("background_check",        "Is employment contingent on a background check or drug test?"),
    ("moonlighting",            "Does the contract restrict working for other employers or side projects?"),
    ("relocation",              "Are there relocation requirements or relocation assistance offered?"),
    ("contract_dates",          "What is the start date and is this a fixed term or indefinite contract?"),
    ("liability_indemnification","Are there indemnification obligations on the employee?"),
    ("dispute_resolution",      "How are employment disputes resolved?"),
    ("entire_agreement",        "Is there an entire agreement clause superseding prior offers or promises?"),
]

NDA_QUERIES = [
    ("mutual_or_oneway",        "Is this a mutual NDA (both parties bound) or one-way (only one party bound)?"),
    ("confidential_info_scope", "How is confidential information defined? Is the definition broad or narrow?"),
    ("confidentiality_exceptions","What information is excluded from confidentiality — public domain, prior knowledge?"),
    ("permitted_disclosures",   "Who is permitted to receive confidential information — employees, advisors, lawyers?"),
    ("confidentiality_duration","How long does the confidentiality obligation last? Is it perpetual?"),
    ("breach_consequences",     "What are the consequences of breaching the NDA? Are damages or injunctions mentioned?"),
    ("return_of_information",   "Is there a requirement to return or destroy confidential information on termination?"),
    ("governing_law",           "What jurisdiction and governing law applies to this NDA?"),
    ("dispute_resolution",      "How are disputes about the NDA resolved?"),
    ("non_solicitation",        "Does the NDA include non-solicitation of employees or customers?"),
    ("non_compete",             "Does the NDA include any non-compete restrictions?"),
    ("residuals",               "Is there a residuals clause allowing use of information retained in unaided memory?"),
    ("contract_dates",          "What is the effective date and term of this NDA?"),
    ("purpose",                 "What is the stated purpose of this NDA? Is it limited to a specific project?"),
    ("assignment",              "Can either party assign this NDA to a third party such as an acquirer?"),
]

SAAS_QUERIES = [
    ("uptime_sla",              "Is there a service level agreement (SLA) for uptime? What is the guaranteed uptime percentage?"),
    ("data_ownership",          "Who owns the customer data stored in the platform?"),
    ("data_portability",        "Can the customer export their data? In what format and how quickly?"),
    ("data_deletion",           "What happens to customer data after contract termination? Is deletion guaranteed?"),
    ("auto_renewal",            "Does the subscription automatically renew? What notice is required to cancel?"),
    ("price_increases",         "Can the vendor increase prices during the contract term? How much notice is required?"),
    ("usage_limits",            "Are there usage limits — API calls, seats, storage? What happens if exceeded?"),
    ("liability_cap",           "Is liability capped? At what amount — monthly fees, annual fees, or other?"),
    ("liability_consequential", "Are consequential damages excluded? Who is protected by this exclusion?"),
    ("indemnification",         "Is there an IP indemnification clause protecting the customer from third-party IP claims?"),
    ("termination_for_cause",   "What events allow the customer to terminate for cause and get a refund?"),
    ("termination_convenience", "Can the customer terminate for convenience? Is there a refund for prepaid fees?"),
    ("payment_terms",           "When is payment due? Are there penalties for late payment?"),
    ("confidentiality",         "What confidentiality obligations does the vendor have regarding customer data?"),
    ("security_standards",      "Are any security standards or certifications (SOC2, ISO 27001) referenced?"),
    ("governing_law",           "What jurisdiction governs this agreement?"),
    ("dispute_resolution",      "How are disputes resolved — arbitration, litigation, or mediation?"),
    ("contract_dates",          "What is the subscription term — monthly, annual, or multi-year?"),
    ("support_terms",           "What level of support is included? What are the response time commitments?"),
    ("audit_rights",            "Does the vendor have the right to audit the customer's usage?"),
    ("acceptable_use",          "Is there an acceptable use policy? What uses are prohibited?"),
    ("subprocessors",           "Can the vendor use subprocessors? Is customer consent required?"),
    ("force_majeure",           "Is there a force majeure clause? Does it excuse payment obligations?"),
    ("entire_agreement",        "Is there an entire agreement clause superseding prior negotiations?"),
    ("modification",            "Can the vendor modify the terms unilaterally? How much notice is required?"),
]

LEASE_QUERIES = [
    ("rent_amount",             "What is the monthly rent amount and when is it due?"),
    ("rent_increases",          "Are rent increases allowed during the lease term? By how much and how often?"),
    ("lease_term",              "What is the lease start date, end date, and total term length?"),
    ("security_deposit",        "What is the security deposit amount? Under what conditions is it returned?"),
    ("early_termination",       "Can the tenant terminate early? What penalties or fees apply?"),
    ("auto_renewal",            "Does the lease automatically renew? What notice is required to prevent renewal?"),
    ("maintenance_repairs",     "Who is responsible for maintenance and repairs — landlord or tenant?"),
    ("utilities",               "Which utilities are included in the rent? Which are the tenant's responsibility?"),
    ("subletting",              "Is subletting or assignment of the lease permitted?"),
    ("alterations",             "Can the tenant make alterations or improvements to the property?"),
    ("pets",                    "Are pets allowed? Are there pet deposits or fees?"),
    ("late_fees",               "Are there late fees for overdue rent? How much and after how many days?"),
    ("entry_rights",            "When and how can the landlord enter the property? How much notice is required?"),
    ("termination_for_cause",   "Under what conditions can the landlord terminate the lease early?"),
    ("governing_law",           "What state law governs this lease agreement?"),
    ("dispute_resolution",      "How are disputes between landlord and tenant resolved?"),
    ("insurance",               "Is renter's insurance required? What coverage amounts?"),
    ("noise_restrictions",      "Are there noise or nuisance restrictions?"),
    ("parking",                 "Is parking included? Where and how many spaces?"),
    ("move_out_conditions",     "What conditions must be met at move-out to receive the full security deposit back?"),
]

# Fallback — used when contract type is "other" or detection fails
GENERAL_QUERIES = [
    ("ip_general",              "Who owns the work product and deliverables created under this contract?"),
    ("ip_personal_time",        "Does the IP assignment cover work created on personal time or personal equipment?"),
    ("ip_preexisting",          "Are pre-existing tools, frameworks, or background IP protected?"),
    ("ip_moral_rights",         "Are moral rights or attribution rights addressed?"),
    ("liability_cap",           "Is there a cap on total liability? What is the maximum amount?"),
    ("liability_consequential",  "Does the contract exclude indirect or consequential damages?"),
    ("liability_uncapped",      "Are there carve-outs where liability is explicitly uncapped?"),
    ("liability_indemnification","Is there an indemnification clause? Who indemnifies whom?"),
    ("payment_schedule",        "What are the payment terms? Net 30, Net 60, or milestone-based?"),
    ("payment_late_fees",       "Are there late payment fees or interest charges?"),
    ("payment_disputes",        "What happens if payment is disputed or withheld?"),
    ("payment_expenses",        "Are expenses or out-of-pocket costs reimbursable?"),
    ("termination_without_cause","Can either party terminate without cause? How much notice?"),
    ("termination_for_cause",   "What events allow termination for cause? Is there a cure period?"),
    ("termination_payment",     "What happens to payment upon early termination?"),
    ("termination_ip_on_exit",  "Who owns deliverables if the contract is terminated early?"),
    ("auto_renewal",            "Does this contract automatically renew?"),
    ("auto_renewal_notice",     "How many days notice is required to cancel auto-renewal?"),
    ("non_compete_scope",       "Is there a non-compete clause? How long and how broad?"),
    ("non_solicitation",        "Is there a non-solicitation clause?"),
    ("exclusivity",             "Does this contract require exclusivity?"),
    ("governing_law",           "What jurisdiction and governing law applies?"),
    ("dispute_resolution",      "How are disputes resolved?"),
    ("confidentiality_scope",   "What information is covered by the confidentiality clause?"),
    ("confidentiality_duration","How long does the confidentiality obligation last?"),
]

QUERIES_BY_TYPE = {
    "freelance":  FREELANCE_QUERIES,
    "employment": EMPLOYMENT_QUERIES,
    "nda":        NDA_QUERIES,
    "saas":       SAAS_QUERIES,
    "lease":      LEASE_QUERIES,
    "other":      GENERAL_QUERIES,
}


# ══════════════════════════════════════════════════════════════════════════════
# CONTRACT TYPE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def detect_contract_type(raw_text: str) -> str:
    """
    Send the first 500 words of the contract to Claude.
    Returns one of: freelance / employment / nda / saas / lease / other

    Why only 500 words?
    Contract type is almost always clear from the title, parties, and
    first few paragraphs. Sending the whole contract wastes tokens.
    This call costs ~$0.0001 — essentially free.
    """
    first_500_words = " ".join(raw_text.split()[:500])

    # temporary debug — remove after verifying
    print(f"\n[TYPE DETECTION] Sending first 500 words to Claude:")
    print(f"{first_500_words[:300]}...")

    prompt = f"""Read the beginning of this contract and classify its type.

Reply with EXACTLY one word from this list:
freelance / employment / nda / saas / lease / other

Rules:
- freelance: independent contractor, consulting, or services agreement
- employment: full-time or part-time job offer or employment contract
- nda: non-disclosure or confidentiality agreement
- saas: software subscription, SaaS, or software license agreement
- lease: property rental or lease agreement
- other: anything that doesn't fit the above

CONTRACT BEGINNING:
{first_500_words}

Reply with one word only:"""

    try:
        message = _client.messages.create(
            model=MODEL,
            max_tokens=10,  # one word — no need for more
            messages=[{"role": "user", "content": prompt}],
        )
        contract_type = message.content[0].text.strip().lower()

        # Validate response is one of our expected types
        if contract_type not in QUERIES_BY_TYPE:
            print(f"[TYPE DETECTION] Unexpected type '{contract_type}', falling back to 'other'")
            return "other"

        print(f"[TYPE DETECTION] Detected contract type: {contract_type}")
        return contract_type

    except Exception as e:
        print(f"[TYPE DETECTION] Failed ({e}), falling back to 'other'")
        return "other"


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def analyze_contract(contract_id: str, raw_text: str = None) -> dict:
    """
    Full analysis pipeline with contract type detection.

    Flow:
      1. Detect contract type from first 500 words  ← NEW
      2. Load the right query set for that type      ← NEW
      3. Run each query through hybrid RAG pipeline  ← unchanged
      4. Call Claude with grounded prompt            ← unchanged
      5. Return structured risk report               ← unchanged

    Args:
        contract_id: used to find the FAISS index and chunks
        raw_text:    full contract text for type detection
                     if None, loads from results/ folder
    """
    # Step 1 — detect contract type
    if raw_text:
        contract_type = detect_contract_type(raw_text)
    else:
        # Fallback — load from saved chunks if raw_text not passed
        try:
            import pickle, os
            chunks_path = f"vector_store/{contract_id}.chunks.json"
            with open(chunks_path) as f:
                import json as _json
                chunks = _json.load(f)
            raw_text = " ".join(chunks)
            contract_type = detect_contract_type(raw_text)
        except Exception:
            contract_type = "other"

    # Step 2 — load the right query set
    clause_queries = QUERIES_BY_TYPE.get(contract_type, GENERAL_QUERIES)
    print(f"[ANALYZER] Using {len(clause_queries)} queries for contract type: {contract_type}")

    # Step 3 — run each query through the pipeline
    findings = []
    for clause_key, query in clause_queries:
        relevant_chunks = retrieve(query, contract_id, top_k=5)
        context = "\n\n---\n\n".join(relevant_chunks)
        result = _call_claude(clause_key, query, context)
        findings.append(result)

    # Step 4 — build the report
    grouped = _group_findings(findings)

    report = {
        "contract_id":      contract_id,
        "contract_type":    contract_type,      # ← new field
        "findings":         findings,
        "grouped":          grouped,
        "high_risk_count":  sum(1 for f in findings if f.get("risk") == "high"),
        "medium_risk_count":sum(1 for f in findings if f.get("risk") == "medium"),
        "missing_count":    sum(1 for f in findings if not f.get("found")),
        "summary":          _generate_summary(findings, contract_type),
    }

    _save_result(contract_id, report)
    return report


# ══════════════════════════════════════════════════════════════════════════════
# CLAUDE API CALL — grounded prompt, structured JSON output
# ══════════════════════════════════════════════════════════════════════════════

def _call_claude(clause_key: str, query: str, context: str) -> dict:
    """
    Grounded prompt — Claude answers ONLY from retrieved chunks.
    Forces citation. Returns structured JSON. Returns NOT_FOUND if absent.
    """
    prompt = f"""You are a contract analyst helping a small business owner understand their contract.

STRICT RULES:
1. Answer ONLY using the CONTRACT TEXT provided below.
2. If the information is not present, set "found" to false and "evidence" to "NOT_FOUND".
3. Do NOT use outside legal knowledge — only what is in the text.
4. Quote the exact clause text as evidence (verbatim, max 2 sentences).
5. plain_english must be 1-2 sentences — simple language, no jargon.
6. risk: "high" if dangerous or one-sided, "medium" if needs attention,
         "low" if standard, "none" if not found.

CONTRACT TEXT:
{context}

QUESTION: {query}

Respond with ONLY valid JSON — no markdown, no code blocks, no extra text:
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


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _generate_summary(findings: list[dict], contract_type: str) -> str:
    """Plain English summary tailored to the detected contract type."""
    high_risk   = [f["clause_key"] for f in findings if f.get("risk") == "high"]
    medium_risk = [f["clause_key"] for f in findings if f.get("risk") == "medium"]
    missing     = [f["clause_key"] for f in findings if not f.get("found")]

    prompt = f"""Based on analysis of a {contract_type} contract:
- High risk clauses: {high_risk if high_risk else 'none'}
- Medium risk clauses: {medium_risk if medium_risk else 'none'}
- Missing clauses: {missing if missing else 'none'}

Write a 3-sentence plain English summary for a non-lawyer.
Be direct. Lead with the biggest risks first.
Mention missing clauses that should be there.
Return only the summary text — no JSON, no bullets."""

    try:
        message = _client.messages.create(
            model=MODEL,
            max_tokens=250,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception:
        return "Summary could not be generated. Please review individual findings above."


def _group_findings(findings: list[dict]) -> dict:
    """Group flat findings list into categories for frontend rendering."""
    groups: dict = {}
    for finding in findings:
        key = finding["clause_key"]
        # Use first word of clause_key as group
        group = key.split("_")[0]
        groups.setdefault(group, []).append(finding)
    return groups


def _fallback(clause_key: str, reason: str) -> dict:
    return {
        "clause_key":   clause_key,
        "found":        False,
        "evidence":     "NOT_FOUND",
        "confidence":   "low",
        "risk":         "none",
        "plain_english":"This clause could not be analyzed automatically. Review manually.",
    }


def _save_result(contract_id: str, report: dict) -> None:
    os.makedirs("results", exist_ok=True)
    with open(f"results/{contract_id}.json", "w") as f:
        json.dump(report, f, indent=2)


def load_result(contract_id: str) -> dict:
    path = f"results/{contract_id}.json"
    if not os.path.exists(path):
        raise FileNotFoundError(f"No report found for contract '{contract_id}'.")
    with open(path) as f:
        return json.load(f)