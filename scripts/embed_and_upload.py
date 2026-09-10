"""
Admin/provisioning script — NOT run by candidates. Run once per candidate
environment (or once against a shared bucket, per your isolation model)
before the sitting opens, so the KB is already loaded when the candidate
logs in.

Reads data/*.md, embeds each document with the Bedrock Titan embedding
model, and writes the resulting vectors into an S3 Vectors index with
metadata (doc_id, title, status, effective_date, source, text). This is
exactly the metadata the retrieval fault (FC-03) leaves unfiltered.

Usage:
    python scripts/embed_and_upload.py \
        --bucket context-eng-kb-vectors \
        --index policy-docs-index \
        --data-dir data/
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re

import boto3

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
EMBED_MODEL_ID = os.environ.get("EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")


def parse_doc(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    m = FRONT_MATTER_RE.match(raw)
    meta, body = {}, raw
    if m:
        fm_block, body = m.group(1), m.group(2)
        for line in fm_block.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return {
        "doc_id": meta.get("doc_id", os.path.basename(path)),
        "title": meta.get("title", os.path.basename(path)),
        "status": meta.get("status", "unknown"),
        "effective_date": meta.get("effective_date", ""),
        "source": meta.get("source", ""),
        "text": body.strip(),
    }


def embed(bedrock_runtime, text: str) -> list[float]:
    resp = bedrock_runtime.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps({"inputText": text}),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(resp["body"].read())
    return payload["embedding"]


def ensure_bucket_and_index(s3vectors, bucket: str, index: str, dimension: int):
    try:
        s3vectors.create_vector_bucket(vectorBucketName=bucket)
    except s3vectors.exceptions.ConflictException:
        pass  # already exists

    try:
        s3vectors.create_index(
            vectorBucketName=bucket,
            indexName=index,
            dimension=dimension,
            distanceMetric="cosine",
            dataType="float32",
            metadataConfiguration={
                # keep full document text out of the filterable index;
                # it's still stored and returned, just not used for filters
                "nonFilterableMetadataKeys": ["text"]
            },
        )
    except s3vectors.exceptions.ConflictException:
        pass  # already exists


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--region", default=None)
    args = parser.parse_args()

    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    bedrock_runtime = session.client("bedrock-runtime")
    s3vectors = session.client("s3vectors")

    docs = [parse_doc(p) for p in sorted(glob.glob(os.path.join(args.data_dir, "*.md")))]
    if not docs:
        raise SystemExit(f"No .md documents found in {args.data_dir}")

    print(f"Embedding {len(docs)} documents with {EMBED_MODEL_ID} ...")
    vectors = []
    dimension = None
    for doc in docs:
        vec = embed(bedrock_runtime, f"{doc['title']}\n{doc['text']}")
        dimension = dimension or len(vec)
        vectors.append(
            {
                "key": doc["doc_id"],
                "data": {"float32": vec},
                "metadata": {
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "status": doc["status"],
                    "effective_date": doc["effective_date"],
                    "source": doc["source"],
                    "text": doc["text"],
                },
            }
        )
        print(f"  embedded {doc['doc_id']} ({doc['status']}, {doc['effective_date']})")

    print(f"Ensuring vector bucket '{args.bucket}' and index '{args.index}' exist ...")
    ensure_bucket_and_index(s3vectors, args.bucket, args.index, dimension)

    print(f"Uploading {len(vectors)} vectors ...")
    s3vectors.put_vectors(
        vectorBucketName=args.bucket,
        indexName=args.index,
        vectors=vectors,
    )
    print("Done. Provisioned metadata fields (status, effective_date) are")
    print("filterable but NOT applied by lambda_app/retrieval.py — that is")
    print("the seeded FC-03 fault (see internal/ANSWER_KEY.md).")


if __name__ == "__main__":
    main()
