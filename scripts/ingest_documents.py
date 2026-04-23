from __future__ import annotations

import sys
from pathlib import Path

from backend.document_parser import parse_pdf
from backend.rag_pipeline import ingest_documents


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/ingest_documents.py <pdf_path>")
        return 1

    pdf_path = Path(sys.argv[1]).expanduser().resolve()
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        return 1

    documents = parse_pdf(pdf_path)
    chunk_count = ingest_documents(documents)
    print(f"Indexed {pdf_path.name} into {chunk_count} chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
