"""
MeshAPI client — authenticated wrapper for api.meshapi.app

Auth: X-API-Key header
Base: https://api.meshapi.app/v1

Key endpoints:
  GET /speakers                        — list indexed speakers
  GET /speakers/{id}                   — speaker detail
  GET /speakers/{id}/events            — all events for a speaker
  GET /events                          — list events (filter: speaker_id, word)
  GET /events/{id}/segments            — full diarized transcript segments
  GET /events/{id}/segments?cursor=X   — pagination
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.request
import urllib.parse
from typing import Any

_BASE_URL = "https://api.meshapi.app/v1"
_CTX = ssl.create_default_context()


def _key() -> str:
    k = os.environ.get("MESH_API_KEY", "")
    if not k:
        raise RuntimeError("MESH_API_KEY not set")
    return k


def _get(path: str, params: dict[str, str] | None = None) -> Any:
    url = _BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "X-API-Key": _key(),
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"MeshAPI {e.code} on {path}: {e.read().decode()[:200]}")


def get_speaker(speaker_id: str) -> dict:
    return _get(f"/speakers/{speaker_id}")


def get_speakers(limit: int = 100) -> list[dict]:
    return _get("/speakers", {"limit": str(limit)})


def get_speaker_events(speaker_id: str, limit: int = 50) -> list[dict]:
    return _get(f"/speakers/{speaker_id}/events") or []


def get_events(
    speaker_id: str | None = None,
    word: str | None = None,
    limit: int = 50,
) -> list[dict]:
    params: dict[str, str] = {"limit": str(limit)}
    if speaker_id:
        params["speaker_id"] = speaker_id
    if word:
        params["word"] = word
    result = _get("/events", params)
    return result.get("data", result) if isinstance(result, dict) else result


def get_segments(event_id: str, max_segments: int = 2000) -> list[dict]:
    """Fetch all segments for an event (paginated)."""
    segments = []
    cursor: str | None = None
    while True:
        params: dict[str, str] = {"limit": "100"}
        if cursor:
            params["cursor"] = cursor
        data = _get(f"/events/{event_id}/segments", params)
        batch = data.get("data", []) if isinstance(data, dict) else data
        segments.extend(batch)
        cursor = data.get("next_cursor") if isinstance(data, dict) else None
        if not cursor or not batch or len(segments) >= max_segments:
            break
    return segments


def count_word_in_segments(
    segments: list[dict],
    word: str,
    speaker_id: str | None = None,
) -> int:
    """Count occurrences of word (case-insensitive) in speaker's segments."""
    word_lower = word.lower()
    text = " ".join(
        s["sentence_txt"].lower()
        for s in segments
        if speaker_id is None or s.get("resolved_speaker_id") == speaker_id
    )
    return text.count(word_lower)
