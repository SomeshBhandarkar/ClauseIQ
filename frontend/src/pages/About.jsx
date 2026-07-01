export default function About() {
  return (
    <main className="mx-auto flex min-h-[calc(100vh-69px)] max-w-2xl flex-col items-center justify-center px-4 py-12 text-center sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight text-foreground">
        About <span className="text-accent">ClauseIQ</span>
      </h1>
      <p className="mx-auto mt-4 max-w-md text-base leading-relaxed text-muted">
        ClauseIQ analyzes contracts with AI, flagging risky clauses and explaining them in plain English.
      </p>
    </main>
  )
}
