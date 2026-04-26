from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from backend.embeddings import build_embeddings


INDEX_FILE = "index.faiss"
DOCSTORE_FILE = "index.pkl"


def _index_exists(index_dir: Path) -> bool:
    return (index_dir / INDEX_FILE).exists() and (index_dir / DOCSTORE_FILE).exists()


def load_vector_store(index_dir: Path) -> FAISS | None:
    if not _index_exists(index_dir):
        return None

    return FAISS.load_local(
        str(index_dir),
        build_embeddings(),
        allow_dangerous_deserialization=True,
    )


def add_documents(index_dir: Path, documents: Iterable[Document]) -> int:
    docs = list(documents)
    if not docs:
        return 0

    vector_store = load_vector_store(index_dir)
    if vector_store is None:
        vector_store = FAISS.from_documents(docs, build_embeddings())
    else:
        vector_store.add_documents(docs)

    vector_store.save_local(str(index_dir))
    return len(docs)


def list_documents(index_dir: Path) -> List[Document]:
    vector_store = load_vector_store(index_dir)
    if vector_store is None:
        return []

    documents: List[Document] = []
    for docstore_id in vector_store.index_to_docstore_id.values():
        document = vector_store.docstore.search(docstore_id)
        if isinstance(document, Document):
            documents.append(document)

    return documents


def list_sources(index_dir: Path) -> List[dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    for document in list_documents(index_dir):
        source = str(document.metadata.get("source", "unknown"))
        summary = summaries.setdefault(
            source,
            {
                "source": source,
                "pages": set(),
                "chunk_count": 0,
                "used_ocr": False,
            },
        )
        page = document.metadata.get("page")
        if page is not None:
            summary["pages"].add(page)
        summary["chunk_count"] = int(summary["chunk_count"]) + 1
        if document.metadata.get("extraction_method") == "ocr":
            summary["used_ocr"] = True

    formatted_sources = []
    for source, summary in summaries.items():
        pages = summary["pages"]
        formatted_sources.append(
            {
                "source": source,
                "page_count": len(pages),
                "chunk_count": summary["chunk_count"],
                "used_ocr": summary["used_ocr"],
            }
        )

    return sorted(formatted_sources, key=lambda item: str(item["source"]).lower())


def documents_for_sources(index_dir: Path, sources: Iterable[str]) -> List[Document]:
    source_set = set(sources)
    if not source_set:
        return []

    return [
        document
        for document in list_documents(index_dir)
        if document.metadata.get("source") in source_set
    ]


def delete_source(index_dir: Path, source: str) -> int:
    vector_store = load_vector_store(index_dir)
    if vector_store is None:
        return 0

    ids_to_delete = []
    for docstore_id in vector_store.index_to_docstore_id.values():
        document = vector_store.docstore.search(docstore_id)
        if isinstance(document, Document) and document.metadata.get("source") == source:
            ids_to_delete.append(docstore_id)

    if not ids_to_delete:
        return 0

    vector_store.delete(ids=ids_to_delete)
    vector_store.save_local(str(index_dir))
    return len(ids_to_delete)


def similarity_search(
    index_dir: Path,
    query: str,
    limit: int = 4,
    sources: Iterable[str] | None = None,
) -> List[Document]:
    vector_store = load_vector_store(index_dir)
    if vector_store is None:
        return []

    source_set = set(sources or [])
    if not source_set:
        return vector_store.similarity_search(query, k=limit)

    def metadata_filter(metadata: dict) -> bool:
        return metadata.get("source") in source_set

    try:
        return vector_store.similarity_search(
            query,
            k=limit,
            filter=metadata_filter,
            fetch_k=max(limit * 8, 32),
        )
    except TypeError:
        results = vector_store.similarity_search(query, k=max(limit * 8, 32))
        return [
            document
            for document in results
            if document.metadata.get("source") in source_set
        ][:limit]
