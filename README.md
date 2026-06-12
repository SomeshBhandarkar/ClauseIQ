# Contract AI

AI-powered contract intelligence for freelancers and small businesses.
Upload a contract → get a plain English risk report in seconds.

---

## Project structure

```
contract-ai/
├── backend/                    ← FastAPI (Python)
│   ├── main.py                 ← app entry point
│   ├── routers/
│   │   ├── upload.py           ← POST /api/upload
│   │   ├── analyze.py          ← POST /api/analyze · GET /api/report
│   │   └── webhooks.py         ← Stripe webhooks
│   ├── services/
│   │   ├── extractor.py        ← pdfplumber + python-docx
│   │   ├── chunker.py          ← split text into RAG chunks
│   │   ├── embedder.py         ← sentence-transformers → FAISS
│   │   ├── retriever.py        ← FAISS similarity search
│   │   └── analyzer.py         ← Claude API + grounded prompt
│   ├── models/
│   │   └── schemas.py          ← Pydantic request/response models
│   └── requirements.txt
│
├── frontend/                   ← React + Vite + Tailwind
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Upload.jsx      ← drag and drop contract
│   │   │   ├── Report.jsx      ← risk report display
│   │   │   └── Dashboard.jsx   ← all contracts + renewals
│   │   ├── components/
│   │   │   ├── RiskBadge.jsx
│   │   │   ├── ClauseCard.jsx
│   │   │   └── Navbar.jsx
│   │   └── lib/
│   │       └── supabase.js     ← Supabase client
│   └── package.json
│
└── README.md
```

---

## Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Add environment variables
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET

# Run the server
uvicorn main:app --reload --port 8000
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/upload | Upload PDF or DOCX → returns contract_id |
| POST | /api/analyze/{contract_id} | Run RAG + Claude analysis → risk report |
| GET  | /api/report/{contract_id} | Fetch a saved report |
| POST | /api/webhook | Stripe subscription events |

---

## Frontend setup

```bash
cd frontend
npm install
npm run dev     # runs on http://localhost:5173
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python |
| Text extraction | pdfplumber + python-docx |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector store | FAISS (prototype) → pgvector/Supabase (production) |
| AI analysis | Claude API (claude-sonnet-4-20250514) |
| Frontend | React + Vite + Tailwind |
| Auth | Supabase Auth |
| Payments | Stripe |
| Deploy | Vercel (frontend) + Railway (backend) |