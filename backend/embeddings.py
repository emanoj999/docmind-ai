from __future__ import annotations

from langchain_openai import OpenAIEmbeddings

from backend.config import settings


def build_embeddings() -> OpenAIEmbeddings:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
