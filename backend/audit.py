"""Append-only audit trail at output/audit_trail.json.

The file is a JSON array of AuditRecord objects. Records are only ever
appended: each write re-reads the array under a file lock, adds one record,
and atomically replaces the file. If the existing file isn't a valid JSON
array, we refuse to write rather than overwrite it.
"""

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_ai import CallToolsNode, ModelRequestNode, UserPromptNode
from pydantic_core import to_jsonable_python

from models import AuditRecord, AuditStep

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
_LOCK_PATH = AUDIT_PATH.with_name(".audit_trail.lock")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def append(record: AuditRecord) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOCK_PATH, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        records: list[Any] = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size:
            records = json.loads(AUDIT_PATH.read_text())
            if not isinstance(records, list):
                raise RuntimeError(f"{AUDIT_PATH} is not a JSON array; refusing to overwrite it")
        records.append(record.model_dump(mode="json"))
        fd, tmp = tempfile.mkstemp(dir=AUDIT_PATH.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(records, f, indent=2)
        os.replace(tmp, AUDIT_PATH)


def _part(part: Any) -> dict[str, Any]:
    """Keep what an auditor needs from a message part; drop provider plumbing."""
    data = to_jsonable_python(part)
    keep = ("part_kind", "content", "tool_name", "args", "tool_call_id", "model_response", "id")
    return {k: data[k] for k in keep if data.get(k) not in (None, "", [])}


def step_from_node(step: int, node: Any) -> AuditStep | None:
    """Turn one node of the PydanticAI agent loop into an audit step."""
    if isinstance(node, UserPromptNode):
        prompt = node.user_prompt if isinstance(node.user_prompt, str) else to_jsonable_python(node.user_prompt)
        return AuditStep(step=step, node="user_prompt", at=now(), parts=[{"content": prompt}])
    if isinstance(node, ModelRequestNode):
        # System instructions are the agent's prompt file; it's named on the record instead of repeated here.
        parts = [_part(p) for p in node.request.parts if p.part_kind != "system-prompt"]
        return AuditStep(step=step, node="model_request", at=now(), parts=parts)
    if isinstance(node, CallToolsNode):
        return AuditStep(step=step, node="model_response", at=now(),
                         parts=[_part(p) for p in node.model_response.parts])
    return None
