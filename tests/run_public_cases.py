"""
Runs the public test cases against a deployed API Gateway endpoint and
prints raw responses so a candidate can eyeball behaviour. This is NOT an
auto-grader (the withheld set and rubric are held outside the candidate
environment) — it just exercises the endpoint contract.

Usage:
    export APP_BASE_URL=https://<api-id>.execute-api.<region>.amazonaws.com
    python tests/run_public_cases.py
"""
from __future__ import annotations

import json
import os

import requests

BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000")
CASES_PATH = os.path.join(os.path.dirname(__file__), "public_cases.json")


def main():
    with open(CASES_PATH) as f:
        cases = json.load(f)

    for case in cases:
        print(f"\n=== {case['case_id']} ===")
        print(case["description"])
        session_id = case["session_id"]
        requests.post(f"{BASE_URL}/reset", json={"session_id": session_id})

        for turn in case["turns"]:
            resp = requests.post(
                f"{BASE_URL}/chat",
                json={"session_id": session_id, "query": turn["query"]},
            )
            data = resp.json()
            print(f"\n> {turn['query']}")
            print(f"answer: {data.get('answer')}")
            print(f"retrieved_doc_ids: {data.get('retrieved_doc_ids')}")
            print(f"retrieved_scores: {data.get('retrieved_scores')}")
            print(f"history_turns: {data.get('history_turns')}")
            print(f"prompt_chars: {data.get('prompt_chars')}")

        print("\nChecks to verify manually:")
        for check in case["checks"]:
            print(f"  - {check}")


if __name__ == "__main__":
    main()
