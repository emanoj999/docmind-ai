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


def similarity_search(index_dir: Path, query: str, limit: int = 4) -> List[Document]:
    vector_store = load_vector_store(index_dir)
    if vector_store is None:
        return []

    return vector_store.similarity_search(query, k=limit)
