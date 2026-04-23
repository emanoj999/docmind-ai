from __future__ import annotations

from typing import Any, Dict, List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from backend.config import settings
from backend.vector_store import add_documents, similarity_search


def chunk_documents(documents: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
    )
    return splitter.split_documents(documents)


def ingest_documents(documents: List[Document]) -> int:
    chunks = chunk_documents(documents)

    for index, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_id"] = index

    return add_documents(settings.index_dir, chunks)


def build_context(documents: List[Document]) -> str:
    blocks = []
    for doc in documents:
        blocks.append(
            "\n".join(
                [
                    f"Source: {doc.metadata.get('source', 'unknown')}",
                    f"Page: {doc.metadata.get('page', 'n/a')}",
                    f"Chunk: {doc.metadata.get('chunk_id', 'n/a')}",
                    f"Content: {doc.page_content}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def answer_question(question: str) -> Dict[str, Any]:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    retrieved_docs = similarity_search(settings.index_dir, question, limit=4)
    if not retrieved_docs:
        return {
            "answer": "No indexed document content is available yet. Upload a PDF first.",
            "sources": [],
        }

    context = build_context(retrieved_docs)
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    prompt = f"""
You are DocMind AI, a document analysis assistant.
Answer the user's question using only the provided context.
If the answer is not supported by the context, say you could not find it in the uploaded documents.
Keep the answer concise and factual.

Question:
{question}

Context:
{context}
""".strip()

    response = llm.invoke(prompt)
    sources = [
        {
            "source": doc.metadata.get("source", "unknown"),
            "page": doc.metadata.get("page"),
            "chunk_id": doc.metadata.get("chunk_id"),
        }
        for doc in retrieved_docs
    ]
    return {
        "answer": response.content,
        "sources": sources,
    }
