from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload, analyze, webhooks
from services.knowledge_base import ensure_kb_built

app = FastAPI(title="Contract AI — Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router,   prefix="/api")
app.include_router(analyze.router,  prefix="/api")
app.include_router(webhooks.router, prefix="/api")


@app.on_event("startup")
def startup():
    """Build knowledge base index on server startup if not already built."""
    ensure_kb_built()


@app.get("/")
def health():
    return {"status": "ok", "service": "contract-ai-backend"}