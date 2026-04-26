import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function sourceKey(source, index) {
  return `${source.source}-${source.page}-${source.chunk_id}-${index}`;
}

function sourceLabel(source) {
  const page = source.page ?? "n/a";
  const chunk = source.chunk_id ?? "n/a";
  return `[${source.citation_id}] ${source.source} / page ${page} / chunk ${chunk}`;
}

async function readApiError(response, fallback) {
  try {
    const data = await response.json();
    return data.detail || fallback;
  } catch {
    return fallback;
  }
}

function isNetworkError(error) {
  return error instanceof TypeError || error.message === "Failed to fetch";
}

function EvidencePanel({ idPrefix, sources, title }) {
  if (!sources.length) {
    return null;
  }

  return (
    <section className="evidence-panel" aria-label={title}>
      <div className="section-heading">
        <h3>{title}</h3>
        <span>{sources.length} snippets</span>
      </div>
      <div className="evidence-list">
        {sources.map((source, index) => (
          <article
            className="evidence-card"
            id={`${idPrefix}-evidence-${source.citation_id}`}
            key={sourceKey(source, index)}
          >
            <div className="evidence-meta">{sourceLabel(source)}</div>
            <p>{source.snippet}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function App() {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [documents, setDocuments] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);
  const [libraryMessage, setLibraryMessage] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [compareQuestion, setCompareQuestion] = useState("");
  const [compareAnswer, setCompareAnswer] = useState("");
  const [compareSources, setCompareSources] = useState([]);
  const [compareMessage, setCompareMessage] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [isComparing, setIsComparing] = useState(false);
  const [deletingSource, setDeletingSource] = useState("");

  const selectedDocuments = useMemo(
    () =>
      documents.filter((documentItem) =>
        selectedSources.includes(documentItem.source)
      ),
    [documents, selectedSources]
  );

  async function fetchDocuments({ quietNetworkError = false } = {}) {
    setIsLoadingDocuments(true);
    setLibraryMessage("");

    try {
      const response = await fetch(`${API_BASE_URL}/documents`);
      if (!response.ok) {
        throw new Error(await readApiError(response, "Could not load documents."));
      }

      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      if (quietNetworkError && isNetworkError(error)) {
        setDocuments([]);
        return;
      }

      setLibraryMessage(error.message);
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  useEffect(() => {
    fetchDocuments({ quietNetworkError: true });
  }, []);

  function toggleSource(source) {
    setSelectedSources((currentSources) =>
      currentSources.includes(source)
        ? currentSources.filter((item) => item !== source)
        : [...currentSources, source]
    );
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) {
      setUploadMessage("Choose a PDF file first.");
      return;
    }

    setIsUploading(true);
    setUploadMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Upload failed."));
      }

      const data = await response.json();
      const ocrSuffix =
        data.used_ocr === "yes"
          ? " OCR fallback was used for at least one page."
          : "";
      setUploadMessage(
        `${data.message} Chunks indexed: ${data.chunks_indexed}.${ocrSuffix}`
      );
      setSelectedSources((currentSources) =>
        currentSources.includes(file.name)
          ? currentSources
          : [...currentSources, file.name]
      );
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      await fetchDocuments();
    } catch (error) {
      setUploadMessage(error.message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDeleteDocument(source) {
    const shouldDelete = window.confirm(`Delete ${source} from DocMind AI?`);
    if (!shouldDelete) {
      return;
    }

    setDeletingSource(source);
    setLibraryMessage("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/documents/${encodeURIComponent(source)}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error(await readApiError(response, "Delete failed."));
      }

      const data = await response.json();
      const deleteMessage = `${data.message} Removed ${data.chunks_deleted} indexed chunks.`;
      setSelectedSources((currentSources) =>
        currentSources.filter((item) => item !== source)
      );
      if (file?.name === source) {
        setFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
      if (sources.some((item) => item.source === source)) {
        setAnswer("");
        setSources([]);
      }
      if (compareSources.some((item) => item.source === source)) {
        setCompareAnswer("");
        setCompareSources([]);
      }
      await fetchDocuments();
      setLibraryMessage(deleteMessage);
    } catch (error) {
      setLibraryMessage(error.message);
    } finally {
      setDeletingSource("");
    }
  }

  function handleAnswerStreamEvent(eventData) {
    if (eventData.type === "sources") {
      setSources(eventData.sources || []);
      return;
    }

    if (eventData.type === "token") {
      setAnswer((currentAnswer) => `${currentAnswer}${eventData.content || ""}`);
      return;
    }

    if (eventData.type === "error") {
      setAnswer(eventData.message || "Question failed.");
    }
  }

  function handleCompareStreamEvent(eventData) {
    if (eventData.type === "sources") {
      setCompareSources(eventData.sources || []);
      return;
    }

    if (eventData.type === "token") {
      setCompareAnswer(
        (currentAnswer) => `${currentAnswer}${eventData.content || ""}`
      );
      return;
    }

    if (eventData.type === "error") {
      setCompareMessage(eventData.message || "Comparison failed.");
    }
  }

  async function readEventStream(response, handleEvent) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const messages = buffer.split("\n\n");
      buffer = messages.pop() || "";

      for (const message of messages) {
        const data = message
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trim())
          .join("\n");

        if (!data) {
          continue;
        }

        handleEvent(JSON.parse(data));
      }
    }

    if (buffer.trim()) {
      const data = buffer
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim())
        .join("\n");

      if (data) {
        handleEvent(JSON.parse(data));
      }
    }
  }

  async function handleAsk(event) {
    event.preventDefault();
    if (!question.trim()) {
      return;
    }

    setIsAsking(true);
    setAnswer("");
    setSources([]);

    try {
      const response = await fetch(`${API_BASE_URL}/ask/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Question failed."));
      }

      if (!response.body) {
        throw new Error("Streaming is not available in this browser.");
      }

      await readEventStream(response, handleAnswerStreamEvent);
    } catch (error) {
      setAnswer(error.message);
    } finally {
      setIsAsking(false);
    }
  }

  async function handleCompare(event) {
    event.preventDefault();
    if (selectedSources.length < 2) {
      setCompareMessage("Select at least two indexed documents.");
      return;
    }

    setIsComparing(true);
    setCompareAnswer("");
    setCompareSources([]);
    setCompareMessage("");

    try {
      const response = await fetch(`${API_BASE_URL}/compare/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sources: selectedSources,
          question: compareQuestion,
        }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Comparison failed."));
      }

      if (!response.body) {
        throw new Error("Streaming is not available in this browser.");
      }

      await readEventStream(response, handleCompareStreamEvent);
    } catch (error) {
      setCompareMessage(error.message);
    } finally {
      setIsComparing(false);
    }
  }

  function scrollToEvidence(citationId) {
    document
      .getElementById(`answer-evidence-${citationId}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <main className="page">
      <header className="app-header">
        <p className="eyebrow">Evidence-first document AI</p>
        <h1>DocMind AI</h1>
      </header>

      <section className="workspace">
        <div className="module upload-module">
          <div className="section-heading">
            <h2>Documents</h2>
            <span>{documents.length} indexed</span>
          </div>

          <form onSubmit={handleUpload} className="stack">
            <label className="file-input">
              <span>{file ? file.name : "Choose PDF"}</span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
            </label>
            <button type="submit" disabled={isUploading}>
              {isUploading ? "Indexing..." : "Upload PDF"}
            </button>
          </form>

          {uploadMessage && <p className="status">{uploadMessage}</p>}

          <div className="library">
            {isLoadingDocuments && <p className="muted">Loading documents...</p>}
            {libraryMessage && <p className="status error">{libraryMessage}</p>}
            {!isLoadingDocuments && documents.length === 0 && (
              <p className="muted">Upload PDFs to build the workspace.</p>
            )}
            {documents.map((documentItem) => (
              <div className="document-row" key={documentItem.source}>
                <input
                  type="checkbox"
                  checked={selectedSources.includes(documentItem.source)}
                  onChange={() => toggleSource(documentItem.source)}
                  aria-label={`Select ${documentItem.source}`}
                />
                <span>
                  <strong>{documentItem.source}</strong>
                  <small>
                    {documentItem.page_count} pages / {documentItem.chunk_count}{" "}
                    chunks{documentItem.used_ocr ? " / OCR" : ""}
                  </small>
                </span>
                <button
                  type="button"
                  className="delete-button"
                  disabled={deletingSource === documentItem.source}
                  onClick={() => handleDeleteDocument(documentItem.source)}
                >
                  {deletingSource === documentItem.source ? "Deleting" : "Delete"}
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="module ask-module">
          <div className="section-heading">
            <h2>Ask</h2>
            <span>{isAsking ? "streaming" : "ready"}</span>
          </div>

          <form onSubmit={handleAsk} className="stack">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={5}
              placeholder="Ask something about the uploaded documents..."
            />
            <button type="submit" disabled={isAsking}>
              {isAsking ? "Thinking..." : "Ask DocMind"}
            </button>
          </form>

          {answer && (
            <section className="answer-block">
              <h3>Answer</h3>
              <p>{answer}</p>
              {sources.length > 0 && (
                <div className="citation-strip" aria-label="Citations">
                  {sources.map((source, index) => (
                    <button
                      type="button"
                      className="citation-pill"
                      key={sourceKey(source, index)}
                      onClick={() => scrollToEvidence(source.citation_id)}
                    >
                      [{source.citation_id}]
                    </button>
                  ))}
                </div>
              )}
              <EvidencePanel
                idPrefix="answer"
                sources={sources}
                title="Evidence"
              />
            </section>
          )}
        </div>

        <div className="module compare-module">
          <div className="section-heading">
            <h2>Compare</h2>
            <span>{selectedDocuments.length} selected</span>
          </div>

          <form onSubmit={handleCompare} className="stack">
            <textarea
              value={compareQuestion}
              onChange={(event) => setCompareQuestion(event.target.value)}
              rows={4}
              placeholder="Optional: focus the comparison on pricing, risks, dates, obligations..."
            />
            <button type="submit" disabled={isComparing}>
              {isComparing ? "Comparing..." : "Compare selected"}
            </button>
          </form>

          {compareMessage && <p className="status error">{compareMessage}</p>}

          {compareAnswer && (
            <section className="answer-block">
              <h3>Comparison</h3>
              <p>{compareAnswer}</p>
              <EvidencePanel
                idPrefix="compare"
                sources={compareSources}
                title="Comparison Evidence"
              />
            </section>
          )}
        </div>
      </section>
    </main>
  );
}

export default App;
