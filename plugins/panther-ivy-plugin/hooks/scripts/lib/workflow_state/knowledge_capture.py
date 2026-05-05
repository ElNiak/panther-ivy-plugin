"""G6 candidate extraction, hashing, dedup, and per-candidate vote aggregation.

Pure library — no I/O side effects. Called from skills/ivy/SKILL.md Phase 1.5
G6 detection branch. See docs/superpowers/specs/2026-05-05-g0b-g6-design.md
for the design contract.
"""

from __future__ import annotations

import hashlib
import re

_SUMMARY_MAX = 200


def _canonical_summary(text: str) -> str:
    """Lowercase + whitespace-collapse for stable candidate_id hashing."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _extract_one(entry: dict) -> dict | None:
    """Return a candidate dict for ``entry``, or None if not candidate-eligible."""
    etype = entry.get("type")
    payload = entry.get("payload", {}) or {}

    if etype == "progress" and payload.get("kind") == "fix_attempt":
        summary = (
            payload.get("text")
            or f"fix_attempt key={payload.get('key')} attempt={payload.get('attempt')}"
        )
        evidence = [payload["key"]] if payload.get("key") else []
    elif etype == "decision":
        summary = payload.get("summary", "")
        evidence = []
    elif etype == "error":
        summary = payload.get("pattern", "")
        file_, line_ = payload.get("file"), payload.get("line")
        evidence = [f"{file_}:{line_}"] if file_ and line_ is not None else []
    elif etype == "gate_verdict" and payload.get("verdict") == "unsound":
        patterns = ",".join(payload.get("patterns", []))
        summary = f"{payload.get('gate', '')} unsound: {patterns}"
        evidence = []
    else:
        return None

    return {
        "source_event_type": etype,
        "source_event_ts": entry["ts"],
        "summary": (summary or "")[:_SUMMARY_MAX],
        "evidence_paths": evidence,
    }


def extract_candidates(
    journal: list[dict],
    since_ts: str,
    until_ts: str,
) -> list[dict]:
    """Extract G6 candidate records from journal events in [since_ts, until_ts].

    Args:
        journal: List of journal event dicts, each with ``ts``, ``type``,
            and ``payload``.
        since_ts: ISO timestamp lower bound (inclusive).
        until_ts: ISO timestamp upper bound (inclusive).

    Returns:
        List of candidate dicts with keys ``source_event_type``,
        ``source_event_ts``, ``summary``, and ``evidence_paths``.
    """
    out = []
    for entry in journal:
        ts = entry.get("ts", "")
        if ts < since_ts or ts > until_ts:
            continue
        cand = _extract_one(entry)
        if cand is None:
            continue
        out.append(cand)
    return out


def compute_candidate_id(candidate: dict) -> str:
    """Stable 12-char SHA-256 prefix over (type, canonical_summary, sorted(evidence)).

    ``source_event_ts`` is intentionally NOT included so near-identical candidates
    from different sessions hash identically and dedup correctly.

    Args:
        candidate: Candidate dict with ``source_event_type``, ``summary``,
            and ``evidence_paths`` keys.

    Returns:
        12-character lowercase hex string.
    """
    canonical = _canonical_summary(candidate.get("summary", ""))
    evidence = sorted(candidate.get("evidence_paths", []))
    ev_part = "|".join(evidence)
    body = f"{candidate.get('source_event_type', '')}|{canonical}|{ev_part}"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


def apply_dedup(candidates: list[dict], journal: list[dict]) -> list[dict]:
    """Drop candidates already captured in a prior ``knowledge_captured`` event.

    Args:
        candidates: List of candidate dicts produced by ``extract_candidates``.
        journal: Full journal event list to scan for prior
            ``knowledge_captured`` entries.

    Returns:
        Subset of ``candidates`` whose computed IDs have not been captured before.
    """
    seen = {
        entry["payload"].get("candidate_id")
        for entry in journal
        if entry.get("type") == "knowledge_captured"
    }
    seen.discard(None)
    return [c for c in candidates if compute_candidate_id(c) not in seen]


def aggregate_per_candidate_votes(
    votes_by_candidate: dict[str, list[str]],
) -> dict[str, str]:
    """Aggregate three KEEP/DROP/DEFER votes per candidate into a single verdict.

    Rules:
        - >=2 KEEP  -> KEEP
        - >=2 DROP  -> DROP
        - >=2 DEFER -> DEFER
        - 1-1-1 split -> DEFER (per design F-C5: asymmetric-vote convention).

    Args:
        votes_by_candidate: Mapping from candidate_id (str) to a list of
            exactly 3 vote strings, each one of ``KEEP``, ``DROP``, or ``DEFER``.

    Returns:
        Mapping from candidate_id to the aggregated verdict string.

    Raises:
        ValueError: If any candidate's vote list does not contain exactly 3 entries.
    """
    out = {}
    for cand_id, votes in votes_by_candidate.items():
        if len(votes) != 3:
            raise ValueError(
                f"candidate {cand_id} has {len(votes)} votes; expected exactly 3"
            )
        counts = {v: votes.count(v) for v in ("KEEP", "DROP", "DEFER")}
        winners = [v for v, c in counts.items() if c >= 2]
        out[cand_id] = winners[0] if winners else "DEFER"
    return out
