"""Helpers for keeping a bounded history of source collection quality snapshots."""
from copy import deepcopy

MAX_SNAPSHOTS = 30


def append_snapshot(history, report, captured_at, limit=MAX_SNAPSHOTS):
    if not isinstance(history, dict) or not isinstance(history.get("snapshots", []), list):
        raise ValueError("history must contain a snapshots array")
    if not isinstance(report, dict) or not isinstance(report.get("sources"), list):
        raise ValueError("report must contain a sources array")
    count = report.get("candidate_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("candidate_count must be a non-negative integer")
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")

    snapshots = deepcopy(history.get("snapshots", []))
    snapshots.append({
        "captured_at": captured_at,
        "candidate_count": count,
        "source_count": len(report["sources"]),
        "sources": deepcopy(report["sources"]),
    })
    return {"snapshots": snapshots[-limit:]}
