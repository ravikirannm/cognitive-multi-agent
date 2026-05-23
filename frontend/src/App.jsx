import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { io } from "socket.io-client";

const API_BASE = "/api";

const STEPS = [
    { id: "agent1",      label: "Agent 1 — Theorist" },
    { id: "agent2",      label: "Agent 2 — Critic" },
    { id: "agent3_first", label: "Agent 3 — Research Prompt" },
    { id: "agent0",      label: "Agent 0 — Researcher" },
    { id: "agent3_final", label: "Agent 3 — Final Synthesis" },
    { id: "agent4",      label: "Agent 4 — Synthesizer" },
];

function StepIcon({ status }) {
    if (status === "running") return <span className="step-spinner" />;
    if (status === "done")    return <span className="step-done">✓</span>;
    if (status === "error")   return <span className="step-error">✕</span>;
    return <span className="step-idle" />;
}

function App() {
    const [status, setStatus]               = useState(null);
    const [notes, setNotes]                 = useState([]);
    const [selectedNote, setSelectedNote]   = useState(null);
    const [selectedContent, setSelectedContent] = useState("");
    const [message, setMessage]             = useState("");
    const [stepStatus, setStepStatus]       = useState({});
    const [stepIteration, setStepIteration] = useState(null);
    const [stepping, setStepping]           = useState(false);
    const socketRef = useRef(null);

    // ── WebSocket setup ──────────────────────────────────────────────────────
    useEffect(() => {
        const socket = io({ path: "/socket.io", transports: ["websocket", "polling"] });
        socketRef.current = socket;

        socket.on("agent_progress", (data) => {
            // Reset progress board when a new iteration begins
            setStepIteration((prev) => {
                if (prev !== data.iteration) {
                    setStepStatus({ [data.step]: data.status });
                    return data.iteration;
                }
                setStepStatus((s) => ({ ...s, [data.step]: data.status }));
                return prev;
            });

            // When a step finishes, refresh its note if it's selected
            if (data.status === "done") {
                setSelectedNote((sel) => {
                    if (sel) loadNote(sel);
                    return sel;
                });
            }
        });

        socket.on("status_update", (data) => {
            setStatus(data);
        });

        socket.on("notes_update", (data) => {
            setNotes(data.notes);
            // Auto-select the latest note if nothing is selected
            setSelectedNote((sel) => {
                if (!sel && data.notes.length > 0) return data.notes[data.notes.length - 1];
                return sel;
            });
        });

        return () => socket.disconnect();
    }, []);

    // ── Initial fetch ────────────────────────────────────────────────────────
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
        if (data.length > 0) {
            setSelectedNote((sel) => sel || data[data.length - 1]);
        }
    }

    async function loadNote(name) {
        const res = await fetch(`${API_BASE}/notes/${encodeURIComponent(name)}`);
        const data = await res.json();
        setSelectedContent(data.content || "");
    }

    useEffect(() => {
        if (selectedNote) loadNote(selectedNote);
    }, [selectedNote]);

    // ── Control actions ──────────────────────────────────────────────────────
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
        setStepping(true);
        setStepStatus({});
        try {
            await fetch(`${API_BASE}/step`, { method: "POST" });
            setMessage("Iteration complete.");
            refreshStatus();
            refreshNotes();
        } finally {
            setStepping(false);
        }
    }

    async function resetNotes() {
        await fetch(`${API_BASE}/reset`, { method: "POST" });
        setMessage("Notes reset.");
        setSelectedNote(null);
        setSelectedContent("");
        setStepStatus({});
        refreshStatus();
        refreshNotes();
    }

    const isRunning  = status?.running || false;
    const isBusy     = isRunning || stepping;
    const hasProgress = Object.keys(stepStatus).length > 0;

    return (
        <div className="app-shell">
            <header>
                <h1>Cognitive Multi-Agent Monitor</h1>
                <p>Control the agent loop, inspect notes, and review generated findings.</p>
            </header>

            {/* ── Controls ── */}
            <section className="controls">
                <button onClick={startLoop} disabled={isBusy}>Start</button>
                <button onClick={stopLoop}  disabled={!isRunning}>Stop</button>
                <button onClick={stepOnce}  disabled={isBusy}>Step</button>
                <button className="danger"  onClick={resetNotes} disabled={isBusy}>Reset Notes</button>
            </section>

            {/* ── Progress panel ── */}
            {hasProgress && (
                <section className="progress-panel">
                    <h2>
                        Iteration {stepIteration}
                        {isBusy && <span className="running-badge">running</span>}
                    </h2>
                    <ol className="step-list">
                        {STEPS.map((s) => (
                            <li key={s.id} className={`step-item step-${stepStatus[s.id] || "idle"}`}>
                                <StepIcon status={stepStatus[s.id] || "idle"} />
                                <span>{s.label}</span>
                            </li>
                        ))}
                    </ol>
                </section>
            )}

            {/* ── Status + Notes ── */}
            <section className="panel">
                <div className="status-box">
                    <h2>Runtime Status</h2>
                    {status ? (
                        <ul>
                            <li>Running: {status.running ? "Yes" : "No"}</li>
                            <li>Iteration: {status.iteration}</li>
                            <li>Latest note: {status.latest_note || "None"}</li>
                            {status.current_step && (
                                <li>Step: <strong>{status.current_step}</strong></li>
                            )}
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

            {/* ── Findings ── */}
            {status?.findings && Object.keys(status.findings).length > 0 && (
                <section className="panel">
                    <div className="status-box">
                        <h2>Latest Findings</h2>
                        <pre className="ellipsis-pre">{JSON.stringify(status.findings, null, 2)}</pre>
                    </div>
                </section>
            )}

            {/* ── Note preview ── */}
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
