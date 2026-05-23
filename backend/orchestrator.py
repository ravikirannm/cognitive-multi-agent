import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from agents import generate_agent_outputs

NOTES_DIR = Path(__file__).resolve().parent / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)

MAX_NOTE_CHARS = 15000

class Orchestrator:
    def __init__(self):
        self.iteration = 0
        self.is_running = False
        self.latest_note = ""
        self.findings: Dict[str, str] = {}
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self.is_running:
            return
        self._stop_event.set()
        self.is_running = False
        if self._thread is not None:
            self._thread.join(timeout=2)

    def step(self):
        with self._lock:
            return self._run_iteration()

    def _loop(self):
        while not self._stop_event.is_set():
            with self._lock:
                self._run_iteration()
            time.sleep(4)

    def _run_iteration(self):
        self.iteration += 1
        framework_text = self._read_existing_note("agent4_framework.md")
        recent_notes = self._collect_recent_notes()
        agent_data = generate_agent_outputs(self.iteration, framework_text, recent_notes)

        self._write_notes(agent_data)
        self.findings = {
            "theory": agent_data["theory"],
            "critique": agent_data["critique"],
            "synthesis": agent_data["synthesis"],
            "framework": agent_data["framework"],
        }
        self.latest_note = f"session_{self.iteration}.md"
        return {
            "iteration": self.iteration,
            "notes": self.list_notes(),
            "findings": self.findings,
        }

    def _write_notes(self, agent_data: Dict[str, str]):
        timestamp = datetime.utcnow().isoformat() + "Z"
        session_file = NOTES_DIR / f"session_{self.iteration}.md"
        session_content = (
            f"# Session {self.iteration}\n"
            f"**Timestamp:** {timestamp}\n\n"
            f"## Agent 1 — Theorist\n{agent_data['theory']}\n\n"
            f"## Agent 2 — Critic\n{agent_data['critique']}\n\n"
            f"## Agent 3 — Assessor\n{agent_data['synthesis']}\n\n"
            f"## Agent 4 — Synthesizer\n{agent_data['framework']}\n"
        )
        session_file.write_text(session_content, encoding="utf-8")

        (NOTES_DIR / "master_theory.md").write_text(agent_data["master_theory"], encoding="utf-8")
        (NOTES_DIR / "open_questions.md").write_text(agent_data["open_questions"], encoding="utf-8")
        (NOTES_DIR / "agent4_framework.md").write_text(agent_data["framework"], encoding="utf-8")

    def _read_existing_note(self, name: str) -> str:
        note_path = NOTES_DIR / name
        if note_path.exists():
            return note_path.read_text(encoding="utf-8")
        return ""

    def _collect_recent_notes(self) -> str:
        note_paths = sorted(NOTES_DIR.glob("*.md"))[-6:]
        note_texts = []
        for note_path in note_paths:
            note_texts.append(f"# {note_path.name}\n{note_path.read_text(encoding='utf-8')}\n")
        combined = "\n".join(note_texts)
        return combined[:MAX_NOTE_CHARS]

    def list_notes(self) -> List[str]:
        return sorted([p.name for p in NOTES_DIR.glob("*.md")])

    def read_note(self, name: str) -> str:
        path = NOTES_DIR / name
        if not path.exists():
            raise FileNotFoundError
        return path.read_text(encoding="utf-8")

    def reset_notes(self):
        for note in NOTES_DIR.glob("*.md"):
            note.unlink()
        self.iteration = 0
        self.latest_note = ""
        self.findings = {}
