# Cognitive Multi-Agent Research Loop

A local multi-agent research loop that uses a local LLM (Ollama / Qwen2) to run four specialized agents. The system stores iteration outputs as Markdown notes and provides a small React frontend to control and inspect the agents and their findings.

![App Screenshot](image.png)

## Quick summary

- **Backend:** Flask API (`backend/`) runs the orchestrator and persists Markdown notes into `backend/notes/`.
- **Frontend:** React + Vite app (`frontend/`) to control the loop and view generated notes.
- **LLM backend:** Local Ollama instance (configurable with `OLLAMA_BASE_URL` and `OLLAMA_MODEL`).

## Architecture & agent responsibilities

This repository implements a closed-loop research pipeline. Each iteration, the orchestrator collects context (existing framework, recent notes, and lightweight web research), then prompts four agents in sequence:

- **Agent 1 — Theorist**
	- Role: Produce a concise, testable theory about cognition or intelligence.
	- Output: `# Theory` markdown note containing `Hypothesis`, `Mechanism`, `Predictions`, and `Implications`.
	- Inputs: Agent 4 framework, recent notes, and external research snippets.

- **Agent 2 — Critic**
	- Role: Rigorously interrogate the Theory for logical gaps, contradictions, untested assumptions, and edge cases.
	- Output: `# Critique` markdown with at least three weaknesses, one or more alternative explanations, and suggested refinements/experiments.

- **Agent 3 — Neutral Assessor**
	- Role: Consolidate the Theory and Critique into a calibrated research note with prioritized open questions and proposed evaluation metrics.
	- Output: `# Synthesis`, `## Master Theory`, `## Open Questions`.

- **Agent 4 — Synthesizer**
	- Role: Ingest all notes and the latest synthesis to update the long-running `agent4_framework.md` document. This becomes seed context for subsequent iterations.
	- Output: `# Agent 4 Framework` with principles, prioritized hypotheses, and a seed prompt for Agent 1.

### Iteration data flow

1. Orchestrator reads `agent4_framework.md` and several most recent session notes.
2. It performs lightweight web searches and pulls short page excerpts for grounding.
3. Agent 1 generates a theory using the collected context.
4. Agent 2 critiques Agent 1's output.
5. Agent 3 synthesizes the pair into a research note and open questions.
6. Agent 4 updates the framework document, which feeds into the next iteration.

This loop increases context richness over time; the model weights remain fixed but the external memory grows.

## Grounding & external research

To reduce hallucinations and provide up-to-date evidence, the orchestrator collects web search results (DuckDuckGo) and extracts short HTML excerpts (via BeautifulSoup). These are included in the LLM prompts as concise context snippets.

Important: the search integration is intentionally lightweight. Respect robots.txt and site usage policies. For production research, consider integrating APIs (arXiv, PubMed) and a rate-limited fetcher.

## API (examples)

- `GET /api/status` — runtime state and latest findings
- `POST /api/start` — start the orchestrator loop
- `POST /api/stop` — stop the loop
- `POST /api/step` — run one iteration synchronously
- `GET /api/notes` — list generated notes
- `GET /api/notes/<name>` — fetch a note content
- `POST /api/reset` — wipe notes and reset iteration counter

## Running the project

### Docker Compose (recommended)

From project root:

```bash
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5000/api/status`

### Local (Python + Node)

1. Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/run.py
```

2. Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Configuration and Ollama

- `OLLAMA_BASE_URL` — base URL for your Ollama instance (default: `http://127.0.0.1:11434`).
- `OLLAMA_MODEL` — model identifier to request (e.g., `qwen2.5:7b`).

If Ollama is not available the backend returns an error string embedded in generated notes; start Ollama before running the loop.

## Troubleshooting

- Repeated identical outputs: ensure `backend/notes/agent4_framework.md` is actually changing between iterations and that the orchestrator reads the latest file. If the framework is constant the prompts will be nearly identical.
- `ImportError` for `duckduckgo_search`: the installed package version may expose a different API. You can either pin the package version used by the project or replace the `search.py` implementation with another search provider.
- Ollama connectivity: confirm `OLLAMA_BASE_URL` and that the Ollama daemon is listening on the configured port.

## Extending this project

- Add Agent 5 (Experimentalist) to run simple computational experiments (simulations, small neural nets, or ablations) to test hypotheses.
- Persist notes to a vector database (e.g., Chroma, Milvus) for semantic retrieval and better context selection.
- Add unit tests for prompt shapes and note-writing logic.

## Contributing

Small, focused pull requests are welcome — especially those that improve grounding, add tests, or make prompts more robust.

## License

Add a `LICENSE` file (e.g., MIT) before publishing the repository.
