import os
import json
import numpy as np
import faiss
from fastembed import TextEmbedding

_model = None


def get_model():
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _model

STORE_DIR    = "vector_store"
KB_INDEX     = os.path.join(STORE_DIR, "knowledge_base.index")
KB_JSON      = os.path.join(STORE_DIR, "knowledge_base.json")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERT CLAUSE DEFINITIONS
# This is your competitive moat — expert-written context for every clause type.
# Claude uses this to compare the contract against industry standard.
# Built once, never changes unless you add more entries.
# ══════════════════════════════════════════════════════════════════════════════

CLAUSE_KNOWLEDGE = [

    # ── IP OWNERSHIP ──────────────────────────────────────────────────────────
    {
        "clause_key":          "ip_ownership_general",
        "what_it_means":       "An IP ownership clause determines who legally owns the work product created during the contract. In work-for-hire arrangements, the client owns everything. In licensing arrangements, the contractor retains ownership but grants usage rights.",
        "industry_standard":   "Standard freelance contracts assign ownership of final deliverables to the client but protect the contractor's pre-existing tools, frameworks, and background IP. Pure work-for-hire with no carve-outs is aggressive.",
        "red_flags":           "Watch for: 'all work product', 'any and all deliverables', 'including work created outside working hours'. These phrases mean the client claims everything with no exceptions.",
        "negotiation":         "Negotiate to add: 'excluding Contractor pre-existing IP listed in Schedule A' and 'excluding work created on Contractor personal time unrelated to this agreement'.",
    },
    {
        "clause_key":          "ip_ownership_personal_time",
        "what_it_means":       "Some IP assignment clauses extend beyond work done for the client and claim ownership of anything the contractor creates during the contract period — even personal side projects built at home on weekends.",
        "industry_standard":   "Reputable companies limit IP assignment to work done using company resources or directly related to company business. Claiming personal-time work is aggressive and increasingly unenforceable in some states like California.",
        "red_flags":           "Watch for: 'during the term of this agreement', 'whether or not during working hours', 'using any company resources'. California Labor Code Section 2870 limits this for employees.",
        "negotiation":         "Add: 'This assignment excludes any invention that does not relate to Company business and was developed entirely on Contractor own time without using Company equipment or resources.'",
    },
    {
        "clause_key":          "ip_ownership_preexisting",
        "what_it_means":       "Pre-existing IP refers to tools, code, frameworks, designs, or methods the contractor developed before this contract started. Without explicit protection, these may be swept into the IP assignment clause.",
        "industry_standard":   "Standard practice is to attach a Schedule A listing the contractor's pre-existing IP that is explicitly excluded from assignment. This protects the contractor's ability to reuse their own tools on future projects.",
        "red_flags":           "If there is no Schedule A or no carve-out for pre-existing IP, assume the client will claim ownership of everything including your existing tools and frameworks.",
        "negotiation":         "Add Schedule A listing all pre-existing tools and frameworks. Add language: 'Contractor retains all rights to pre-existing IP listed in Schedule A. Client receives a limited license to use such IP solely for the deliverables.'",
    },
    {
        "clause_key":          "ip_ownership_moral_rights",
        "what_it_means":       "Moral rights are the right to be credited as the creator and the right to object to changes that harm your reputation. In the US moral rights are limited but exist for visual art under VARA. In EU countries they are much stronger.",
        "industry_standard":   "Most US commercial contracts waive moral rights entirely. This is standard and generally acceptable for commercial work. For artistic or portfolio work, consider negotiating attribution rights.",
        "red_flags":           "If you want portfolio usage rights, ensure the contract explicitly allows you to show the work in your portfolio. Many NDA clauses accidentally prevent this.",
        "negotiation":         "Add: 'Contractor retains the right to display the work in their professional portfolio subject to any confidentiality obligations in this agreement.'",
    },

    # ── LIABILITY ─────────────────────────────────────────────────────────────
    {
        "clause_key":          "liability_cap",
        "what_it_means":       "A liability cap limits the maximum amount one party can be sued for under this contract. Without a cap, a contractor could theoretically be sued for millions even on a small project.",
        "industry_standard":   "Standard freelance contracts cap liability at the total fees paid under the contract or 3 months of fees, whichever is higher. Enterprise contracts often use 12 months of fees. Uncapped liability on the contractor side is highly aggressive.",
        "red_flags":           "If there is no liability cap for the contractor, a single mistake could expose you to claims far exceeding your project fee. This is the single biggest financial risk in freelance contracts.",
        "negotiation":         "Add: 'Each party total liability under this agreement shall not exceed the total fees paid by Client to Contractor in the 12 months preceding the claim.'",
    },
    {
        "clause_key":          "liability_consequential",
        "what_it_means":       "Consequential damages are indirect losses caused by a breach — lost profits, lost business opportunities, reputational harm. These can be enormous and completely disproportionate to the contract value.",
        "industry_standard":   "Standard commercial contracts exclude consequential, indirect, incidental, and punitive damages for BOTH parties. A one-sided exclusion that only protects the client is aggressive.",
        "red_flags":           "Watch for asymmetric exclusions where the client excludes consequential damages for themselves but not for the contractor. This leaves the contractor fully exposed to indirect loss claims.",
        "negotiation":         "Ensure the exclusion is mutual: 'Neither party shall be liable for any indirect, consequential, incidental, special, or punitive damages, regardless of the cause of action.'",
    },
    {
        "clause_key":          "liability_indemnification",
        "what_it_means":       "Indemnification means one party agrees to cover the other party's legal costs and damages if a third party sues. Broad indemnification clauses can make the contractor responsible for the client's legal problems.",
        "industry_standard":   "Standard indemnification covers only the indemnifying party's own acts, errors, and omissions. Broad indemnification that covers the client's own negligence is highly aggressive and should be rejected.",
        "red_flags":           "Watch for: 'any and all claims', 'arising out of or related to', 'including client negligence'. These phrases can make you responsible for things entirely outside your control.",
        "negotiation":         "Limit to: 'Contractor shall indemnify Client solely against third-party claims arising directly from Contractor gross negligence or willful misconduct.' Exclude client's own acts.",
    },
    {
        "clause_key":          "liability_uncapped",
        "what_it_means":       "Certain types of claims are often carved out from liability caps — IP infringement, confidentiality breaches, fraud, and gross negligence. This means unlimited liability exposure for these specific events.",
        "industry_standard":   "IP indemnification carve-outs are standard and acceptable. Confidentiality breach carve-outs are common. Carve-outs for ordinary negligence or general breach of contract are aggressive.",
        "red_flags":           "Watch for carve-outs that are so broad they swallow the cap entirely. If 'breach of contract' is a carve-out, the cap is effectively meaningless.",
        "negotiation":         "Limit carve-outs to gross negligence, fraud, and willful misconduct only. IP and confidentiality carve-outs should have their own reasonable sub-caps.",
    },

    # ── PAYMENT ───────────────────────────────────────────────────────────────
    {
        "clause_key":          "payment_schedule",
        "what_it_means":       "Payment terms define when invoices must be paid. Net 30 means payment within 30 days of invoice. Net 60 is longer and puts cash flow pressure on contractors. Milestone payments tie payment to deliverable approval.",
        "industry_standard":   "Net 30 is standard for freelance work. Net 60 is acceptable for large enterprises but should come with a late fee provision. Net 90 or longer is aggressive and should be negotiated.",
        "red_flags":           "Watch for: 'payment upon client satisfaction', 'payment upon final approval', 'payment within 90 days'. These give clients too much control over when you get paid.",
        "negotiation":         "Push for 50% upfront and 50% on delivery for project work. For ongoing work, negotiate Net 30 with 1.5% monthly interest on late payments.",
    },
    {
        "clause_key":          "payment_late_fees",
        "what_it_means":       "Late fee provisions charge interest on overdue invoices, incentivizing clients to pay on time. Without late fees, clients have no financial incentive to prioritize your invoices.",
        "industry_standard":   "1.5% per month (18% annually) is standard for late payment interest. Some jurisdictions have maximum limits. Any late fee provision is better than none.",
        "red_flags":           "No late fee provision means the client can pay whenever they want with no consequence. Combined with Net 60 terms this can severely impact cash flow.",
        "negotiation":         "Add: 'Invoices unpaid after 30 days shall accrue interest at 1.5% per month on the outstanding balance until paid in full.'",
    },
    {
        "clause_key":          "payment_kill_fee",
        "what_it_means":       "A kill fee compensates the contractor if the client cancels the project mid-way. Without it, the contractor loses income for time already blocked and work already done.",
        "industry_standard":   "Standard kill fees are 25-50% of remaining project value for cancellation after work has started. Some contracts use a sliding scale based on project completion percentage.",
        "red_flags":           "No kill fee provision means you can lose substantial income if a client cancels after you have turned down other work to accommodate this project.",
        "negotiation":         "Add: 'If Client cancels this project after work has commenced, Client shall pay a kill fee equal to 25% of the remaining unpaid project fees plus payment for all work completed to date.'",
    },
    {
        "clause_key":          "payment_expenses",
        "what_it_means":       "Expense reimbursement clauses specify whether the client will reimburse out-of-pocket costs like travel, software licenses, stock assets, or third-party services incurred during the project.",
        "industry_standard":   "Standard practice is to reimburse pre-approved expenses with receipts. Expenses above a certain threshold (typically $100-500) require prior written approval.",
        "red_flags":           "No expense clause means you bear all costs personally. Watch for clauses requiring expenses to be included in your project fee with no separate reimbursement.",
        "negotiation":         "Add: 'Client shall reimburse Contractor for all pre-approved out-of-pocket expenses incurred in connection with this agreement, submitted with receipts within 30 days.'",
    },

    # ── TERMINATION ───────────────────────────────────────────────────────────
    {
        "clause_key":          "termination_without_cause",
        "what_it_means":       "Termination without cause (or for convenience) allows a party to end the contract for any reason with advance notice. This is different from termination for cause which requires a specific breach.",
        "industry_standard":   "30 days notice for termination without cause is standard for freelance contracts. Enterprise clients often require 60-90 days. Less than 14 days notice is aggressive.",
        "red_flags":           "Watch for: immediate termination rights, very short notice periods (under 14 days), or termination without any payment for work completed.",
        "negotiation":         "Ensure termination without cause requires payment for all work completed plus the kill fee. Add: 'Upon termination for convenience, Client shall pay for all work completed through the termination date plus the applicable kill fee.'",
    },
    {
        "clause_key":          "termination_for_cause",
        "what_it_means":       "Termination for cause allows immediate termination when one party materially breaches the contract. A cure period gives the breaching party time to fix the problem before termination takes effect.",
        "industry_standard":   "A 15-30 day cure period is standard for material breach before termination for cause takes effect. Immediate termination without cure period is aggressive except for serious breaches like fraud.",
        "red_flags":           "Watch for very broad definitions of 'cause' that give the client subjective termination rights. 'Failure to meet client expectations' is too vague and gives clients a free termination option.",
        "negotiation":         "Ensure cause is clearly defined and limited to material breach. Add a 15-day cure period: 'The breaching party shall have 15 days after written notice to cure any material breach before termination takes effect.'",
    },
    {
        "clause_key":          "termination_ip_on_exit",
        "what_it_means":       "This determines what happens to work in progress if the contract ends early. Without clarity, disputes arise over who owns half-finished deliverables and whether partial payment is owed.",
        "industry_standard":   "Standard practice is that the client receives ownership of completed and paid-for work. Work in progress at termination is paid on a pro-rata basis and ownership transfers upon payment.",
        "red_flags":           "Watch for clauses where the client receives all work product including incomplete work without additional payment. This means you do work for free.",
        "negotiation":         "Add: 'Upon termination, Client shall receive ownership of all deliverables paid for in full. Work in progress shall be delivered upon payment of pro-rata fees for work completed to the termination date.'",
    },

    # ── AUTO-RENEWAL ──────────────────────────────────────────────────────────
    {
        "clause_key":          "auto_renewal_exists",
        "what_it_means":       "Auto-renewal clauses automatically extend the contract for another term unless one party actively cancels before the deadline. Missing the cancellation deadline means you are locked in for another full term.",
        "industry_standard":   "Auto-renewal with 30-60 days notice to cancel is standard for ongoing service contracts. Annual contracts typically require 30-90 days advance notice. Short notice windows under 14 days are aggressive.",
        "red_flags":           "Watch for: very long renewal terms (2+ years), very short cancellation windows (under 30 days), and auto-renewal combined with price increase rights.",
        "negotiation":         "Ensure the notice period is reasonable (minimum 30 days) and the renewal term matches the original term. Add calendar reminders for cancellation deadlines the moment you sign.",
    },
    {
        "clause_key":          "auto_renewal_notice",
        "what_it_means":       "The notice period for cancelling auto-renewal is how many days before the contract ends you must notify the other party that you do not want to renew. Missing this window locks you in for another full term.",
        "industry_standard":   "30 days notice is the absolute minimum acceptable. 60-90 days is standard for annual contracts. Longer notice periods give clients more time to find alternatives and contractors time to plan.",
        "red_flags":           "Notice windows under 30 days are designed to be missed. A 60-day notice window on an annual contract means you must decide whether to renew 2 months before the contract ends.",
        "negotiation":         "If the notice period exceeds 60 days, negotiate it down. Always calendar the deadline immediately after signing. Consider adding a reminder obligation: 'Vendor shall notify Client of upcoming renewal 30 days before the notice deadline.'",
    },

    # ── NON-COMPETE AND RESTRICTIONS ──────────────────────────────────────────
    {
        "clause_key":          "restrictions_non_compete",
        "what_it_means":       "A non-compete clause prevents the contractor from working for competitors or starting a competing business for a defined period after the contract ends. Overly broad non-competes can significantly limit earning potential.",
        "industry_standard":   "6-12 months is standard for freelance non-competes. Geographic limitations should be reasonable. Industry limitations should be narrowly defined to direct competitors only. 2+ year non-competes are aggressive.",
        "red_flags":           "Watch for: global geographic scope, very broad industry definitions, long durations (2+ years), and no compensation for the non-compete period. Non-competes are unenforceable in California and increasingly limited in other states.",
        "negotiation":         "Limit duration to 6 months, limit geography to where the client actively operates, limit scope to direct competitors in the same niche. Always ask: 'What additional compensation do you offer for this non-compete?'",
    },
    {
        "clause_key":          "restrictions_non_solicitation",
        "what_it_means":       "Non-solicitation clauses prevent the contractor from poaching the client's customers or employees after the contract ends. This is different from non-compete — it does not prevent working in the same industry.",
        "industry_standard":   "12-24 months for non-solicitation of customers is standard and generally enforceable. Non-solicitation of employees for 12 months is common. These are generally more enforceable than broad non-competes.",
        "red_flags":           "Watch for non-solicitation that covers people you already knew before the contract, or that prevents you from working with customers who approach you first.",
        "negotiation":         "Limit to customers you directly worked with during the contract, not all customers of the business. Add: 'excluding any person or entity with whom Contractor had a pre-existing relationship prior to this agreement.'",
    },
    {
        "clause_key":          "restrictions_exclusivity",
        "what_it_means":       "An exclusivity clause prevents the contractor from working with other clients, competitors, or in the same industry during the contract term. This essentially makes you a full-time employee without employee benefits.",
        "industry_standard":   "Exclusivity is unusual for freelance contracts unless the client is paying a premium retainer. If exclusivity is required, expect to be compensated at or near full-time employment rates.",
        "red_flags":           "Exclusivity at freelance rates is extremely aggressive — you are being paid part-time but prevented from earning other income. This is a major red flag.",
        "negotiation":         "Either remove exclusivity entirely or negotiate a significant rate premium. If you accept exclusivity, add: 'This exclusivity requires a minimum monthly retainer of $X regardless of hours worked.'",
    },

    # ── GOVERNING LAW ─────────────────────────────────────────────────────────
    {
        "clause_key":          "governing_law_jurisdiction",
        "what_it_means":       "The governing law clause specifies which state or country's laws apply to the contract and where disputes must be litigated. This matters enormously if you ever need to enforce the contract or defend a claim.",
        "industry_standard":   "Governing law in the client's home state is standard and usually acceptable. Requiring disputes to be litigated in a distant city or country is burdensome for the contractor.",
        "red_flags":           "Watch for: foreign jurisdiction (especially for US contractors), requiring disputes in the client's city far from yours, or mandatory arbitration in an inconvenient location.",
        "negotiation":         "If the governing law jurisdiction is inconvenient, negotiate for your own state or a neutral venue. At minimum, ensure remote participation is allowed for any proceedings.",
    },
    {
        "clause_key":          "governing_law_disputes",
        "what_it_means":       "Dispute resolution clauses specify how conflicts are resolved — through court litigation, binding arbitration, or mediation first then arbitration. Each has different costs, timelines, and outcomes.",
        "industry_standard":   "Mediation then arbitration is standard for commercial contracts. Mandatory binding arbitration with class action waiver is common but controversial. Litigation in court gives both parties more rights but costs more.",
        "red_flags":           "Watch for: mandatory arbitration in a specific city, arbitration costs borne entirely by one party, class action waivers for consumer contracts, very short statutes of limitations.",
        "negotiation":         "If mandatory arbitration is required, ensure costs are shared equally and the arbitrator selection process is neutral. Add: 'Arbitration shall be conducted remotely unless both parties agree otherwise.'",
    },

    # ── CONFIDENTIALITY ───────────────────────────────────────────────────────
    {
        "clause_key":          "confidentiality_scope",
        "what_it_means":       "The confidentiality clause defines what information must be kept secret and prevents sharing it with third parties. Overly broad definitions can prevent normal business activities like getting feedback from advisors.",
        "industry_standard":   "Standard confidentiality covers non-public business information, technical data, and client lists. Reasonable exceptions include: information already publicly known, independently developed, received from third parties, or required by law to disclose.",
        "red_flags":           "Watch for: no exceptions to confidentiality, covering information that is already public, preventing you from mentioning the client relationship in your portfolio.",
        "negotiation":         "Ensure standard exceptions are included. Add portfolio rights: 'Contractor may identify Client as a client and describe the nature of services provided in Contractor professional portfolio and marketing materials.'",
    },
    {
        "clause_key":          "confidentiality_duration",
        "what_it_means":       "The duration of confidentiality obligations determines how long after the contract ends you must keep information secret. Perpetual confidentiality means forever.",
        "industry_standard":   "2-3 years post-contract is standard for freelance and consulting agreements. Perpetual confidentiality is standard for trade secrets specifically. Perpetual confidentiality on all information is aggressive.",
        "red_flags":           "Perpetual confidentiality on general business information (not just trade secrets) is aggressive. It also makes it very difficult to ever prove you are free to discuss something.",
        "negotiation":         "Limit general confidentiality to 2-3 years. Accept perpetual confidentiality only for specifically identified trade secrets: 'Confidentiality obligations shall survive for 2 years post-termination, except for trade secrets which shall be protected indefinitely.'",
    },

    # ── NDA SPECIFIC ──────────────────────────────────────────────────────────
    {
        "clause_key":          "mutual_or_oneway",
        "what_it_means":       "A mutual NDA binds both parties equally — both must protect each other's confidential information. A one-way NDA only binds one party, typically the contractor or employee receiving information.",
        "industry_standard":   "Mutual NDAs are standard for equal business partnerships, early-stage discussions, and vendor relationships. One-way NDAs are standard when only one party is sharing sensitive information.",
        "red_flags":           "A one-way NDA where only the contractor is bound but the client can share contractor information freely is aggressive. Both parties typically share some sensitive information in any working relationship.",
        "negotiation":         "If you are sharing any sensitive information (your methods, pricing, tools, or processes), push for a mutual NDA. At minimum ensure the client's obligations to protect your information are clearly stated.",
    },

    # ── SAAS SPECIFIC ─────────────────────────────────────────────────────────
    {
        "clause_key":          "uptime_sla",
        "what_it_means":       "An uptime SLA (Service Level Agreement) guarantees a minimum percentage of time the service will be available. 99.9% uptime means about 8.7 hours of downtime per year. 99.99% means about 52 minutes per year.",
        "industry_standard":   "99.9% uptime is the standard minimum for commercial SaaS. Enterprise customers often require 99.95% or 99.99%. The SLA should specify what remedy is provided for downtime — typically service credits.",
        "red_flags":           "Watch for: no SLA at all, SLAs with no remedies for breaches, SLAs that exclude maintenance windows from uptime calculations, or remedies limited to service credits only with no right to terminate.",
        "negotiation":         "Negotiate minimum 99.9% uptime with service credits of at least 10% of monthly fees per percentage point below the SLA. Add termination right if SLA is breached for 3+ consecutive months.",
    },
    {
        "clause_key":          "data_ownership",
        "what_it_means":       "Data ownership clauses define who owns the data you put into the SaaS platform. In some contracts, by uploading data you grant the vendor broad rights to use it including for training AI models.",
        "industry_standard":   "Customer data remains the customer's property. The vendor receives a limited license to use it solely to provide the service. Vendors should not use customer data for training AI models without explicit consent.",
        "red_flags":           "Watch for: broad licenses to use your data for any purpose, rights to share data with third parties, using your data to train AI models, data surviving contract termination.",
        "negotiation":         "Add: 'Customer retains all ownership of Customer Data. Vendor receives a limited license to use Customer Data solely to provide the services. Vendor shall not use Customer Data for product improvement, AI training, or any purpose beyond service delivery without explicit written consent.'",
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# BUILD AND QUERY THE KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════════

def build_knowledge_base() -> None:
    """
    Convert all clause definitions to vectors and save as a FAISS index.
    Called once on server startup — takes about 5 seconds.
    Rebuilds automatically if the index file doesn't exist.

    What gets embedded?
    We embed a concatenation of all fields — not just the clause name.
    This means searching "who owns the work" retrieves the ip_general
    entry because its what_it_means field contains those concepts.
    """
    os.makedirs(STORE_DIR, exist_ok=True)

    # Embed a rich text representation of each entry
    # Combining all fields gives better retrieval than clause_key alone
    texts = []
    for entry in CLAUSE_KNOWLEDGE:
        combined = (
            f"Clause: {entry['clause_key']}. "
            f"{entry['what_it_means']} "
            f"{entry['industry_standard']} "
            f"{entry['red_flags']} "
            f"{entry['negotiation']}"
        )
        texts.append(combined)

    embeddings = list(get_model().embed(texts))
    embeddings = np.array(embeddings, dtype="float32")

    index = faiss.IndexFlatL2(384)
    index.add(embeddings)

    faiss.write_index(index, KB_INDEX)

    with open(KB_JSON, "w") as f:
        json.dump(CLAUSE_KNOWLEDGE, f, indent=2)

    print(f"[KB] Knowledge base built: {len(CLAUSE_KNOWLEDGE)} clause definitions indexed")


def get_knowledge(clause_key: str) -> dict | None:
    """
    Retrieve the knowledge base entry for a specific clause_key.
    Direct lookup by key — no vector search needed here since
    we know exactly which clause we're analyzing.

    Returns the full entry dict or None if not found.
    """
    for entry in CLAUSE_KNOWLEDGE:
        if entry["clause_key"] == clause_key:
            return entry
    return None


def get_knowledge_context(clause_key: str) -> str:
    """
    Format the knowledge base entry as a string for Claude's prompt.
    Returns empty string if no entry exists for this clause_key.
    """
    entry = get_knowledge(clause_key)

    if not entry:
        return ""

    return f"""
INDUSTRY KNOWLEDGE FOR THIS CLAUSE TYPE:
What it means:        {entry['what_it_means']}
Industry standard:    {entry['industry_standard']}
Red flags to watch:   {entry['red_flags']}
How to negotiate:     {entry['negotiation']}
""".strip()


def ensure_kb_built() -> None:
    """
    Called on server startup.
    Builds the knowledge base if it doesn't exist yet.
    """
    if not os.path.exists(KB_INDEX) or not os.path.exists(KB_JSON):
        print("[KB] Knowledge base not found — building now...")
        build_knowledge_base()
    else:
        print(f"[KB] Knowledge base loaded: {len(CLAUSE_KNOWLEDGE)} entries")