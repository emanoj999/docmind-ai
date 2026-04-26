from __future__ import annotations

import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import settings
from backend.document_parser import OCRUnavailableError, parse_pdf
from backend.rag_pipeline import (
    answer_question,
    compare_documents,
    delete_indexed_document,
    ingest_documents,
    list_indexed_documents,
    stream_answer,
    stream_compare_documents,
)


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
    citation_id: int
    source: str
    page: int | None = None
    chunk_id: int | None = None
    snippet: str


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]


class DocumentItem(BaseModel):
    source: str
    page_count: int
    chunk_count: int
    used_ocr: bool


class CompareRequest(BaseModel):
    sources: List[str]
    question: str | None = None


class DeleteDocumentResponse(BaseModel):
    message: str
    chunks_deleted: int
    file_deleted: bool


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/documents", response_model=List[DocumentItem])
def get_documents() -> List[DocumentItem]:
    try:
        documents = list_indexed_documents()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [DocumentItem(**document) for document in documents]


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


@app.delete("/documents/{source}", response_model=DeleteDocumentResponse)
def delete_document(source: str) -> DeleteDocumentResponse:
    safe_source = Path(source).name
    if not safe_source:
        raise HTTPException(status_code=400, detail="Missing document source.")

    try:
        chunks_deleted = delete_indexed_document(safe_source)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    file_path = settings.uploads_dir / safe_source
    file_deleted = False
    if file_path.exists():
        file_path.unlink()
        file_deleted = True

    if chunks_deleted == 0 and not file_deleted:
        raise HTTPException(status_code=404, detail="Document was not found.")

    return DeleteDocumentResponse(
        message=f"Deleted {safe_source}.",
        chunks_deleted=chunks_deleted,
        file_deleted=file_deleted,
    )


@app.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = answer_question(payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AskResponse(**result)


@app.post("/ask/stream")
def ask_question_stream(payload: AskRequest) -> StreamingResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    def events():
        try:
            for event in stream_answer(payload.question):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/compare", response_model=AskResponse)
def compare_selected_documents(payload: CompareRequest) -> AskResponse:
    try:
        result = compare_documents(payload.sources, payload.question)
    except ValueError as exc:
        status_code = 500 if "OPENAI_API_KEY" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return AskResponse(**result)


@app.post("/compare/stream")
def compare_selected_documents_stream(payload: CompareRequest) -> StreamingResponse:
    selected_sources = [source for source in payload.sources if source.strip()]
    if len(selected_sources) < 2:
        raise HTTPException(
            status_code=400,
            detail="Choose at least two indexed documents to compare.",
        )

    def events():
        try:
            for event in stream_compare_documents(payload.sources, payload.question):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
