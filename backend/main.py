from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.document_parser import OCRUnavailableError, parse_pdf
from backend.rag_pipeline import answer_question, ingest_documents


app = FastAPI(title="DocMind AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    source: str
    page: int | None = None
    chunk_id: int | None = None


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, str | int]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    file_path = settings.uploads_dir / Path(file.filename).name
    contents = await file.read()
    file_path.write_bytes(contents)

    try:
        parsed_documents = parse_pdf(file_path)
    except OCRUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not parsed_documents:
        raise HTTPException(
            status_code=400,
            detail=(
                "No extractable text was found in the uploaded PDF. If this is a "
                "scanned document, install OCR dependencies and try again."
            ),
        )

    chunk_count = ingest_documents(parsed_documents)
    used_ocr = any(
        document.metadata.get("extraction_method") == "ocr"
        for document in parsed_documents
    )
    return {
        "message": f"Indexed {file.filename} successfully.",
        "chunks_indexed": chunk_count,
        "used_ocr": "yes" if used_ocr else "no",
    }


@app.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = answer_question(payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AskResponse(**result)
