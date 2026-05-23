import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from agents import generate_agent_outputs

NOTES_DIR = Path(__file__).resolve().parent / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)

MAX_NOTE_CHARS = 15000


def _natural_sort_key(name: str):
    """Sort key that orders session_N files by N numerically."""
    parts = re.split(r"(\d+)", name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


class Orchestrator:
    def __init__(self, emit_fn: Optional[Callable] = None):
        self.iteration = 0
        self.is_running = False
        self.latest_note = ""
        self.findings: Dict[str, str] = {}
        self.current_step = ""
        self._emit_fn = emit_fn
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def _emit(self, event: str, data: dict):
        if self._emit_fn:
            self._emit_fn(event, data)

    def _on_progress(self, step: str, status: str, label: str):
        self.current_step = step if status == "running" else ""
        self._emit("agent_progress", {
            "step": step,
            "status": status,
            "label": label,
            "iteration": self.iteration,
        })

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._emit("status_update", self._status_dict())
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self.is_running:
            return
        self._stop_event.set()
        self.is_running = False
        self.current_step = ""
        self._emit("status_update", self._status_dict())
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
        open_questions_text = self._read_existing_note("open_questions.md")
        recent_notes = self._collect_recent_notes()

        agent_data = generate_agent_outputs(
            self.iteration,
            framework_text,
            recent_notes,
            open_questions_text,
            on_progress=self._on_progress,
        )

        self._write_notes(agent_data)
        self.findings = {
            "theory": agent_data["theory"],
            "critique": agent_data["critique"],
            "research_prompt": agent_data["research_prompt"],
            "agent0_feedback": agent_data["agent0_feedback"],
            "synthesis": agent_data["synthesis"],
            "framework": agent_data["framework"],
        }
        self.latest_note = f"session_{self.iteration:08d}.md"
        self.current_step = ""

        notes = self.list_notes()
        self._emit("notes_update", {"notes": notes})
        self._emit("status_update", self._status_dict())

        return {
            "iteration": self.iteration,
            "notes": notes,
            "findings": self.findings,
        }

    def _status_dict(self) -> dict:
        return {
            "running": self.is_running,
            "iteration": self.iteration,
            "latest_note": self.latest_note,
            "findings": self.findings,
            "current_step": self.current_step,
        }

    def _write_notes(self, agent_data: Dict[str, str]):
        timestamp = datetime.utcnow().isoformat() + "Z"
        session_file = NOTES_DIR / f"session_{self.iteration:08d}.md"
        session_content = (
            f"# Session {self.iteration}\n"
            f"**Timestamp:** {timestamp}\n\n"
            f"## Agent 1 — Theorist\n{agent_data['theory']}\n\n"
            f"## Agent 2 — Critic\n{agent_data['critique']}\n\n"
            f"## Agent 3 — Research Prompt (First Pass)\n{agent_data['research_prompt']}\n\n"
            f"## Agent 0 — Researcher\n{agent_data['agent0_feedback']}\n\n"
            f"## Agent 3 — Assessor (Final Synthesis)\n{agent_data['synthesis']}\n\n"
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
        note_paths = sorted(NOTES_DIR.glob("*.md"), key=lambda p: _natural_sort_key(p.name))[-6:]
        note_texts = []
        for note_path in note_paths:
            note_texts.append(f"# {note_path.name}\n{note_path.read_text(encoding='utf-8')}\n")
        combined = "\n".join(note_texts)
        return combined[:MAX_NOTE_CHARS]

    def list_notes(self) -> List[str]:
        return sorted([p.name for p in NOTES_DIR.glob("*.md")], key=_natural_sort_key)

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
        self.current_step = ""
        self._emit("notes_update", {"notes": []})
        self._emit("status_update", self._status_dict())
