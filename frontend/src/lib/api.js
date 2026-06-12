import axios from "axios"

const BASE_URL = "http://localhost:8000"

const client = axios.create({
  baseURL: BASE_URL,
})

// POST /api/upload (multipart) -> { contract_id }
export const uploadContract = async (file) => {
  const formData = new FormData()
  formData.append("file", file)

  const { data } = await client.post("/api/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return data
}

// POST /api/analyze/{contractId} -> { job_id }
export const startAnalysis = async (contractId) => {
  const { data } = await client.post(`/api/analyze/${contractId}`)
  return data
}

// GET /api/status/{jobId} -> { status, progress, total, current_clause }
export const pollStatus = async (jobId) => {
  const { data } = await client.get(`/api/status/${jobId}`)
  return data
}

// GET /api/report/{contractId} -> { filename, summary, findings, ... }
export const getReport = async (contractId) => {
  const { data } = await client.get(`/api/report/${contractId}`)
  return data
}

// GET /api/contracts -> [{ contract_id, filename, analyzed_at, high_risk_count, ... }]
export const getContracts = async () => {
  const { data } = await client.get("/api/contracts")
  return data
}
