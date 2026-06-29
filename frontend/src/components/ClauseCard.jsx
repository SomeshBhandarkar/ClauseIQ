import { useState } from "react"
import RiskBadge from "./RiskBadge.jsx"

// "ip_general" -> "IP Ownership", generic snake_case -> Title Case with IP uppercased
function toTitleCase(key = "") {
  return key
    .split("_")
    .map((word) => {
      if (word.toLowerCase() === "ip") return "IP"
      return word.charAt(0).toUpperCase() + word.slice(1)
    })
    .join(" ")
}

export default function ClauseCard({ finding }) {
  const [showEvidence, setShowEvidence] = useState(false)

  const {
    clause_key,
    found,
    evidence,
    confidence,
    risk = "none",
    plain_english,
    negotiation_tip,
  } = finding || {}

  const title = toTitleCase(clause_key)

  return (
    <div className="rounded-xl border border-border bg-surface-raised/60 p-4 transition-colors hover:border-border-strong">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-4">
        <div className="shrink-0">
          <RiskBadge risk={found ? risk : "none"} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-foreground">{title}</h4>
            {typeof confidence === "number" && (
              <span className="shrink-0 font-mono text-xs text-faint">
                {Math.round(confidence * 100)}% conf
              </span>
            )}
          </div>

          {plain_english && (
            <p className="mt-1 text-sm leading-relaxed text-muted">{plain_english}</p>
          )}

          {negotiation_tip && (risk === "high" || risk === "medium") && (
            <div className="mt-2 flex gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2">
              <span className="shrink-0 text-sm">💡</span>
              <p className="text-xs leading-relaxed text-blue-300">{negotiation_tip}</p>
            </div>
          )}

          {found ? (
            <div className="mt-3">
              <button
                type="button"
                onClick={() => setShowEvidence((prev) => !prev)}
                className="text-xs font-medium text-accent underline-offset-2 hover:underline"
              >
                {showEvidence ? "Hide Evidence" : "View Evidence"}
              </button>

              {showEvidence && (
                <pre className="mt-2 overflow-x-auto rounded-lg border border-border bg-background/80 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap text-muted">
                  {evidence || "No evidence text provided."}
                </pre>
              )}
            </div>
          ) : (
            <p className="mt-2 text-sm italic text-faint">Not found in contract</p>
          )}
        </div>
      </div>
    </div>
  )
}
