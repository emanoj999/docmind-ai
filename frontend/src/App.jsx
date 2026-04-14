import { useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [file, setFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);

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

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setUploadMessage(`${data.message} Chunks indexed: ${data.chunks_indexed}.`);
    } catch (error) {
      setUploadMessage(error.message);
    } finally {
      setIsUploading(false);
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
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Question failed.");
      }

      setAnswer(data.answer);
      setSources(data.sources);
    } catch (error) {
      setAnswer(error.message);
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Personal RAG Project</p>
        <h1>DocMind AI</h1>
        <p className="intro">
          Upload a PDF, index it into a FAISS vector store, and ask grounded
          questions about the content.
        </p>
      </section>

      <section className="panel">
        <h2>Upload Document</h2>
        <form onSubmit={handleUpload} className="stack">
          <input
            type="file"
            accept=".pdf"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <button type="submit" disabled={isUploading}>
            {isUploading ? "Uploading..." : "Upload PDF"}
          </button>
        </form>
        {uploadMessage && <p className="status">{uploadMessage}</p>}
      </section>

      <section className="panel">
        <h2>Ask Questions</h2>
        <form onSubmit={handleAsk} className="stack">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={5}
            placeholder="Ask something about the uploaded document..."
          />
          <button type="submit" disabled={isAsking}>
            {isAsking ? "Thinking..." : "Ask DocMind"}
          </button>
        </form>

        {answer && (
          <div className="result">
            <h3>Answer</h3>
            <p>{answer}</p>
            {sources.length > 0 && (
              <>
                <h3>Sources</h3>
                <ul>
                  {sources.map((source, index) => (
                    <li key={`${source.source}-${source.chunk_id}-${index}`}>
                      {source.source} | page {source.page ?? "n/a"} | chunk{" "}
                      {source.chunk_id ?? "n/a"}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </section>
    </main>
  );
}

export default App;
