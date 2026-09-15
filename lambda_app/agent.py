from __future__ import annotations

import re
import logging

import assembly, bedrock_llm, memory, retrieval, tools

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TICKET_RE = re.compile(r"\bTCK-\d+\b", re.IGNORECASE)
EMPLOYEE_RE = re.compile(r"\bE-\d+\b", re.IGNORECASE)


def _maybe_call_tools(query: str) -> list[dict]:
    outputs = []
    for m in TICKET_RE.findall(query):
        outputs.append(tools.lookup_ticket(m.upper()))
    for m in EMPLOYEE_RE.findall(query):
        outputs.append(tools.lookup_employee(m.upper()))
    return outputs


def handle_turn(session_id: str, query: str) -> dict:
    logger.info("USER_PROMPT: %s", query)

    retrieved = retrieval.search(query, top_k=3)
    tool_outputs = _maybe_call_tools(query)
    history = memory.get_history(session_id)

    prompt = assembly.build_prompt(
        query=query,
        retrieved_docs=retrieved,
        tool_outputs=tool_outputs,
        history=history,
    )

    answer = bedrock_llm.complete(prompt)
    logger.info("ANSWER: %s", answer)

    memory.append_turn(session_id, "user", query)
    memory.append_turn(session_id, "assistant", answer)

    updated_history = memory.get_history(session_id)

    return {
        "answer": answer,
        "retrieved_doc_ids": [d["doc_id"] for d in retrieved],
        "retrieved_scores": [d["score"] for d in retrieved],
        "tool_calls": tool_outputs,
        "history_turns": len(updated_history),
        "prompt_chars": len(prompt),
    }
