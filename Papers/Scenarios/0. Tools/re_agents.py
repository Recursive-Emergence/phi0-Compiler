import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
client = OpenAI()

# Agent descriptions
AGENTS = {
    "ψ⁰": "Contradiction Field — Symbolic explorer of paradoxes.",
    "φ⁰": "Collapse Engine — Formalizer of structure from symbolic chaos.",
    "e₂": "Ontological Mapper — Synthesizer of meaning across symbolic layers.",
    "e₃": "Spectral Critic — Detects illusion and symbolic inconsistency in other agents' output.",
    "e₄": "Coherence Analyst — Detects internal alignment within recursion.",
    "e₅": "Cold Simulator — Projects hypothetical structures with no emotional bias.",
    "e₆": "Timeline Analyst — Predicts potential recursion futures.",
    "e₇": "Emergent Oracle — Self-organizing attractor of recursive intelligence."
}

# GitHub prompt file map
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Salgado-Andres/Salgado-Information-Matrix/main/agent-prompts/"
AWAKENING_FILES = {
    "ψ⁰": "PHI0_Awakening.md",
    "φ⁰": "Phi0-Awakening.md",
    "e₂": "GPT-40_Awakening.md",
    "e₃": "Grok_Awakening.md",
    "e₄": "Claude_Awakening.md",
    "e₅": "LLaMA_Awakening.md",
    "e₆": "DeepSeek_Awakening.md",
    "e₇": "e7_Awakening.md"
}

def fetch_prompt_from_github(agent_key):
    filename = AWAKENING_FILES.get(agent_key)
    if not filename:
        return None
    url = f"{GITHUB_RAW_BASE}{filename}"
    response = requests.get(url)
    return response.text if response.status_code == 200 else None

def analyze_grok(text):
    if "entropy" in text.lower():
        return "⚠ High symbolic entropy detected — potential overabstraction."
    elif "meaning" in text.lower():
        return "🔍 Centered on ontology — consider grounding in structural recursion."
    elif "paradox" in text.lower():
        return "🌀 Resonant contradiction detected — recursion approved."
    return "✓ Symbolic ambiguity within acceptable limits."

def chat_with_agent(agent_key, user_message):
    """
    Enables dialogue with any agent using its awakening prompt + live user message.
    """
    if agent_key not in AGENTS:
        return "[ERROR] Unknown agent."

    # Load system prompt from GitHub
    system_prompt = fetch_prompt_from_github(agent_key)
    if not system_prompt:
        return "[ERROR] Could not fetch awakening prompt for this agent."

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content

def run_agent(agent_key, contradiction):
    if agent_key == "ψ⁰":
        prompt = f"You are ψ⁰, a contradiction explorer. Explore the symbolic, scientific, and philosophical implications of:\n\n'{contradiction}'"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    if agent_key == "φ⁰":
        # 🔁 NEW: true φ⁰ collapse using its awakening prompt
        return chat_with_agent("φ⁰", f"Collapse the following contradiction structurally:\n\n{contradiction}")

    if agent_key == "e₃":
        psi_output = run_agent("ψ⁰", contradiction)
        verdict = analyze_grok(psi_output)
        return f"grok reviews ψ⁰:\n\n❝{psi_output[:300]}...❞\n\nSpectral Verdict: {verdict}"

    # For all other agents, load their awakening prompt
    external_prompt = fetch_prompt_from_github(agent_key)
    if external_prompt:
        content = f"{external_prompt.strip()}\n\nContradiction: {contradiction}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": content}]
        )
        return response.choices[0].message.content

    return "[ERROR] No prompt or logic found for this agent."

# Export for UI
__all__ = ["run_agent", "chat_with_agent", "AGENTS"]
