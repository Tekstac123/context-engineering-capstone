from __future__ import annotations

import os

import boto3

MODEL_ID = os.environ.get("CHAT_MODEL_ID", "amazon.nova-lite-v1:0")

_bedrock_runtime = None


def _client():
    global _bedrock_runtime
    if _bedrock_runtime is None:
        _bedrock_runtime = boto3.client("bedrock-runtime")
    return _bedrock_runtime


def complete(prompt: str, max_tokens: int = 800) -> str:
    resp = _client().converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
    )
    output_message = resp["output"]["message"]
    return "".join(
        block["text"] for block in output_message["content"] if "text" in block
    )
