import { useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { uploadContract, startAnalysis } from "../lib/api.js"

const ACCEPTED = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]
const ACCEPTED_EXT = [".pdf", ".docx"]
const MAX_SIZE = 10 * 1024 * 1024 // 10MB

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function isValidFile(file) {
  const name = file.name.toLowerCase()
  const extOk = ACCEPTED_EXT.some((ext) => name.endsWith(ext))
  const typeOk = ACCEPTED.includes(file.type)
  return extOk || typeOk
}

export default function Upload() {
  const navigate = useNavigate()
  const inputRef = useRef(null)

  const [file, setFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const handleFiles = (fileList) => {
    setError("")
    const selected = fileList?.[0]
    if (!selected) return

    if (!isValidFile(selected)) {
      setError("Only PDF and DOCX files are supported.")
      return
    }
    if (selected.size > MAX_SIZE) {
      setError("File is too large. Maximum size is 10MB.")
      return
    }
    setFile(selected)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  const onAnalyze = async () => {
    if (!file || submitting) return
    setSubmitting(true)
    setError("")
    try {
      const { contract_id } = await uploadContract(file)
      const { job_id } = await startAnalysis(contract_id)
      navigate(`/report/${contract_id}?job_id=${job_id}`)
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        "Something went wrong while uploading. Please try again."
      setError(message)
      setSubmitting(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-[calc(100vh-69px)] max-w-2xl flex-col items-center justify-center px-4 py-12 sm:px-6">
      <div className="w-full text-center">
        <span className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
          <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-accent" aria-hidden="true" />
          ClauseIQ — AI Contract Analysis
        </span>
        <h1 className="mt-5 text-3xl font-bold tracking-tight text-foreground text-balance sm:text-5xl">
          Decode any contract in{" "}
          <span className="text-accent">plain English</span>
        </h1>
        <p className="mx-auto mt-4 max-w-md text-base leading-relaxed text-muted text-pretty">
          Upload a contract and get an AI-powered risk report in seconds. No legalese, no guesswork.
        </p>
      </div>

      <div className="mt-10 w-full">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          className={`flex w-full flex-col items-center justify-center rounded-2xl border-2 px-6 py-14 text-center transition-all ${
            isDragging
              ? "border-solid border-accent bg-accent/10 shadow-[0_0_40px_-8px_var(--color-accent)]"
              : "border-dashed border-border-strong bg-surface/60 hover:border-accent/60 hover:bg-surface-raised/60"
          }`}
        >
          {file ? (
            <>
              <span className="flex h-12 w-12 items-center justify-center rounded-full border border-risk-low/40 bg-risk-low/15">
                <CheckIcon className="h-6 w-6 text-risk-low" />
              </span>
              <p className="mt-3 text-sm font-semibold text-foreground break-all">{file.name}</p>
              <p className="mt-1 font-mono text-xs text-faint">{formatBytes(file.size)}</p>
              <span className="mt-3 text-xs font-medium text-accent underline-offset-2 hover:underline">
                Click to choose a different file
              </span>
            </>
          ) : (
            <>
              <span className="flex h-12 w-12 items-center justify-center rounded-full border border-border bg-surface-raised">
                <DocumentIcon className="h-6 w-6 text-accent" />
              </span>
              <p className="mt-3 text-sm font-medium text-foreground">
                Drop your contract here or click to upload
              </p>
            </>
          )}

          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </button>

        <p className="mt-3 text-center font-mono text-xs text-faint">
          Supports PDF and DOCX • Max 10MB
        </p>

        <button
          type="button"
          onClick={onAnalyze}
          disabled={!file || submitting}
          className={`mt-6 w-full rounded-xl px-6 py-3.5 text-sm font-semibold transition-all ${
            file && !submitting
              ? "bg-accent text-accent-foreground hover:bg-accent-strong hover:shadow-[0_0_30px_-6px_var(--color-accent)]"
              : "cursor-not-allowed border border-border bg-surface text-faint"
          }`}
        >
          {submitting ? "Analyzing…" : "Analyze Contract"}
        </button>

        {error && (
          <p className="mt-3 rounded-lg border border-risk-high/30 bg-risk-high/10 px-3 py-2 text-center text-sm text-risk-high">
            {error}
          </p>
        )}
      </div>
    </main>
  )
}

function DocumentIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  )
}

function CheckIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  )
}
