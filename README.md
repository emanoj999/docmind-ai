# DocMind AI

DocMind AI is a personal AI-powered document analysis project built to learn how modern Retrieval-Augmented Generation (RAG) applications work.

The goal is simple: upload documents, ask questions in natural language, and receive answers grounded in the document content rather than generic model knowledge.

## Overview

DocMind AI is designed as a hands-on learning project for building an intelligent document assistant. Instead of manually searching through PDFs, users can interact with their documents through a chat-style interface.

The system follows a standard RAG workflow:

1. Documents are uploaded and parsed.
2. Text is split into smaller chunks.
3. Chunks are converted into embeddings.
4. Embeddings are stored in a vector index.
5. When a user asks a question, the most relevant chunks are retrieved.
6. An LLM uses the retrieved context to generate an answer.

This project focuses on clarity and learning rather than production-scale architecture.

## Features

- Upload PDF documents
- Build a searchable document knowledge base
- Ask natural language questions about uploaded content
- Retrieve semantically relevant document chunks
- Generate context-aware answers with RAG
- Show source references for transparency
- Provide a simple chat-style user experience

## Tech Stack

### Backend

- Python
- FastAPI
- LangChain
- FAISS

### Frontend

- React

### AI Models

- OpenAI language model for answer generation
- OpenAI embeddings model such as `text-embedding-3-small`

### Deployment

- Docker
- Render, Vercel, or AWS for learning and experimentation

## Why This Stack

This stack is intentionally simple.

- `FastAPI` keeps the backend lightweight and easy to build.
- `React` provides a straightforward frontend for chat and uploads.
- `LangChain` helps explore common AI application patterns quickly.
- `FAISS` is a good fit for a personal project and local experimentation.
- `OpenAI` provides reliable models for both embeddings and answer generation.

For a personal project, this is a reasonable and practical setup. If the project grows later, components such as `FAISS` can be replaced with a more persistent vector database.

## System Architecture

High-level query flow:

`User Question -> FastAPI API -> Vector Search -> Retrieve Relevant Chunks -> OpenAI LLM -> Answer with Sources`

High-level ingestion flow:

`PDF Upload -> Parse Text -> Chunk Text -> Create Embeddings -> Store in FAISS Index`

## How It Works

### 1. Document Upload

Users upload PDF documents through the frontend. The backend extracts the text from each document.

### 2. Chunking

The extracted text is split into smaller sections so retrieval is more accurate and efficient.

### 3. Embedding Generation

Each chunk is converted into a vector embedding using an OpenAI embeddings model.

### 4. Vector Storage

Embeddings are stored in a FAISS index, which enables semantic similarity search.

### 5. Retrieval

When the user asks a question, the system embeds the query and finds the most relevant chunks from the indexed document content.

### 6. Answer Generation

The retrieved chunks are sent to the language model as context, and the model generates a grounded answer.

### 7. Source Referencing

The response can include metadata such as filename, page number, or chunk reference so the user can trace where the answer came from.

## Suggested Project Structure

```text
docmind-ai/
├── README.md
├── requirements.txt
├── .env.example
├── backend/
│   ├── main.py
│   ├── rag_pipeline.py
│   ├── embeddings.py
│   ├── document_parser.py
│   └── vector_store.py
├── frontend/
│   └── src/
├── data/
│   └── sample_docs/
├── scripts/
│   └── ingest_documents.py
└── tests/
    └── test_rag.py
```

This structure keeps the main concerns separate:

- `document_parser.py` for file parsing and text extraction
- `embeddings.py` for embedding generation
- `vector_store.py` for FAISS storage and retrieval
- `rag_pipeline.py` for question-answering flow
- `main.py` for API routes

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/docmind-ai.git
cd docmind-ai
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
```

### 4. Run the backend

```bash
uvicorn backend.main:app --reload
```

### 5. Run the frontend

```bash
cd frontend
npm install
npm start
```

## Example Usage

Upload documents such as:

- company handbook
- research paper
- internal notes
- product documentation

Then ask questions like:

- "What are the main policies described in this document?"
- "Summarize the key points of section 3."
- "What does this paper say about the proposed methodology?"

The system retrieves the most relevant chunks and generates an answer based on the document content.

## Current Scope

DocMind AI is currently intended as:

- a personal learning project
- a portfolio project
- a practical way to understand RAG architecture end to end

It is not intended yet as a production-ready document platform.

## Limitations

- PDF parsing quality can affect answer quality
- Scanned PDFs may require OCR support
- FAISS is suitable for local and small-scale usage, not long-term production storage
- Retrieval quality depends on chunking strategy and embedding quality

## Future Improvements

- Add support for DOCX and TXT files
- Add OCR for scanned PDFs
- Store document metadata more explicitly
- Add persistent vector storage
- Support multiple documents per user
- Add authentication
- Improve source citations in answers

## Learning Goals

This project is a practical way to understand:

- document ingestion pipelines
- chunking and embeddings
- semantic search
- retrieval-augmented generation
- API and frontend integration for AI products

## License

Add your preferred license here.
