from __future__ import annotations

import os

import boto3

TABLE_NAME = os.environ.get("SESSION_TABLE_NAME", "context-eng-sessions")

_table = None


def _get_table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(TABLE_NAME)
    return _table


def get_history(session_id: str) -> list[dict]:
    resp = _get_table().get_item(Key={"session_id": session_id})
    item = resp.get("Item")
    if not item:
        return []
    return item.get("history", [])


def append_turn(session_id: str, role: str, content: str) -> None:
    history = get_history(session_id)

    # --- FAULT: no cap on `history` length before appending, and the
    # full (unbounded) list is written back on every call.
    history.append({"role": role, "content": content})

    _get_table().put_item(Item={"session_id": session_id, "history": history})


def reset(session_id: str) -> None:
    _get_table().delete_item(Key={"session_id": session_id})
