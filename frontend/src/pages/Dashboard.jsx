import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { getContracts } from "../lib/api.js"

function formatDate(isoString) {
  if (!isoString) return "—"
  try {
    return new Date(isoString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  } catch {
    return isoString
  }
}

export default function Dashboard() {
  const [contracts, setContracts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    getContracts()
      .then(setContracts)
      .catch(() => setError("Could not load contracts. Is the backend running?"))
      .finally(() => setLoading(false))
  }, [])

  return (
    <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight text-foreground">Your Contracts</h1>
      <p className="mt-1 text-sm text-muted">Review past analyses and reopen their reports.</p>

      <div className="mt-6 overflow-hidden rounded-2xl border border-border bg-surface/70">
        {loading ? (
          <p className="px-4 py-10 text-center text-sm text-muted">Loading…</p>
        ) : error ? (
          <p className="px-4 py-10 text-center text-sm text-risk-high">{error}</p>
        ) : contracts.length === 0 ? (
          <p className="px-4 py-10 text-center text-sm text-muted">
            No contracts analyzed yet.{" "}
            <Link to="/" className="text-accent underline-offset-2 hover:underline">
              Upload one now.
            </Link>
          </p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-raised/50 text-xs uppercase tracking-wide text-faint">
              <tr>
                <th className="px-4 py-3 font-medium">Filename</th>
                <th className="px-4 py-3 font-medium">Date Analyzed</th>
                <th className="px-4 py-3 font-medium">High Risk</th>
                <th className="px-4 py-3 font-medium">Medium Risk</th>
                <th className="px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {contracts.map((c) => (
                <tr key={c.contract_id} className="transition-colors hover:bg-surface-raised/40">
                  <td className="px-4 py-3 font-medium text-foreground">{c.filename}</td>
                  <td className="px-4 py-3 font-mono text-muted">{formatDate(c.analyzed_at)}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex min-w-7 justify-center rounded-md border border-risk-high/40 bg-risk-high/15 px-2 py-0.5 font-mono text-xs font-semibold text-risk-high">
                      {c.high_risk_count}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex min-w-7 justify-center rounded-md border border-risk-medium/40 bg-risk-medium/15 px-2 py-0.5 font-mono text-xs font-semibold text-risk-medium">
                      {c.medium_risk_count}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/report/${c.contract_id}`}
                      className="text-sm font-medium text-accent underline-offset-2 hover:underline"
                    >
                      View Report
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  )
}
