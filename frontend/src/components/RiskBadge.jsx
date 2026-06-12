const STYLES = {
  high: {
    className: "border-risk-high/40 bg-risk-high/15 text-risk-high",
    label: "High Risk",
  },
  medium: {
    className: "border-risk-medium/40 bg-risk-medium/15 text-risk-medium",
    label: "Medium Risk",
  },
  low: {
    className: "border-risk-low/40 bg-risk-low/15 text-risk-low",
    label: "Low Risk",
  },
  none: {
    className: "border-border bg-surface-raised text-faint",
    label: "Not Found",
  },
}

export default function RiskBadge({ risk }) {
  const config = STYLES[risk] || STYLES.none

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold whitespace-nowrap ${config.className}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {config.label}
    </span>
  )
}
