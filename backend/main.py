from dotenv import load_dotenv
load_dotenv()  # loads .env into os.environ before anything else

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload, analyze, webhooks

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


@app.get("/")
def health():
    return {"status": "ok", "service": "contract-ai-backend"}