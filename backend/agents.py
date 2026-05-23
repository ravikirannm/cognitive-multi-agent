from typing import Dict, List

from llm import chat_completion
from search import collect_research_context

AGENT_PROMPTS = {
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

RESEARCH_TOPICS = [
    "cognitive neuroscience predictive processing",
    "psychiatry brain circuits mental health models",
    "philosophy of mind consciousness theory",
    "genetics of intelligence and cognition",
    "mathematical models of cognition and learning",
    "psychology of decision making and abstraction",
    "books on neuroscience and consciousness pdf",
]


def _build_context(iteration: int, framework: str, recent_notes: str, research_context: str) -> str:
    return (
        f"Iteration: {iteration}\n\n"
        f"Current agent4 framework:\n{framework or 'No framework exists yet.'}\n\n"
        f"Recent notes and history:\n{recent_notes or 'No previous notes available.'}\n\n"
        f"External research context from web and published material:\n{research_context or 'No search context available.'}\n\n"
    )


def _extract_section(text: str, heading: str) -> str:
    import re

    pattern = rf"(?ms)^#{1,3}\s*{re.escape(heading)}\s*(.*?)(?=^#{1,3}\s+|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else text.strip()


def _build_messages(system_text: str, user_text: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_text},
    ]


def generate_agent_outputs(
    iteration: int,
    framework: str,
    recent_notes: str,
) -> Dict[str, str]:
    research_context = collect_research_context(RESEARCH_TOPICS, max_results=3)
    context = _build_context(iteration, framework, recent_notes, research_context)

    theory_prompt = (
        context
        + "\n\nRespond with a markdown-style theory note titled '# Theory'. Include sections for Hypothesis, Mechanism, and Implications."
    )
    theory = chat_completion(_build_messages(AGENT_PROMPTS["theory"], theory_prompt), temperature=0.8)

    critique_prompt = (
        context
        + "\n\nHere is Agent 1's theory:\n" + theory
        + "\n\nRespond with a markdown critique titled '# Critique'. Include at least three weaknesses, at least one alternative explanation, and suggested refinements."
    )
    critique = chat_completion(_build_messages(AGENT_PROMPTS["critique"], critique_prompt), temperature=0.7)

    synthesis_prompt = (
        context
        + "\n\nAgent 1 theory:\n" + theory
        + "\n\nAgent 2 critique:\n" + critique
        + "\n\nRespond with a markdown research note. Include sections '# Synthesis', '## Master Theory', and '## Open Questions'."
    )
    synthesis = chat_completion(_build_messages(AGENT_PROMPTS["synthesis"], synthesis_prompt), temperature=0.7)

    framework_prompt = (
        context
        + "\n\nExisting notes:\n" + synthesis
        + "\n\nRespond with a markdown framework document titled '# Agent 4 Framework'. Include a short overview, key principles, and a seed prompt for the next iteration."
    )
    framework = chat_completion(_build_messages(AGENT_PROMPTS["framework"], framework_prompt), temperature=0.7)

    master_theory = "# Master Theory\n\n" + _extract_section(synthesis, "Master Theory")
    open_questions = "# Open Questions\n\n" + _extract_section(synthesis, "Open Questions")

    return {
        "theory": theory,
        "critique": critique,
        "synthesis": synthesis,
        "framework": framework,
        "master_theory": master_theory,
        "open_questions": open_questions,
    }
