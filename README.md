# ClauseIQ

AI-powered contract intelligence for freelancers and small businesses.
Upload a contract → get a plain-English risk report in seconds, grounded in
industry-standard clause knowledge.

**Live app:** https://clause-f8gepw1ha-phantomphoenix1544-2099s-projects.vercel.app/

---

## What it does

ClauseIQ runs every uploaded contract through a 3-stage hybrid RAG pipeline
across **25 targeted clause checks** — IP ownership, liability, payment terms,
termination, auto-renewal, restrictive covenants, governing law, and
confidentiality. Each finding is backed by:

- **Evidence** — the exact contract text the finding is based on
- **Risk level** — high / medium / low / not found
- **Plain-English explanation** — what the clause means and why it matters
- **Industry-standard comparison** — pulled from a built-in clause knowledge base
- **Negotiation tips** — concrete language to counter-propose

Users can sign in (email/password or Google), see their contract history on a
dashboard, and revisit past reports at any time.

---

## Project structure

```
SMB_app/
├── backend/                          ← FastAPI (Python)
│   ├── main.py                       ← app entry point
│   ├── routers/
│   │   ├── upload.py                 ← POST /api/upload
│   │   ├── analyze.py                ← POST /api/analyze, GET /api/status, GET /api/report
│   │   ├── contracts.py              ← GET /api/contracts
│   │   └── webhooks.py               ← Stripe webhooks (stubbed)
│   ├── services/
│   │   ├── extractor.py              ← pdfplumber + python-docx text extraction
│   │   ├── chunker.py                ← sentence-aware overlapping chunker
│   │   ├── embedder.py               ← fastembed → FAISS index
│   │   ├── retriever.py              ← FAISS + BM25 + RRF + Cohere rerank
│   │   ├── analyzer.py               ← 25 clause checks via Claude
│   │   ├── knowledge_base.py         ← industry-standard clause reference data
│   │   └── database.py               ← Supabase persistence (jobs + contracts)
│   ├── models/
│   │   └── schemas.py                ← Pydantic request/response models
│   └── requirements.txt
│
├── frontend/                         ← React + Vite + Tailwind
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Upload.jsx            ← drag-and-drop contract upload
│   │   │   ├── Report.jsx            ← polling + full risk report
│   │   │   ├── Dashboard.jsx         ← table of past analyses
│   │   │   ├── Login.jsx             ← Supabase auth (email/password + Google)
│   │   │   └── About.jsx
│   │   ├── components/
│   │   │   ├── RiskBadge.jsx
│   │   │   ├── ClauseCard.jsx
│   │   │   ├── Navbar.jsx
│   │   │   └── InteractiveBackground.jsx
│   │   └── lib/
│   │       ├── api.js                ← backend API calls (axios)
│   │       └── supabase.js           ← Supabase client
│   └── package.json
│
└── README.md
```

---

## How analysis works (RAG pipeline)

Every contract is analyzed 25 times — once per clause type — using a 3-stage
hybrid retrieval pipeline before each Claude call:

1. **FAISS semantic search** — embeds the query with `fastembed`
   (`BAAI/bge-small-en-v1.5`, 384-dim) and finds the top 10 nearest chunks.
2. **BM25 keyword search** — finds the top 10 chunks by exact keyword match,
   catching terms embeddings might miss.
3. **Reciprocal Rank Fusion** — merges both ranked lists (`score = 1/(60+rank)`),
   so chunks appearing in both lists outrank chunks appearing in only one.
4. **Cohere Rerank** (`rerank-english-v3.0`) — reads the merged chunks +
   query together and keeps the top 5 most relevant, with a graceful
   fallback to RRF order if Cohere is unavailable.

Claude (`claude-sonnet-4-5`) then answers strictly from those top 5 chunks,
returning a structured finding per clause.

---

## Backend setup

```bash
cd backend
python -m venv venv
source ../venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Add environment variables in backend/.env
# ANTHROPIC_API_KEY, COHERE_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY

uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload PDF/DOCX → extract, chunk, embed → returns `contract_id` |
| POST | `/api/analyze/{contract_id}` | Start async analysis → returns `job_id` |
| GET | `/api/status/{job_id}` | Poll analysis progress |
| GET | `/api/report/{contract_id}` | Fetch a saved report |
| GET | `/api/contracts` | List all past analyses |
| POST | `/api/webhook` | Stripe subscription events (stubbed, not enforced yet) |

---

## Frontend setup

```bash
cd frontend
npm install
npm run dev     # runs on http://localhost:3000
```

Frontend env vars (`frontend/.env`): `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python |
| Text extraction | pdfplumber + python-docx |
| Embeddings | fastembed (`BAAI/bge-small-en-v1.5`) — no PyTorch, fits low-memory hosting |
| Vector search | FAISS (`IndexFlatL2`) |
| Keyword search | BM25 (`rank_bm25`) |
| Reranking | Cohere (`rerank-english-v3.0`) |
| AI analysis | Claude API (`claude-sonnet-4-5`) |
| Persistence | Supabase (Postgres) — jobs + contracts tables |
| Auth | Supabase Auth (email/password + Google OAuth) |
| Frontend | React + Vite + Tailwind CSS |
| Payments | Stripe (webhook wired, gating not enforced yet) |
| Deploy | Vercel (frontend) + Render (backend) |
