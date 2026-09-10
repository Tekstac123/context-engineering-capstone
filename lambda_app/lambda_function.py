from __future__ import annotations

import json

import agent, memory

RESPONSE_HEADERS = {"Content-Type": "application/json"}


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": RESPONSE_HEADERS,
        "body": json.dumps(body),
    }


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")

    if method == "GET" and path.rstrip("/").endswith("/health"):
        return _response(200, {"status": "ok"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "invalid JSON body"})

    if method == "POST" and path.rstrip("/").endswith("/reset"):
        session_id = body.get("session_id")
        if not session_id:
            return _response(400, {"error": "session_id is required"})
        memory.reset(session_id)
        return _response(200, {"status": "reset"})

    if method == "POST" and path.rstrip("/").endswith("/chat"):
        session_id = body.get("session_id")
        query = body.get("query")
        if not session_id or not query:
            return _response(400, {"error": "session_id and query are required"})
        result = agent.handle_turn(session_id, query)
        return _response(200, result)

    return _response(404, {"error": f"no route for {method} {path}"})
