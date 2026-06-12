import os
import json
import uuid
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.extractor import extract_text, clean_text
from services.chunker import chunk_text
from services.embedder import embed_and_store
from models.schemas import UploadResponse

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_contract(file: UploadFile = File(...)):
    """
    POST /api/upload
    Accepts a PDF or DOCX file.
    Pipeline: save → extract text → clean → chunk → embed into FAISS
    Returns contract_id for the frontend to trigger analysis.
    """
    allowed = {".pdf", ".docx", ".doc"}
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload a PDF or DOCX."
        )

    contract_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{contract_id}{ext}")

    # Save file to disk
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        raw_text = extract_text(file_path)
        clean = clean_text(raw_text)
        chunks = chunk_text(clean, chunk_size=500, overlap=50)

        if not chunks:
            raise ValueError("No content could be extracted from this file.")

        embed_and_store(contract_id, chunks)

        meta = {"filename": file.filename, "uploaded_at": datetime.now(timezone.utc).isoformat()}
        with open(os.path.join(UPLOAD_DIR, f"{contract_id}.meta.json"), "w") as mf:
            json.dump(meta, mf)

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=422, detail=str(e))

    return UploadResponse(
        contract_id=contract_id,
        filename=file.filename,
        chunk_count=len(chunks),
        message="File processed and ready for analysis.",
    )