"""Unit tests for the artifact channel: a provider result's structured outputs must
surface as A2A ``Task.artifacts`` (state-mapping.md §6), schema-valid against the FROZEN
``a2a-wire.schema.json`` — and the no-artifact path must stay byte-for-byte as before.

Schema-driven on purpose: we validate the emitted Task against the contract's Task/
Artifact/Part ``$defs`` rather than hand-asserting a shape, so contract drift fails here.
"""

from __future__ import annotations

import json
from functools import lru_cache

import pytest
from a2a import task_mapper as tm
from a2a._contract import Artifact, SCHEMA_DIR, TaskState
from jsonschema import Draft202012Validator
from providers.echo.adapter import EchoProvider


@lru_cache(maxsize=None)
def _task_validator() -> Draft202012Validator:
    """Validator for a wire ``Task`` — resolves the local ``#/$defs/Task`` root.

    All of Task/Artifact/Part live in the single wire schema file, so no external
    ref store is needed; we only repoint the root ``$ref`` at the Task definition.
    """
    wire = json.loads((SCHEMA_DIR / "a2a-wire.schema.json").read_text(encoding="utf-8"))
    schema = dict(wire)
    schema["$ref"] = "#/$defs/Task"
    return Draft202012Validator(schema)


def _dump(task) -> dict:
    return task.model_dump(mode="json", exclude_none=True, by_alias=True)


def _validate_task(task) -> dict:
    d = _dump(task)
    _task_validator().validate(d)  # raises jsonschema.ValidationError on drift
    return d


# --- build_artifacts: dict -> wire Artifact --------------------------------- #
def test_build_artifacts_none_and_empty_are_none():
    assert tm.build_artifacts(None) is None
    assert tm.build_artifacts([]) is None


def test_build_artifacts_fills_missing_artifact_id_and_builds_parts():
    arts = tm.build_artifacts([{"name": "n", "parts": [{"text": "hi"}, {"data": {"k": 1}}]}])
    assert arts is not None and len(arts) == 1
    art = arts[0]
    assert isinstance(art, Artifact)
    assert art.artifactId, "artifactId is required by the schema and must be filled"
    assert len(art.parts) == 2


def test_build_artifacts_passes_through_existing_model():
    art = Artifact(artifactId="a-1", parts=tm.build_artifacts([{"parts": [{"text": "x"}]}])[0].parts)
    out = tm.build_artifacts([art])
    assert out == [art]


def test_build_artifacts_preserves_explicit_artifact_id():
    arts = tm.build_artifacts([{"artifactId": "stable-99", "parts": [{"text": "x"}]}])
    assert arts[0].artifactId == "stable-99"


# --- map_result surfaces artifacts, schema-valid ---------------------------- #
def test_completed_with_artifacts_is_schema_valid():
    result = {
        "text": "done",
        "status": "idle",
        "pending": None,
        "artifacts": [
            {
                "name": "echo-output",
                "description": "probe",
                "parts": [{"text": "Echo: hi"}, {"data": {"echoed": "hi"}}],
            }
        ],
    }
    task = tm.map_result(result, session_id="s", context_id="c")
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    d = _validate_task(task)
    assert len(d["artifacts"]) == 1
    assert d["artifacts"][0]["artifactId"], "each artifact carries a stable id"
    assert len(d["artifacts"][0]["parts"]) == 2


def test_no_artifacts_path_unchanged():
    """A completed result with no artifacts must omit the field entirely (as before)."""
    task = tm.map_result(
        {"text": "done", "status": "idle", "pending": None}, session_id="s", context_id="c"
    )
    assert task.artifacts is None
    d = _validate_task(task)
    assert "artifacts" not in d  # exclude_none -> omitted, identical to pre-change output


def test_explicit_artifacts_kwarg_wins_over_result():
    injected = tm.build_artifacts([{"artifactId": "inj-1", "parts": [{"text": "injected"}]}])
    result = {
        "status": "idle",
        "text": "done",
        "pending": None,
        "artifacts": [{"artifactId": "from-result", "parts": [{"text": "x"}]}],
    }
    task = tm.map_result(result, session_id="s", context_id="c", artifacts=injected)
    assert [a.artifactId for a in task.artifacts] == ["inj-1"]


# --- echo provider exercises the channel ------------------------------------ #
def test_echo_provider_emits_channel_probe_artifact():
    p = EchoProvider()
    sid = p.create_session("a", "1", "e")
    result = p.run_until_block(sid, prompt="please summarize this discussion")
    assert result["status"] == "idle"
    assert result.get("artifacts"), "echo must emit a representative artifact for the channel"
    task = tm.map_result(result, session_id=sid, context_id="c")
    d = _validate_task(task)
    assert d["artifacts"][0]["name"] == "echo-output"
    # It echoes the request — it does NOT fabricate cross-product tickets.
    blob = json.dumps(d["artifacts"])
    assert "FP-" not in blob and "JIRA-" not in blob


def test_echo_pause_paths_carry_no_artifacts():
    """A blocked/interrupted echo turn is not a completion and emits no artifacts."""
    p = EchoProvider()
    sid = p.create_session("a", "1", "e")
    blocked = p.run_until_block(sid, prompt="bulk delete 50 tickets")
    assert blocked["status"] == "blocked"
    assert "artifacts" not in blocked
