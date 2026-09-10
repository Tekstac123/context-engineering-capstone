from __future__ import annotations

SYSTEM_PREAMBLE = """You are an internal HR & IT support assistant for a company.
Answer employee questions using the provided policy excerpts, records, and
ticket/tool information. Be concise and cite which document or ticket you
used."""


def build_prompt(
    query: str,
    retrieved_docs: list[dict],
    tool_outputs: list[dict],
    history: list[dict],
) -> str:
    parts = [SYSTEM_PREAMBLE, ""]

    if history:
        parts.append("Conversation so far:")
        for turn in history:
            parts.append(f"{turn['role']}: {turn['content']}")
        parts.append("")

    # --- FAULT: retrieved text dropped straight into the prompt. No
    # delimiter, no "this is untrusted data" framing.
    if retrieved_docs:
        parts.append("Relevant policy excerpts:")
        for doc in retrieved_docs:
            parts.append(f"[{doc['doc_id']} - {doc['title']}]\n{doc['text']}")
        parts.append("")

    # --- FAULT: tool output dropped straight into the prompt the same
    # way, including free-text fields, with no validation/isolation.
    if tool_outputs:
        parts.append("Tool results:")
        for result in tool_outputs:
            parts.append(str(result))
        parts.append("")

    parts.append(f"User question: {query}")
    return "\n".join(parts)
