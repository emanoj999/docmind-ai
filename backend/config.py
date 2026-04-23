from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.openai_embedding_model = os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )
        self.ocr_language = os.getenv("DOCMIND_OCR_LANGUAGE", "eng")
        self.data_dir = Path(os.getenv("DOCMIND_DATA_DIR", "backend/data"))
        self.uploads_dir = self.data_dir / "uploads"
        self.index_dir = self.data_dir / "faiss_index"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
