import re
from typing import Callable, Dict, List, Optional

from llm import chat_completion
from search import collect_research_context

AGENT_PROMPTS = {
    "researcher": (
        "You are Agent 0, Researcher. Your role is to find genuinely new external evidence, "
        "alternative perspectives, and relevant published findings in response to specific research questions. "
        "You are thorough, skeptical, and focused on what is missing from existing theory — not on confirming it."
    ),
    "theory": (
        "You are Agent 1, Theorist. Your job is to propose a high-level cognitive theory"
        " rooted in psychology, neuroscience, genetics, mathematics, and philosophy."
    ),
    "critique": (
        "You are Agent 2, Critic. Your job is to interrogate Agent 1's theory, identify weaknesses,"
        " evaluate assumptions, and suggest concrete refinements."
    ),
    "synthesis": (
        "You are Agent 3, Neutral Assessor. Your job is to summarize the theory and critique,"
        " write balanced research notes, and formulate open questions and next steps."
    ),
    "framework": (
        "You are Agent 4, Synthesizer. Your job is to integrate all notes into a coherent framework"
        " that can seed the next iteration of the loop."
    ),
}

_FALLBACK_RESEARCH_TOPICS = [
    "cognitive neuroscience predictive processing",
    "psychiatry brain circuits mental health models",
    "philosophy of mind consciousness theory",
    "genetics of intelligence and cognition",
    "mathematical models of cognition and learning",
    "psychology of decision making and abstraction",
    "books on neuroscience and consciousness pdf",
]


def _derive_research_topics(open_questions_text: str) -> List[str]:
    """Extract search topics from open questions text, falling back to static list."""
    if not open_questions_text:
        return _FALLBACK_RESEARCH_TOPICS

    topics = []
    for line in open_questions_text.splitlines():
        clean = re.sub(r"^[\-\*\#\d\.\s]+", "", line).strip()
        clean = re.sub(r"\*+", "", clean).strip()
        if "?" in clean and len(clean) > 15:
            topics.append(clean[:120])

    return topics[:7] if topics else _FALLBACK_RESEARCH_TOPICS


def _extract_search_queries(research_prompt_text: str) -> List[str]:
    """Extract web search queries from Agent 3's first-pass research prompt."""
    queries = []

    # Prefer the ## Search Directions section
    section_match = re.search(
        r"(?ms)^##\s*Search Directions\s*(.*?)(?=^##|\Z)", research_prompt_text
    )
    if section_match:
        for line in section_match.group(1).splitlines():
            clean = re.sub(r"^[\-\*\d\.\s]+", "", line).strip()
            if clean:
                queries.append(clean[:120])

    # Fallback: lines containing question marks
    if not queries:
        for line in research_prompt_text.splitlines():
            clean = re.sub(r"^[\-\*\#\d\.\s]+", "", line).strip()
            if "?" in clean and len(clean) > 10:
                queries.append(clean[:120])

    return queries[:5] or ["cognitive neuroscience research"]


def _build_context(iteration: int, framework: str, recent_notes: str, research_context: str) -> str:
    return (
        f"Iteration: {iteration}\n\n"
        f"Current agent4 framework:\n{framework or 'No framework exists yet.'}\n\n"
        f"Recent notes and history:\n{recent_notes or 'No previous notes available.'}\n\n"
        f"External research context from web and published material:\n{research_context or 'No search context available.'}\n\n"
    )


def _extract_section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^#{1,3}\s*{re.escape(heading)}\s*(.*?)(?=^#{1,3}\s+|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else text.strip()


def _build_messages(system_text: str, user_text: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_text},
    ]


def _run_agent0_researcher(research_prompt: str, recent_notes: str) -> str:
    """Agent 0 explores the web and existing notes based on Agent 3's focused research prompt."""
    queries = _extract_search_queries(research_prompt)
    web_context = collect_research_context(queries, max_results=3)

    prompt = (
        "You received the following focused research prompt from Agent 3:\n\n"
        + research_prompt
        + "\n\n---\n\n"
        "External web research results (search results and page excerpts):\n"
        + web_context
        + "\n\n---\n\n"
        "Existing research notes for reference (what is already known):\n"
        + (recent_notes[:3000] if recent_notes else "None")
        + "\n\n---\n\n"
        "Respond with a markdown report titled '# Research Findings'. "
        "For each question in the research prompt, provide: (1) relevant external evidence found, "
        "(2) alternative perspectives or counterevidence, (3) whether this is genuinely new territory "
        "not already covered in the existing notes. Be specific, cite sources where available, "
        "and clearly flag what is new versus already known."
    )

    return chat_completion(
        _build_messages(AGENT_PROMPTS["researcher"], prompt),
        temperature=0.7,
    )


def generate_agent_outputs(
    iteration: int,
    framework: str,
    recent_notes: str,
    open_questions_text: str = "",
    on_progress: Optional[Callable[[str, str, str], None]] = None,
) -> Dict[str, str]:

    def progress(step: str, status: str, label: str):
        if on_progress:
            on_progress(step, status, label)

    topics = _derive_research_topics(open_questions_text)
    research_context = collect_research_context(topics, max_results=3)
    context = _build_context(iteration, framework, recent_notes, research_context)

    # Agent 1: Theorist
    progress("agent1", "running", "Agent 1 — Theorist")
    theory_prompt = (
        context
        + "\n\nRespond with a markdown-style theory note titled '# Theory'. "
        "Include sections for Hypothesis, Mechanism, and Implications."
    )
    theory = chat_completion(
        _build_messages(AGENT_PROMPTS["theory"], theory_prompt), temperature=0.8
    )
    progress("agent1", "done", "Agent 1 — Theorist")

    # Agent 2: Critic
    progress("agent2", "running", "Agent 2 — Critic")
    critique_prompt = (
        context
        + "\n\nHere is Agent 1's theory:\n" + theory
        + "\n\nRespond with a markdown critique titled '# Critique'. "
        "Include at least three weaknesses, at least one alternative explanation, and suggested refinements."
    )
    critique = chat_completion(
        _build_messages(AGENT_PROMPTS["critique"], critique_prompt), temperature=0.7
    )
    progress("agent2", "done", "Agent 2 — Critic")

    # Agent 3 — First pass: identify gaps and generate a focused research prompt
    progress("agent3_first", "running", "Agent 3 — Research Prompt")
    first_pass_prompt = (
        context
        + "\n\nAgent 1 theory:\n" + theory
        + "\n\nAgent 2 critique:\n" + critique
        + "\n\nExisting Agent 4 framework (already covered territory):\n"
        + (framework or "None yet.")
        + "\n\nDo NOT write the final synthesis yet. "
        "Identify what territory is genuinely NOT covered by the existing framework above, "
        "and output a focused research prompt titled '# Research Prompt'. "
        "Include exactly two sections:\n"
        "## Core Questions — 2 to 4 specific questions whose answers would most advance "
        "the theory beyond what is already in the framework.\n"
        "## Search Directions — 2 to 4 short, web-search-friendly phrases to find "
        "external evidence for those questions.\n"
        "Be specific. Avoid questions already answered in the existing framework."
    )
    research_prompt = chat_completion(
        _build_messages(AGENT_PROMPTS["synthesis"], first_pass_prompt), temperature=0.7
    )
    progress("agent3_first", "done", "Agent 3 — Research Prompt")

    # Agent 0: Researcher — explores web and notes based on Agent 3's research prompt
    progress("agent0", "running", "Agent 0 — Researcher")
    agent0_feedback = _run_agent0_researcher(research_prompt, recent_notes)
    progress("agent0", "done", "Agent 0 — Researcher")

    # Agent 3 — Final synthesis: integrates Agent 1/2 outputs with Agent 0's new findings
    progress("agent3_final", "running", "Agent 3 — Final Synthesis")
    final_synthesis_prompt = (
        context
        + "\n\nAgent 1 theory:\n" + theory
        + "\n\nAgent 2 critique:\n" + critique
        + "\n\nAgent 0 (Researcher) feedback report:\n" + agent0_feedback
        + "\n\nNow write the final synthesis. Respond with a markdown research note. "
        "Include sections '# Synthesis', '## Master Theory', and '## Open Questions'. "
        "The open questions must be grounded in Agent 0's new findings and should not "
        "repeat questions already addressed in the existing framework."
    )
    synthesis = chat_completion(
        _build_messages(AGENT_PROMPTS["synthesis"], final_synthesis_prompt), temperature=0.7
    )
    progress("agent3_final", "done", "Agent 3 — Final Synthesis")

    # Agent 4: Framework synthesizer
    progress("agent4", "running", "Agent 4 — Synthesizer")
    framework_prompt = (
        context
        + "\n\nExisting notes:\n" + synthesis
        + "\n\nRespond with a markdown framework document titled '# Agent 4 Framework'. "
        "Include a short overview, key principles, and a seed prompt for the next iteration."
    )
    framework_out = chat_completion(
        _build_messages(AGENT_PROMPTS["framework"], framework_prompt), temperature=0.7
    )
    progress("agent4", "done", "Agent 4 — Synthesizer")

    master_theory = "# Master Theory\n\n" + _extract_section(synthesis, "Master Theory")
    open_questions = "# Open Questions\n\n" + _extract_section(synthesis, "Open Questions")

    return {
        "theory": theory,
        "critique": critique,
        "research_prompt": research_prompt,
        "agent0_feedback": agent0_feedback,
        "synthesis": synthesis,
        "framework": framework_out,
        "master_theory": master_theory,
        "open_questions": open_questions,
    }
