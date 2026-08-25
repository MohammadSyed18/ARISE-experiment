"""Portable experiment archives verified by digest and deterministic scenario replay."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from .runner import run_data
from .validation import validate_scenario

MAX_ARCHIVE_BYTES = 10_000_000


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf8")


def create_archive(scenario, *, policy="revision"):
    checked = validate_scenario(deepcopy(scenario))
    result = run_data(checked, policy=policy)
    payload = {"schema": 1, "policy": policy, "scenario": checked, "result": result}
    return {"payload": payload, "sha256": sha256(canonical(payload)).hexdigest()}


def verify_archive(value):
    if not isinstance(value, dict) or set(value) != {"payload", "sha256"}:
        raise ValueError("invalid experiment archive envelope")
    payload = value["payload"]
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != 1
        or set(payload) != {"schema", "policy", "scenario", "result"}
    ):
        raise ValueError("unsupported experiment archive schema")
    if value["sha256"] != sha256(canonical(payload)).hexdigest():
        raise ValueError("experiment archive digest mismatch")
    replay = run_data(payload["scenario"], policy=payload["policy"])
    if canonical(replay) != canonical(payload["result"]):
        raise ValueError("experiment archive result does not match replay")
    return deepcopy(replay)


def save_archive(path, archive):
    verify_archive(archive)
    raw = canonical(archive)
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("experiment archive exceeds 10 MB")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_archive(path):
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_ARCHIVE_BYTES + 1)
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("experiment archive exceeds 10 MB")
    value = json.loads(raw)
    verify_archive(value)
    return value


def compare_archives(left, right):
    """A structural change report; metrics retain their fixture-only interpretation."""
    a, b = verify_archive(left), verify_archive(right)
    left_claims = {item["id"]: item for item in a["graph"]["claims"]}
    right_claims = {item["id"]: item for item in b["graph"]["claims"]}
    return {
        "same_scenario": canonical(left["payload"]["scenario"])
        == canonical(right["payload"]["scenario"]),
        "policies": [a["policy"], b["policy"]],
        "added_claims": sorted(set(right_claims) - set(left_claims)),
        "removed_claims": sorted(set(left_claims) - set(right_claims)),
        "changed_claims": [
            key
            for key in sorted(set(left_claims) & set(right_claims))
            if canonical(left_claims[key]) != canonical(right_claims[key])
        ],
        "metrics": {"left": a["metrics"], "right": b["metrics"]},
    }
