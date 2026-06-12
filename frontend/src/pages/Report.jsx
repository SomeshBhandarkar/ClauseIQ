import { useEffect, useRef, useState } from "react"
import { useParams, useSearchParams, Link } from "react-router-dom"
import { pollStatus, getReport } from "../lib/api.js"
import RiskBadge from "../components/RiskBadge.jsx"
import ClauseCard from "../components/ClauseCard.jsx"

const CATEGORIES = [
  { key: "ip_ownership", label: "IP Ownership" },
  { key: "liability", label: "Liability" },
  { key: "payment_terms", label: "Payment Terms" },
  { key: "termination", label: "Termination" },
  { key: "auto_renewal", label: "Auto-Renewal" },
  { key: "restrictions", label: "Restrictions" },
  { key: "governing_law", label: "Governing Law" },
  { key: "confidentiality", label: "Confidentiality" },
]

const RISK_RANK = { high: 3, medium: 2, low: 1, none: 0 }
const DOT_COLOR = {
  high: "bg-risk-high shadow-[0_0_8px_var(--color-risk-high)]",
  medium: "bg-risk-medium shadow-[0_0_8px_var(--color-risk-medium)]",
  low: "bg-risk-low shadow-[0_0_8px_var(--color-risk-low)]",
  none: "bg-faint",
}

function worstRisk(findings) {
  return findings.reduce((worst, f) => {
    const r = f.found ? f.risk || "none" : "none"
    return (RISK_RANK[r] || 0) > (RISK_RANK[worst] || 0) ? r : worst
  }, "none")
}

export default function Report() {
  const { contractId } = useParams()
  const [searchParams] = useSearchParams()
  const jobId = searchParams.get("job_id")

  const [status, setStatus] = useState("processing")
  const [progress, setProgress] = useState(0)
  const [total, setTotal] = useState(0)
  const [currentClause, setCurrentClause] = useState("")
  const [report, setReport] = useState(null)
  const [error, setError] = useState("")

  const timerRef = useRef(null)

  useEffect(() => {
    if (!jobId) {
      setError("Missing job reference. Please upload your contract again.")
      setStatus("error")
      return
    }

    let cancelled = false

    const tick = async () => {
      try {
        const data = await pollStatus(jobId)
        if (cancelled) return

        setProgress(data.progress ?? 0)
        setTotal(data.total ?? 0)
        setCurrentClause(data.current_clause ?? "")

        if (data.status === "done") {
          setStatus("done")
          const reportData = await getReport(contractId)
          if (!cancelled) setReport(reportData)
          return
        }
        if (data.status === "error") {
          setStatus("error")
          setError(data.message || "Analysis failed. Please try again.")
          return
        }
        timerRef.current = setTimeout(tick, 2000)
      } catch (err) {
        if (cancelled) return
        setStatus("error")
        setError(
          err?.response?.data?.detail || err?.message || "Unable to reach the analysis service.",
        )
      }
    }

    tick()
    return () => {
      cancelled = true
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [jobId, contractId])

  if (status === "error") {
    return (
      <main className="mx-auto flex min-h-[calc(100vh-69px)] max-w-xl flex-col items-center justify-center px-4 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full border border-risk-high/40 bg-risk-high/15">
          <span className="text-2xl font-bold text-risk-high">!</span>
        </div>
        <h1 className="mt-5 text-xl font-semibold text-foreground">Analysis failed</h1>
        <p className="mt-2 text-sm text-muted">{error}</p>
        <Link
          to="/"
          className="mt-6 rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-accent-foreground transition-all hover:bg-accent-strong hover:shadow-[0_0_30px_-6px_var(--color-accent)]"
        >
          Upload another contract
        </Link>
      </main>
    )
  }

  if (status !== "done" || !report) {
    const pct = total > 0 ? Math.round((progress / total) * 100) : 0
    return (
      <main className="mx-auto flex min-h-[calc(100vh-69px)] max-w-xl flex-col items-center justify-center px-4 text-center">
        <div className="relative flex h-16 w-16 items-center justify-center">
          <span className="absolute inset-0 animate-pulse-glow rounded-full border border-accent/40 bg-accent/10" aria-hidden="true" />
          <ScanIcon className="h-7 w-7 text-accent" />
        </div>
        <h1 className="mt-5 text-xl font-semibold text-foreground">Analyzing your contract</h1>
        <p className="mt-2 text-sm text-muted">
          Our AI is reading every clause. This usually takes under a minute.
        </p>

        <div className="mt-8 w-full">
          <div className="relative h-2.5 w-full overflow-hidden rounded-full border border-border bg-surface">
            <div
              className="animate-shimmer relative h-full rounded-full bg-accent transition-all duration-500 ease-out"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="mt-3 text-sm text-muted">
            {currentClause || "Preparing analysis…"}
            {total > 0 && (
              <span className="ml-1 font-mono font-medium text-faint">
                {progress} / {total}
              </span>
            )}
          </p>
        </div>
      </main>
    )
  }

  return <ReportView report={report} />
}

function ReportView({ report }) {
  const findings = report.findings || []

  // Group findings into the 8 fixed categories. A finding is matched by its
  // `category` field, falling back to a prefix match on `clause_key`.
  const sections = CATEGORIES.map((cat) => {
    const prefix = cat.key.split("_")[0]
    const items = findings.filter((f) => {
      if (f.category) return f.category === cat.key
      return (f.clause_key || "").startsWith(prefix)
    })
    return { ...cat, items }
  })

  return (
    <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      {/* Summary card */}
      <section className="relative overflow-hidden rounded-2xl border border-border bg-surface/70 p-6">
        <div className="absolute -top-px left-6 right-6 h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent" aria-hidden="true" />
        <h1 className="text-2xl font-bold tracking-tight text-foreground text-balance">
          {report.filename || "Contract Analysis"}
        </h1>

        <div className="mt-5 flex flex-wrap gap-3">
          <StatBadge
            count={report.high_risk_count ?? 0}
            label="High Risk"
            className="border-risk-high/40 bg-risk-high/15 text-risk-high"
          />
          <StatBadge
            count={report.medium_risk_count ?? 0}
            label="Medium Risk"
            className="border-risk-medium/40 bg-risk-medium/15 text-risk-medium"
          />
          <StatBadge
            count={report.missing_count ?? 0}
            label="Missing Clauses"
            className="border-border bg-surface-raised text-muted"
          />
        </div>

        {report.summary && (
          <p className="mt-5 text-sm leading-relaxed text-muted text-pretty">
            {report.summary}
          </p>
        )}
      </section>

      {/* Findings by category */}
      <section className="mt-8 space-y-3">
        {sections.map((section) => (
          <CategorySection key={section.key} label={section.label} items={section.items} />
        ))}
      </section>

      {/* Disclaimer */}
      <p className="mt-10 text-xs leading-relaxed text-faint">
        This analysis is AI-generated for informational purposes only. It is not legal advice. For
        legally binding decisions, consult a qualified attorney.
      </p>
    </main>
  )
}

function StatBadge({ count, label, className }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-semibold ${className}`}>
      <span className="font-mono text-base font-bold">{count}</span>
      {label}
    </span>
  )
}

function CategorySection({ label, items }) {
  const [open, setOpen] = useState(false)
  const risk = worstRisk(items)

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface/70 transition-colors hover:border-border-strong">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left transition-colors hover:bg-surface-raised/50"
      >
        <span className="flex items-center gap-3">
          <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${DOT_COLOR[risk]}`} aria-hidden="true" />
          <span className="text-sm font-semibold text-foreground">{label}</span>
          <span className="font-mono text-xs text-faint">
            {items.length} {items.length === 1 ? "finding" : "findings"}
          </span>
        </span>
        <ChevronIcon className={`h-5 w-5 text-faint transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="space-y-3 border-t border-border bg-background/40 px-5 py-4">
          {items.length > 0 ? (
            items.map((finding, i) => <ClauseCard key={finding.clause_key || i} finding={finding} />)
          ) : (
            <p className="text-sm italic text-faint">No findings in this category.</p>
          )}
        </div>
      )}
    </div>
  )
}

function ScanIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 4.5v3m0-3h3m-3 0L7.5 8.25M20.25 4.5v3m0-3h-3m3 0L16.5 8.25M3.75 19.5v-3m0 3h3m-3 0L7.5 15.75M20.25 19.5v-3m0 3h-3m3 0L16.5 15.75M3 12h18" />
    </svg>
  )
}

function ChevronIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  )
}
