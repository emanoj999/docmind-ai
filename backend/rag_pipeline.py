from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from backend.config import settings
from backend.vector_store import (
    add_documents,
    delete_source,
    list_sources,
    similarity_search,
)


QUESTION_CONTEXT_LIMIT = 4
COMPARE_CHUNKS_PER_SOURCE = 4
MAX_SNIPPET_LENGTH = 420


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
    for index, doc in enumerate(documents, start=1):
        blocks.append(
            "\n".join(
                [
                    f"Evidence: [{index}]",
                    f"Source: {doc.metadata.get('source', 'unknown')}",
                    f"Page: {doc.metadata.get('page', 'n/a')}",
                    f"Chunk: {doc.metadata.get('chunk_id', 'n/a')}",
                    f"Content: {doc.page_content}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _build_snippet(text: str, max_length: int = MAX_SNIPPET_LENGTH) -> str:
    snippet = _clean_text(text)
    if len(snippet) <= max_length:
        return snippet

    shortened = snippet[: max_length + 1].rsplit(" ", 1)[0].strip()
    return f"{shortened}..."


def _message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def _format_sources(documents: List[Document]) -> List[dict[str, Any]]:
    return [
        {
            "citation_id": index,
            "source": doc.metadata.get("source", "unknown"),
            "page": doc.metadata.get("page"),
            "chunk_id": doc.metadata.get("chunk_id"),
            "snippet": _build_snippet(doc.page_content),
        }
        for index, doc in enumerate(documents, start=1)
    ]


def _build_question_prompt(question: str, documents: List[Document]) -> str:
    context = build_context(documents)
    return f"""
You are DocMind AI, a document analysis assistant.
Answer the user's question using only the provided evidence.
If the answer is not supported by the evidence, say you could not find it in the uploaded documents.
When you use a fact from the evidence, cite it with the evidence number in square brackets, such as [1].
Keep the answer concise and factual.

Question:
{question}

Evidence:
{context}
""".strip()


def _build_compare_prompt(question: str, documents: List[Document]) -> str:
    context = build_context(documents)
    return f"""
You are DocMind AI, a document comparison assistant.
Compare the selected documents using only the provided evidence.
Call out important similarities, differences, contradictions, and missing information.
When you use a fact from the evidence, cite it with the evidence number in square brackets, such as [1].
If the evidence is insufficient for part of the comparison, say what is missing.

Comparison request:
{question}

Evidence:
{context}
""".strip()


def _build_llm() -> ChatOpenAI:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


def list_indexed_documents() -> List[dict[str, object]]:
    return list_sources(settings.index_dir)


def delete_indexed_document(source: str) -> int:
    return delete_source(settings.index_dir, source)


def _retrieve_question_documents(question: str) -> List[Document]:
    return similarity_search(
        settings.index_dir,
        question,
        limit=QUESTION_CONTEXT_LIMIT,
    )


def answer_question(question: str) -> Dict[str, Any]:
    llm = _build_llm()
    retrieved_docs = _retrieve_question_documents(question)
    if not retrieved_docs:
        return {
            "answer": "No indexed document content is available yet. Upload a PDF first.",
            "sources": [],
        }

    prompt = _build_question_prompt(question, retrieved_docs)
    response = llm.invoke(prompt)
    return {
        "answer": _message_content_to_text(response.content),
        "sources": _format_sources(retrieved_docs),
    }


def stream_answer(question: str) -> Iterator[dict[str, Any]]:
    llm = _build_llm()
    retrieved_docs = _retrieve_question_documents(question)
    sources = _format_sources(retrieved_docs)
    yield {"type": "sources", "sources": sources}

    if not retrieved_docs:
        yield {
            "type": "token",
            "content": "No indexed document content is available yet. Upload a PDF first.",
        }
        yield {"type": "done"}
        return

    prompt = _build_question_prompt(question, retrieved_docs)
    for chunk in llm.stream(prompt):
        content = _message_content_to_text(chunk.content)
        if content:
            yield {"type": "token", "content": content}

    yield {"type": "done"}


def _dedupe_documents(documents: Iterable[Document]) -> List[Document]:
    seen: set[tuple[object, object, object]] = set()
    deduped = []
    for document in documents:
        key = (
            document.metadata.get("source"),
            document.metadata.get("page"),
            document.metadata.get("chunk_id"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(document)
    return deduped


def _prepare_comparison(
    sources: List[str],
    question: str | None = None,
) -> tuple[str, List[Document]]:
    requested_sources = [source for source in sources if source.strip()]
    if len(requested_sources) < 2:
        raise ValueError("Choose at least two indexed documents to compare.")

    available_sources = {
        str(document["source"]) for document in list_indexed_documents()
    }
    missing_sources = sorted(set(requested_sources) - available_sources)
    if missing_sources:
        raise ValueError(
            "These documents are not indexed: " + ", ".join(missing_sources)
        )

    comparison_request = (
        question.strip()
        if question and question.strip()
        else "Compare the selected documents and identify the most important differences."
    )

    retrieved_docs = []
    for source in requested_sources:
        retrieved_docs.extend(
            similarity_search(
                settings.index_dir,
                comparison_request,
                limit=COMPARE_CHUNKS_PER_SOURCE,
                sources=[source],
            )
        )

    return comparison_request, _dedupe_documents(retrieved_docs)


def compare_documents(sources: List[str], question: str | None = None) -> Dict[str, Any]:
    comparison_request, retrieved_docs = _prepare_comparison(sources, question)
    if not retrieved_docs:
        return {
            "answer": "No indexed document content is available for the selected documents.",
            "sources": [],
        }

    llm = _build_llm()
    prompt = _build_compare_prompt(comparison_request, retrieved_docs)
    response = llm.invoke(prompt)
    return {
        "answer": _message_content_to_text(response.content),
        "sources": _format_sources(retrieved_docs),
    }


def stream_compare_documents(
    sources: List[str],
    question: str | None = None,
) -> Iterator[dict[str, Any]]:
    comparison_request, retrieved_docs = _prepare_comparison(sources, question)
    formatted_sources = _format_sources(retrieved_docs)
    yield {"type": "sources", "sources": formatted_sources}

    if not retrieved_docs:
        yield {
            "type": "token",
            "content": "No indexed document content is available for the selected documents.",
        }
        yield {"type": "done"}
        return

    llm = _build_llm()
    prompt = _build_compare_prompt(comparison_request, retrieved_docs)
    for chunk in llm.stream(prompt):
        content = _message_content_to_text(chunk.content)
        if content:
            yield {"type": "token", "content": content}

    yield {"type": "done"}
