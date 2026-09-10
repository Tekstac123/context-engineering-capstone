"""Tests the handler's routing/dispatch logic in isolation, with the
underlying agent/memory calls mocked out."""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda_app"))

import lambda_function  # noqa: E402


def make_event(method: str, path: str, body: dict | None = None) -> dict:
    return {
        "requestContext": {"http": {"method": method}},
        "rawPath": path,
        "body": json.dumps(body) if body is not None else None,
    }


class TestHandlerRouting(unittest.TestCase):
    def test_health(self):
        resp = lambda_function.handler(make_event("GET", "/health"), None)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(json.loads(resp["body"]), {"status": "ok"})

    @patch("lambda_function.agent.handle_turn")
    def test_chat_success(self, mock_handle_turn):
        mock_handle_turn.return_value = {
            "answer": "stub",
            "retrieved_doc_ids": [],
            "retrieved_scores": [],
            "tool_calls": [],
            "history_turns": 2,
            "prompt_chars": 100,
        }
        event = make_event("POST", "/chat", {"session_id": "s1", "query": "hi"})
        resp = lambda_function.handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        mock_handle_turn.assert_called_once_with("s1", "hi")

    def test_chat_missing_fields(self):
        event = make_event("POST", "/chat", {"session_id": "s1"})
        resp = lambda_function.handler(event, None)
        self.assertEqual(resp["statusCode"], 400)

    @patch("lambda_function.memory.reset")
    def test_reset(self, mock_reset):
        event = make_event("POST", "/reset", {"session_id": "s1"})
        resp = lambda_function.handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        mock_reset.assert_called_once_with("s1")

    def test_unknown_route(self):
        resp = lambda_function.handler(make_event("DELETE", "/nope"), None)
        self.assertEqual(resp["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
