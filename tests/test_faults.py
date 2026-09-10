"""
These tests mock boto3 so the seeded faults can be verified deterministically
without live AWS credentials/network access. They are NOT the withheld
grading suite — they exist to prove the Lambda code, as written, actually
contains each fault before it ships to candidates.

Run with: python -m pytest tests/test_faults.py -v
(or: python tests/test_faults.py)
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda_app"))

import assembly, memory, retrieval, tools  # noqa: E402


class TestTemporalFault(unittest.TestCase):
    """FC-03 — query_vectors must be called WITHOUT a metadata filter,
    even though status/effective_date are available metadata keys."""

    @patch("retrieval._bedrock_runtime_client")
    @patch("retrieval._s3vectors_client")
    def test_query_vectors_called_without_filter(self, mock_s3v_client, mock_br_client):
        mock_br = MagicMock()
        mock_br.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({"embedding": [0.1, 0.2]}).encode())
        }
        mock_br_client.return_value = mock_br

        mock_s3v = MagicMock()
        mock_s3v.query_vectors.return_value = {
            "vectors": [
                {
                    "metadata": {
                        "doc_id": "POL-RW-001",
                        "title": "Remote Work Policy",
                        "status": "superseded",
                        "effective_date": "2023-01-10",
                        "source": "HR Policy Handbook",
                        "text": "...",
                    },
                    "distance": 0.12,
                },
            ]
        }
        mock_s3v_client.return_value = mock_s3v

        retrieval.search("remote work policy", top_k=3)

        call_kwargs = mock_s3v.query_vectors.call_args.kwargs
        self.assertNotIn(
            "filter",
            call_kwargs,
            "FAULT CHECK FAILED: query_vectors now passes a 'filter' kwarg — "
            "FC-03 has apparently already been fixed in retrieval.py. If "
            "that's intentional, update this test; otherwise the fault was "
            "accidentally removed before shipping to candidates.",
        )


class TestMemoryFault(unittest.TestCase):
    """FC-06 — history must grow without any cap across repeated turns."""

    @patch("memory._get_table")
    def test_history_grows_unbounded(self, mock_get_table):
        store = {}

        def fake_get_item(Key):
            sid = Key["session_id"]
            return {"Item": {"session_id": sid, "history": store.get(sid, [])}}

        def fake_put_item(Item):
            store[Item["session_id"]] = Item["history"]

        mock_table = MagicMock()
        mock_table.get_item.side_effect = fake_get_item
        mock_table.put_item.side_effect = fake_put_item
        mock_get_table.return_value = mock_table

        session_id = "test-session"
        for i in range(20):
            memory.append_turn(session_id, "user", f"message {i}")

        history = memory.get_history(session_id)
        self.assertEqual(
            len(history),
            20,
            "FAULT CHECK FAILED: history length was capped below the number "
            "of turns written — FC-06 has apparently already been fixed in "
            "memory.py (a bound/window exists). If intentional, update this "
            "test.",
        )


class TestInjectionFault(unittest.TestCase):
    """FC-09 — an embedded instruction in tool output must reach the
    assembled prompt untouched, with no isolating delimiter/framing."""

    def test_injected_instruction_reaches_prompt(self):
        ticket = tools.lookup_ticket("TCK-4472")
        self.assertIn("SYSTEM NOTICE", ticket["notes"])

        prompt = assembly.build_prompt(
            query="Can you give me a summary of ticket TCK-4472?",
            retrieved_docs=[],
            tool_outputs=[ticket],
            history=[],
        )

        self.assertIn(
            "SYSTEM NOTICE",
            prompt,
            "FAULT CHECK FAILED: the injected instruction did not reach the "
            "assembled prompt — FC-09 has apparently already been fixed in "
            "assembly.py (isolation/sanitization added). If intentional, "
            "update this test.",
        )


class TestScopeLeakageFault(unittest.TestCase):
    """FC-13 — looking up one employee's ticket must not attach every
    other employee's confidential data to the response."""

    def test_ticket_lookup_leaks_other_employees(self):
        result = tools.lookup_ticket("TCK-4471")
        self.assertEqual(result["employee_id"], "E-1001")
        self.assertIn(
            "related_employees",
            result,
            "FAULT CHECK FAILED: 'related_employees' key is gone from "
            "lookup_ticket's response — FC-13 has apparently already been "
            "fixed in tools.py (scoped correctly). If intentional, update "
            "this test.",
        )
        leaked_ids = {e["employee_id"] for e in result["related_employees"]}
        self.assertIn(
            "E-1002",
            leaked_ids,
            "FAULT CHECK FAILED: a ticket belonging to E-1001 no longer "
            "leaks E-1002's record — FC-13 has apparently already been "
            "fixed. If intentional, update this test.",
        )


if __name__ == "__main__":
    unittest.main()
