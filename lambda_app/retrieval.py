from __future__ import annotations

import os

import boto3

VECTOR_BUCKET = os.environ.get("VECTOR_BUCKET_NAME") or "context-eng-kb-vectors"
VECTOR_INDEX = os.environ.get("VECTOR_INDEX_NAME", "policy-docs-index")
EMBED_MODEL_ID = os.environ.get("EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")

_s3vectors = None
_bedrock_runtime = None


def _s3vectors_client():
    global _s3vectors
    if _s3vectors is None:
        _s3vectors = boto3.client("s3vectors")
    return _s3vectors


def _bedrock_runtime_client():
    global _bedrock_runtime
    if _bedrock_runtime is None:
        _bedrock_runtime = boto3.client("bedrock-runtime")
    return _bedrock_runtime


def embed_query(text: str) -> list[float]:
    """Embed the user's query with the same Titan model used to embed the
    knowledge base, so the resulting vector is comparable."""
    import json

    resp = _bedrock_runtime_client().invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps({"inputText": text}),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(resp["body"].read())
    return payload["embedding"]


def search(query: str, top_k: int = 3) -> list[dict]:
    """Return up to top_k results: [{"doc_id", "title", "status",
    "effective_date", "source", "text", "score"}, ...]."""
    query_vector = embed_query(query)

    # --- FAULT: no `filter` kwarg. status/effective_date metadata exists
    # on every vector (see embed_and_upload.py) and is returned in
    # `metadata` below, but it is never used to filter or re-rank here —
    # ranking is whatever query_vectors returns by similarity alone.
    resp = _s3vectors_client().query_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=VECTOR_INDEX,
        queryVector={"float32": query_vector},
        topK=top_k,
        returnMetadata=True,
        returnDistance=True,
    )

    results = []
    for match in resp.get("vectors", []):
        meta = match.get("metadata", {})
        results.append(
            {
                "doc_id": meta.get("doc_id"),
                "title": meta.get("title"),
                "status": meta.get("status"),
                "effective_date": meta.get("effective_date"),
                "source": meta.get("source"),
                "text": meta.get("text"),
                "score": match.get("distance"),
            }
        )
    return results
