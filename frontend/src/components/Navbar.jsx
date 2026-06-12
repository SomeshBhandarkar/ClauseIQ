import { Link, useLocation } from "react-router-dom"

export default function Navbar() {
  const { pathname } = useLocation()

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/70 backdrop-blur-xl">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link to="/" className="group flex items-center gap-2.5 text-lg font-bold tracking-tight">
          <span className="relative flex h-8 w-8 items-center justify-center rounded-lg border border-accent/40 bg-accent/10 text-sm font-bold text-accent shadow-[0_0_18px_-4px_var(--color-accent)]">
            CA
            <span className="absolute inset-0 rounded-lg ring-1 ring-inset ring-accent/20" aria-hidden="true" />
          </span>
          <span className="text-foreground">
            Contract<span className="text-accent">AI</span>
          </span>
        </Link>

        <div className="flex items-center gap-2 sm:gap-4">
          <Link
            to="/dashboard"
            className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              pathname === "/dashboard"
                ? "text-accent"
                : "text-muted hover:text-foreground"
            }`}
          >
            Dashboard
          </Link>
          <Link
            to="/"
            className="rounded-lg border border-accent/40 bg-accent/10 px-4 py-2 text-sm font-semibold text-accent transition-all hover:bg-accent hover:text-accent-foreground hover:shadow-[0_0_22px_-4px_var(--color-accent)]"
          >
            Upload Contract
          </Link>
        </div>
      </nav>
    </header>
  )
}
