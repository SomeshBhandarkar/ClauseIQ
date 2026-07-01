import { useEffect, useState } from "react"
import { Navigate, useNavigate } from "react-router-dom"
import { supabase } from "../lib/supabase.js"
import { useAuth } from "../context/AuthContext.jsx"

export default function Login() {
  const navigate = useNavigate()
  const { session } = useAuth()

  const [tab, setTab] = useState("signin")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setError("")
  }, [tab])

  if (session) {
    return <Navigate to="/upload" replace />
  }

  const onSignIn = async (e) => {
    e.preventDefault()
    if (submitting) return
    setError("")
    setSubmitting(true)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    setSubmitting(false)
    if (error) {
      setError(error.message)
      return
    }
    navigate("/upload")
  }

  const onSignUp = async (e) => {
    e.preventDefault()
    if (submitting) return
    setError("")

    if (password !== confirmPassword) {
      setError("Passwords do not match")
      return
    }

    setSubmitting(true)
    const { error } = await supabase.auth.signUp({ email, password })
    setSubmitting(false)
    if (error) {
      setError(error.message)
      return
    }
    navigate("/upload")
  }

  const onGoogle = async () => {
    setError("")
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin + "/upload" },
    })
    if (error) setError(error.message)
  }

  return (
    <main className="mx-auto flex min-h-[calc(100vh-69px)] max-w-md flex-col items-center justify-center px-4 py-12 sm:px-6">
      <div className="w-full text-center">
        <span className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
          <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-accent" aria-hidden="true" />
          ClauseIQ
        </span>
        <h1 className="mt-5 text-3xl font-bold tracking-tight text-foreground text-balance">
          {tab === "signin" ? "Welcome back" : "Create your account"}
        </h1>
        <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-muted text-pretty">
          {tab === "signin"
            ? "Sign in to view your contract analyses."
            : "Sign up to start analyzing your contracts."}
        </p>
      </div>

      <div className="mt-10 w-full rounded-2xl border border-border bg-surface/60 p-6 sm:p-8">
        <div className="mb-6 flex rounded-lg border border-border-strong bg-surface-raised/60 p-1">
          <button
            type="button"
            onClick={() => setTab("signin")}
            className={`flex-1 rounded-md py-2 text-sm font-semibold transition-colors ${
              tab === "signin" ? "bg-accent text-accent-foreground" : "text-muted hover:text-foreground"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => setTab("signup")}
            className={`flex-1 rounded-md py-2 text-sm font-semibold transition-colors ${
              tab === "signup" ? "bg-accent text-accent-foreground" : "text-muted hover:text-foreground"
            }`}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={tab === "signin" ? onSignIn : onSignUp} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-left">
            <span className="text-xs font-medium text-muted">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="you@company.com"
              className="rounded-lg border border-border-strong bg-surface-raised/60 px-3.5 py-2.5 text-sm text-foreground placeholder:text-faint outline-none transition-colors focus:border-accent/60 focus:ring-2 focus:ring-accent/20"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-left">
            <span className="text-xs font-medium text-muted">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={tab === "signin" ? "current-password" : "new-password"}
              placeholder="••••••••"
              className="rounded-lg border border-border-strong bg-surface-raised/60 px-3.5 py-2.5 text-sm text-foreground placeholder:text-faint outline-none transition-colors focus:border-accent/60 focus:ring-2 focus:ring-accent/20"
            />
          </label>

          {tab === "signup" && (
            <label className="flex flex-col gap-1.5 text-left">
              <span className="text-xs font-medium text-muted">Confirm password</span>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                placeholder="••••••••"
                className="rounded-lg border border-border-strong bg-surface-raised/60 px-3.5 py-2.5 text-sm text-foreground placeholder:text-faint outline-none transition-colors focus:border-accent/60 focus:ring-2 focus:ring-accent/20"
              />
            </label>
          )}

          <button
            type="submit"
            disabled={submitting}
            className={`mt-2 w-full rounded-xl px-6 py-3 text-sm font-semibold transition-all ${
              !submitting
                ? "bg-accent text-accent-foreground hover:bg-accent-strong hover:shadow-[0_0_30px_-6px_var(--color-accent)]"
                : "cursor-not-allowed border border-border bg-surface text-faint"
            }`}
          >
            {submitting
              ? tab === "signin" ? "Signing in…" : "Creating account…"
              : tab === "signin" ? "Sign In" : "Create Account"}
          </button>

          {error && (
            <p className="rounded-lg border border-risk-high/30 bg-risk-high/10 px-3 py-2 text-center text-sm text-risk-high">
              {error}
            </p>
          )}
        </form>

        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs text-faint">or</span>
          <div className="h-px flex-1 bg-border" />
        </div>

        <button
          type="button"
          onClick={onGoogle}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-border-strong bg-surface-raised/60 px-6 py-3 text-sm font-semibold text-foreground transition-colors hover:bg-surface-raised"
        >
          <GoogleIcon className="h-4 w-4" />
          Continue with Google
        </button>
      </div>
    </main>
  )
}

function GoogleIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24z" />
      <path fill="#FBBC05" d="M5.27 14.28A7.2 7.2 0 0 1 4.87 12c0-.79.14-1.56.4-2.28V6.63H1.29A11.98 11.98 0 0 0 0 12c0 1.93.46 3.76 1.29 5.37l3.98-3.09z" />
      <path fill="#EA4335" d="M12 4.76c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.94 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.63l3.98 3.09C6.22 6.87 8.87 4.76 12 4.76z" />
    </svg>
  )
}
