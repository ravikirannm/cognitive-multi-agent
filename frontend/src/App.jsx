import { useEffect, useState } from "react";
import ReactMarkdown from 'react-markdown';

const API_BASE = "/api";

function App() {
    const [status, setStatus] = useState(null);
    const [notes, setNotes] = useState([]);
    const [selectedNote, setSelectedNote] = useState(null);
    const [selectedContent, setSelectedContent] = useState("");
    const [message, setMessage] = useState("");

    useEffect(() => {
        refreshStatus();
        refreshNotes();
    }, []);

    async function refreshStatus() {
        const res = await fetch(`${API_BASE}/status`);
        const data = await res.json();
        setStatus(data);
    }

    async function refreshNotes() {
        const res = await fetch(`${API_BASE}/notes`);
        const data = await res.json();
        setNotes(data);
        if (data.length > 0 && !selectedNote) {
            setSelectedNote(data[0]);
        }
    }

    async function loadNote(name) {
        setSelectedNote(name);
        const res = await fetch(`${API_BASE}/notes/${encodeURIComponent(name)}`);
        const data = await res.json();
        setSelectedContent(data.content || "");
    }

    async function startLoop() {
        await fetch(`${API_BASE}/start`, { method: "POST" });
        setMessage("Loop started.");
        refreshStatus();
    }

    async function stopLoop() {
        await fetch(`${API_BASE}/stop`, { method: "POST" });
        setMessage("Loop stopped.");
        refreshStatus();
    }

    async function stepOnce() {
        await fetch(`${API_BASE}/step`, { method: "POST" });
        setMessage("Performed one iteration.");
        refreshStatus();
        refreshNotes();
    }

    async function resetNotes() {
        await fetch(`${API_BASE}/reset`, { method: "POST" });
        setMessage("Notes reset.");
        setSelectedNote(null);
        setSelectedContent("");
        refreshStatus();
        refreshNotes();
    }

    useEffect(() => {
        if (selectedNote) {
            loadNote(selectedNote);
        }
    }, [selectedNote]);

    return (
        <div className="app-shell">
            <header>
                <h1>Cognitive Multi-Agent Monitor</h1>
                <p>Control the agent loop, inspect notes, and review generated findings.</p>
            </header>

            <section className="controls">
                <button onClick={startLoop}>Start</button>
                <button onClick={stopLoop}>Stop</button>
                <button onClick={stepOnce}>Step</button>
                <button className="danger" onClick={resetNotes}>Reset Notes</button>
            </section>

            <section className="panel">
                <div className="status-box">
                    <h2>Runtime Status</h2>
                    {status ? (
                        <ul>
                            <li>Running: {status.running ? "Yes" : "No"}</li>
                            <li>Iteration: {status.iteration}</li>
                            <li>Latest note: {status.latest_note || "None"}</li>
                        </ul>
                    ) : (
                        <p>Loading status…</p>
                    )}
                </div>

                <div className="notes-box">
                    <h2>Generated Notes</h2>
                    {notes.length ? (
                        <ul>
                            {notes.map((note) => (
                                <li key={note}>
                                    <button
                                        className={note === selectedNote ? "selected" : ""}
                                        onClick={() => setSelectedNote(note)}
                                    >
                                        {note}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p>No notes yet. Run a step to create notes.</p>
                    )}
                </div>
            </section>

            {status?.findings && (
                <section className="panel">
                    <div className="status-box">
                        <h2>Latest Findings</h2>
                        <pre className="ellipsis-pre">{JSON.stringify(status.findings, null, 2)}</pre>
                    </div>
                </section>
            )}

            <section className="content-box">
                <h2>Note Preview</h2>
                {selectedContent ? (
                    <ReactMarkdown>{selectedContent}</ReactMarkdown>
                ) : (
                    <p>Select a note to view its contents.</p>
                )}
            </section>

            <footer>{message}</footer>
        </div>
    );
}

export default App;
