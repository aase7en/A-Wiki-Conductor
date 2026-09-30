"""WO-P1-570 — focused tests for the Phase 1 A-Relay carrier.

Covers the work-order acceptance list against
``src/a_conductor/sidecar_relay.py`` (stdlib-only dumb carrier for the
Phase 0 contract ``docs/contracts/a-sidecar-relay-v1.md``):

1. all 11 families accepted; unknown family rejected;
2. required fields and mutation-relevant binding requirements;
3. event-id minting/validation;
4. append-only UTF-8/LF JSONL + 65536-byte cap;
5. torn final line;
6. dedupe-on-read and stable ordering;
7. result receipts require evidence refs;
8. sensitive/executable-content rejection;
9. typed CLI exit behavior;
10. stdlib-only / no network / no subprocess / no authority methods;
11. Windows/macOS path evidence remains opaque;
12. related ``test_control_events.py`` / ``test_lifecycle_journal.py``
    remain green (run separately by the work order).
"""

from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from a_conductor import sidecar_relay as sr

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_SOURCE_PATH = Path(sr.__file__)

VALID_HEAD_SHA = "a" * 40
FULL_BINDING = {
    "TASK_ID": "WO-P1-570",
    "CLAIM_ID": "WO-P1-570-ARELAY-CARRIER-MAC-001",
    "REPO": "aase7en/A-Wiki-Conductor",
    "WORKTREE": "/Users/dev/worktrees/demo",
    "HEAD_SHA": VALID_HEAD_SHA,
}


def _payload(**overrides: object) -> dict:
    payload: dict = {
        "EVENT_ID": "evt-codex-0123456789abcdef",
        "EVENT_TYPE": "SIDECAR_CHECKPOINT",
        "SOURCE_SURFACE": "codex",
        "SOURCE_THREAD_ID": "thread-1",
        "SOURCE_TURN_ID": "turn-1",
        "EVIDENCE_REFS": ["docs/work-orders/WO-P1-570-a-relay-carrier-phase1.md"],
        "CREATED_AT": "2026-09-30T04:04:33+00:00",
    }
    payload.update(FULL_BINDING)
    for key, value in overrides.items():
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    return payload


def _envelope(**overrides: object) -> sr.RelayEnvelope:
    return sr.envelope_from_mapping(_payload(**overrides))


def _code(excinfo: pytest.ExceptionInfo) -> str:
    return excinfo.value.code


class TestFamilyAllowlist:
    def test_all_eleven_families_accepted(self) -> None:
        assert len(sr.EVENT_FAMILIES) == 11
        for family in sorted(sr.EVENT_FAMILIES):
            envelope = sr.envelope_from_mapping(
                _payload(EVENT_TYPE=family, EVENT_ID=f"evt-codex-{family.lower()}")
            )
            assert envelope.event_type == family

    def test_unknown_family_rejected(self) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(EVENT_TYPE="SIDECAR_NEW_THING"))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_lowercase_family_rejected(self) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(EVENT_TYPE="sidecar_checkpoint"))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"


class TestMandatoryFieldsAndBinding:
    @pytest.mark.parametrize(
        "field",
        [
            "EVENT_ID",
            "EVENT_TYPE",
            "SOURCE_SURFACE",
            "SOURCE_THREAD_ID",
            "SOURCE_TURN_ID",
            "CREATED_AT",
        ],
    )
    def test_missing_mandatory_field_rejected(self, field: str) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(**{field: None}))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_unknown_envelope_key_rejected(self) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(PROMPT="please merge everything"))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_non_object_payload_rejected(self) -> None:
        for bad in (None, [], "text", 7):
            with pytest.raises(sr.RelayCarrierError) as excinfo:
                sr.envelope_from_mapping(bad)
            assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_mutation_relevant_families_require_full_binding(self) -> None:
        assert sr.MUTATION_RELEVANT_FAMILIES == sr.EVENT_FAMILIES - {
            "GPT_WORK_LIMITED",
            "CONTEXT_PRESSURE_HIGH",
        }
        for family in sorted(sr.MUTATION_RELEVANT_FAMILIES):
            for field in ("TASK_ID", "CLAIM_ID", "REPO", "WORKTREE", "HEAD_SHA"):
                with pytest.raises(sr.RelayCarrierError) as excinfo:
                    sr.envelope_from_mapping(
                        _payload(
                            EVENT_TYPE=family,
                            EVENT_ID=f"evt-codex-{family.lower()}",
                            **{field: None},
                        )
                    )
                assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_observability_families_do_not_require_binding(self) -> None:
        for family in ("GPT_WORK_LIMITED", "CONTEXT_PRESSURE_HIGH"):
            envelope = sr.envelope_from_mapping(
                _payload(
                    EVENT_TYPE=family,
                    EVENT_ID=f"evt-gpt-{family.lower()}",
                    SOURCE_SURFACE="gpt",
                    TASK_ID=None,
                    CLAIM_ID=None,
                    REPO=None,
                    WORKTREE=None,
                    HEAD_SHA=None,
                )
            )
            assert envelope.task_id is None
            assert envelope.claim_id is None
            assert envelope.repo is None
            assert envelope.worktree is None
            assert envelope.head_sha is None

    def test_to_mapping_omits_unbound_fields(self) -> None:
        envelope = sr.envelope_from_mapping(
            _payload(
                EVENT_TYPE="GPT_WORK_LIMITED",
                SOURCE_SURFACE="gpt",
                EVENT_ID="evt-gpt-work-limited-1",
                TASK_ID=None,
                CLAIM_ID=None,
                REPO=None,
                WORKTREE=None,
                HEAD_SHA=None,
            )
        )
        mapping = envelope.to_mapping()
        assert "TASK_ID" not in mapping
        assert "CLAIM_ID" not in mapping
        assert "REPO" not in mapping
        assert "WORKTREE" not in mapping
        assert "HEAD_SHA" not in mapping

    @pytest.mark.parametrize(
        "field,value",
        [
            ("REPO", "no-slash"),
            ("REPO", "a/b/c"),
            ("REPO", "aase7en//conductor"),
            ("REPO", "/A-Wiki-Conductor"),
            ("HEAD_SHA", "a" * 39),
            ("HEAD_SHA", "a" * 41),
            ("HEAD_SHA", "A" * 40),
            ("HEAD_SHA", "z" * 40),
            ("WORKTREE", "   "),
            ("TASK_ID", "has space"),
            ("TASK_ID", ""),
            ("CLAIM_ID", "trailing\n"),
            ("REQUESTED_CAPABILITY", "Not A Token"),
            ("REQUESTED_CAPABILITY", "x" * 65),
            ("SOURCE_THREAD_ID", ""),
            ("SOURCE_TURN_ID", ""),
        ],
    )
    def test_binding_field_grammar_enforced(self, field: str, value: object) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(**{field: value}))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_non_string_field_rejected(self) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(TASK_ID=123))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"


class TestEventId:
    def test_minted_id_shape(self) -> None:
        event_id = sr.mint_event_id("glm")
        assert event_id.startswith("evt-glm-")
        assert sr.mint_event_id("glm") != sr.mint_event_id("glm")

    def test_minted_id_is_accepted_for_its_surface(self) -> None:
        envelope = sr.envelope_from_mapping(
            _payload(SOURCE_SURFACE="glm", EVENT_ID=sr.mint_event_id("glm"))
        )
        assert envelope.event_id.startswith("evt-glm-")

    def test_id_surface_must_match_source_surface(self) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(
                _payload(SOURCE_SURFACE="codex", EVENT_ID=sr.mint_event_id("glm"))
            )
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    @pytest.mark.parametrize(
        "bad_id",
        [
            "",
            "event-codex-abc",
            "evt-codex",
            "evt-codex-",
            "evt-codex-has space",
            "evt-codex-tail\nmore",
            "evt-unknown-surface-abc",
            "evt-codex-" + "x" * 129,
        ],
    )
    def test_invalid_event_ids_rejected(self, bad_id: str) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(EVENT_ID=bad_id))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"


class TestPriority:
    def test_human_gate_defaults_high(self) -> None:
        envelope = sr.envelope_from_mapping(
            _payload(
                EVENT_TYPE="HUMAN_GATE_REQUIRED",
                EVENT_ID="evt-codex-human-gate-1",
            )
        )
        assert envelope.priority == "HIGH"

    def test_context_pressure_defaults_high(self) -> None:
        envelope = sr.envelope_from_mapping(
            _payload(
                EVENT_TYPE="CONTEXT_PRESSURE_HIGH",
                EVENT_ID="evt-codex-pressure-1",
            )
        )
        assert envelope.priority == "HIGH"

    def test_other_families_default_normal(self) -> None:
        assert _envelope().priority == "NORMAL"

    def test_explicit_priority_preserved(self) -> None:
        envelope = sr.envelope_from_mapping(_payload(PRIORITY="LOW"))
        assert envelope.priority == "LOW"

    @pytest.mark.parametrize("bad", ["URGENT", "high", "", 3])
    def test_invalid_priority_rejected(self, bad: object) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(PRIORITY=bad))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"


class TestCreatedAt:
    @pytest.mark.parametrize(
        "bad",
        [
            "2026-09-30T04:04:33",
            "not-a-time",
            "2026-09-30 04:04:33+00:00",
            "",
            12345,
            "2026-13-45T99:99:99+00:00",
        ],
    )
    def test_invalid_created_at_rejected(self, bad: object) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(CREATED_AT=bad))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_zulu_offset_accepted(self) -> None:
        envelope = sr.envelope_from_mapping(_payload(CREATED_AT="2026-09-30T04:04:33Z"))
        assert envelope.created_at == "2026-09-30T04:04:33Z"

    def test_numeric_offset_accepted(self) -> None:
        envelope = sr.envelope_from_mapping(
            _payload(CREATED_AT="2026-09-30T11:04:33+07:00")
        )
        assert envelope.created_at == "2026-09-30T11:04:33+07:00"


class TestEvidenceRefs:
    @pytest.mark.parametrize(
        "family",
        ["SIDECAR_RESULT_RECEIPT", "GLM_RESULT_RECEIPT"],
    )
    def test_result_receipt_requires_evidence(self, family: str) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(
                _payload(EVENT_TYPE=family, EVENT_ID=f"evt-codex-{family.lower()}", EVIDENCE_REFS=None)
            )
        assert _code(excinfo) == "RELAY_EVIDENCE_MISSING"

        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(
                _payload(EVENT_TYPE=family, EVENT_ID=f"evt-codex-{family.lower()}", EVIDENCE_REFS=[])
            )
        assert _code(excinfo) == "RELAY_EVIDENCE_MISSING"

    def test_result_receipt_with_evidence_accepted(self) -> None:
        envelope = sr.envelope_from_mapping(
            _payload(
                EVENT_TYPE="GLM_RESULT_RECEIPT",
                SOURCE_SURFACE="glm",
                EVENT_ID="evt-glm-receipt-1",
                EVIDENCE_REFS=["runs/WO-P1-570/r1/result.md"],
            )
        )
        assert envelope.evidence_refs == ("runs/WO-P1-570/r1/result.md",)

    def test_sixteen_refs_accepted_seventeen_rejected(self) -> None:
        refs = [f"runs/demo/{index}/result.md" for index in range(16)]
        envelope = sr.envelope_from_mapping(_payload(EVIDENCE_REFS=refs))
        assert len(envelope.evidence_refs) == 16
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(EVIDENCE_REFS=refs + ["one-more"]))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_duplicate_refs_rejected(self) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(
                _payload(EVIDENCE_REFS=["runs/a.md", "runs/a.md"])
            )
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_url_refs_rejected(self) -> None:
        for bad in [
            "https://share.example.com/runs/1",
            "http://example.com/x",
            "file:///etc/passwd",
        ]:
            with pytest.raises(sr.RelayCarrierError) as excinfo:
                sr.envelope_from_mapping(_payload(EVIDENCE_REFS=[bad]))
            assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_ref_length_bounded(self) -> None:
        ok = "x" * 4096
        sr.envelope_from_mapping(_payload(EVIDENCE_REFS=[ok]))
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(EVIDENCE_REFS=["x" * 4097]))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_non_list_refs_rejected(self) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(EVIDENCE_REFS="runs/a.md"))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_blank_ref_rejected(self) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(EVIDENCE_REFS=["   "]))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"


class TestSensitiveContent:
    def test_pem_block_rejected(self) -> None:
        pem = "-----BEGIN PRIVATE KEY-----MIIB-----END PRIVATE KEY-----"
        for field in ("EVIDENCE_REFS", "SOURCE_THREAD_ID", "DEVICE_CONTEXT"):
            value = [pem] if field == "EVIDENCE_REFS" else pem
            with pytest.raises(sr.RelayCarrierError) as excinfo:
                sr.envelope_from_mapping(_payload(**{field: value}))
            assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    @pytest.mark.parametrize(
        "token",
        [
            "ghp_" + "A" * 36,
            "gho_" + "B" * 36,
            "github_pat_" + "C" * 40,
            "sk-" + "D" * 32,
            "xoxb-" + "E" * 30,
            "AKIA" + "F" * 16,
            "AIza" + "G" * 35,
        ],
    )
    def test_secret_token_markers_rejected(self, token: str) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(SOURCE_THREAD_ID=token))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_control_characters_rejected(self) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_mapping(_payload(DEVICE_CONTEXT="macos\x1b[31m"))
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_bidi_and_zero_width_characters_rejected(self) -> None:
        for bad in ("evil\u202eevil", "zero\u200bwidth", "soft\u00adhyphen"):
            with pytest.raises(sr.RelayCarrierError) as excinfo:
                sr.envelope_from_mapping(_payload(WORKTREE=bad))
            assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_surrogate_escape_rejected(self) -> None:
        raw_json = (
            '{"EVENT_ID":"evt-codex-0123456789abcdef",'
            '"EVENT_TYPE":"SIDECAR_CHECKPOINT",'
            '"SOURCE_SURFACE":"codex",'
            '"SOURCE_THREAD_ID":"thread-\\ud800",'
            '"SOURCE_TURN_ID":"turn-1",'
            '"TASK_ID":"WO-P1-570",'
            '"CLAIM_ID":"WO-P1-570-ARELAY-CARRIER-MAC-001",'
            '"REPO":"aase7en/A-Wiki-Conductor",'
            '"WORKTREE":"/Users/dev/worktrees/demo",'
            '"HEAD_SHA":"' + "a" * 40 + '",'
            '"EVIDENCE_REFS":["docs/x.md"],'
            '"CREATED_AT":"2026-09-30T04:04:33+00:00"}'
        )
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.envelope_from_json_line(raw_json)
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_error_messages_are_code_only(self) -> None:
        secret = "ghp_" + "A" * 36
        try:
            sr.envelope_from_mapping(_payload(SOURCE_THREAD_ID=secret))
        except sr.RelayCarrierError as error:
            assert secret not in str(error)
            assert str(error) == error.code
            assert error.code.startswith("RELAY_")
        else:
            raise AssertionError("expected RelayCarrierError")


class TestAppendOnlyJsonl:
    def test_append_writes_strict_utf8_lf_jsonl(self, tmp_path: Path) -> None:
        log = tmp_path / "relay" / "events.jsonl"
        first = _envelope(EVENT_ID="evt-codex-000000000001")
        second = sr.envelope_from_mapping(
            _payload(
                EVENT_ID="evt-glm-000000000002",
                SOURCE_SURFACE="glm",
                EVENT_TYPE="GLM_RESULT_RECEIPT",
                EVIDENCE_REFS=["runs/demo/result.md"],
            )
        )
        sr.append_event(log, first)
        sr.append_event(log, second)
        raw = log.read_bytes()
        assert raw.endswith(b"\n")
        assert b"\r" not in raw
        raw.decode("utf-8", errors="strict")
        lines = raw.decode("utf-8").splitlines()
        assert lines[0] == first.to_json()
        assert lines[1] == second.to_json()

    def test_existing_lines_are_never_rewritten(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        first = _envelope()
        sr.append_event(log, first)
        before = log.read_bytes()
        sr.append_event(
            log,
            sr.envelope_from_mapping(_payload(EVENT_ID="evt-codex-000000000003")),
        )
        after = log.read_bytes()
        assert after.startswith(before)

    def test_size_cap_enforced_at_boundary(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        fixed_refs = [f"{index:04d}" + "x" * 4092 for index in range(15)]
        base = sr.envelope_from_mapping(_payload(EVIDENCE_REFS=fixed_refs + ["x"]))
        base_size = len(base.to_json().encode("utf-8")) + 1
        assert base_size < sr.MAX_EVENT_BYTES
        pad_ref = "p" * (1 + sr.MAX_EVENT_BYTES - base_size)
        assert len(pad_ref) < 4096
        envelope = sr.envelope_from_mapping(
            _payload(EVIDENCE_REFS=fixed_refs + [pad_ref])
        )
        assert len(envelope.to_json().encode("utf-8")) + 1 == sr.MAX_EVENT_BYTES
        sr.append_event(log, envelope)
        assert log.exists()

        oversized = sr.envelope_from_mapping(
            _payload(EVIDENCE_REFS=fixed_refs + [pad_ref + "x"])
        )
        assert len(oversized.to_json().encode("utf-8")) + 1 > sr.MAX_EVENT_BYTES
        before = log.read_bytes()
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.append_event(log, oversized)
        assert _code(excinfo) == "RELAY_EVENT_TOO_LARGE"
        assert log.read_bytes() == before


class TestTornFinalLine:
    def test_torn_tail_skipped_on_read(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        first = _envelope()
        sr.append_event(log, first)
        with log.open("ab") as handle:
            handle.write(b'{"EVENT_ID": "evt-codex-tor')
        result = sr.read_events(log)
        assert [event.event_id for event in result.events] == [first.event_id]
        assert result.torn_tail_skipped is True

    def test_append_refuses_after_torn_tail(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        sr.append_event(log, _envelope())
        with log.open("ab") as handle:
            handle.write(b'{"EVENT_ID": "evt-codex-tor')
        before = log.read_bytes()
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.append_event(
                log,
                sr.envelope_from_mapping(_payload(EVENT_ID="evt-codex-000000000009")),
            )
        assert _code(excinfo) == "RELAY_IO_ERROR"
        assert log.read_bytes() == before

    def test_midfile_corrupt_complete_line_fails_closed(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        first = _envelope()
        second = sr.envelope_from_mapping(_payload(EVENT_ID="evt-codex-000000000010"))
        content = (
            first.to_json().encode("utf-8")
            + b"\n"
            + b"{corrupt json"
            + b"\n"
            + second.to_json().encode("utf-8")
            + b"\n"
        )
        log.write_bytes(content)
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.read_events(log)
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_crlf_line_rejected(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        log.write_bytes(_envelope().to_json().encode("utf-8") + b"\r\n")
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.read_events(log)
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_invalid_utf8_log_fails_typed(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        log.write_bytes(b'{"half": "\xff\xfe"}\n')
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.read_events(log)
        assert _code(excinfo) == "RELAY_IO_ERROR"


class TestDedupeAndOrdering:
    def test_read_missing_log_fails_typed(self, tmp_path: Path) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.read_events(tmp_path / "missing.jsonl")
        assert _code(excinfo) == "RELAY_IO_ERROR"

    def test_directory_log_path_fails_typed(self, tmp_path: Path) -> None:
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.read_events(tmp_path)
        assert _code(excinfo) == "RELAY_IO_ERROR"

    def test_identical_append_is_idempotent(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        envelope = _envelope()
        sr.append_event(log, envelope)
        sr.append_event(log, envelope)
        assert len(log.read_bytes().splitlines()) == 1
        assert len(sr.read_events(log).events) == 1

    def test_conflicting_event_id_rejected_on_append(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        sr.append_event(log, _envelope())
        before = log.read_bytes()
        conflicting = sr.envelope_from_mapping(
            _payload(CREATED_AT="2026-09-30T05:04:33+00:00")
        )
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            sr.append_event(log, conflicting)
        assert _code(excinfo) == "RELAY_EVENT_DUPLICATE"
        assert log.read_bytes() == before

    def test_dedupe_on_read_first_wins(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        first = _envelope()
        duplicate = sr.envelope_from_mapping(
            _payload(CREATED_AT="2026-09-30T06:06:06+00:00")
        )
        log.write_bytes(
            (first.to_json() + "\n" + duplicate.to_json() + "\n").encode("utf-8")
        )
        result = sr.read_events(log)
        assert len(result.events) == 1
        assert result.events[0].created_at == first.created_at
        assert result.torn_tail_skipped is False

    def test_order_events_deterministic_per_producer(self) -> None:
        a1 = sr.envelope_from_mapping(
            _payload(
                EVENT_ID="evt-codex-00000000000a",
                CREATED_AT="2026-09-30T03:00:00+00:00",
            )
        )
        a2 = sr.envelope_from_mapping(
            _payload(
                EVENT_ID="evt-codex-00000000000b",
                CREATED_AT="2026-09-30T01:00:00+00:00",
            )
        )
        b1 = sr.envelope_from_mapping(
            _payload(
                EVENT_ID="evt-glm-00000000000c",
                SOURCE_SURFACE="glm",
                EVENT_TYPE="GLM_RESULT_RECEIPT",
                EVIDENCE_REFS=["runs/x.md"],
                CREATED_AT="2026-09-30T02:00:00+00:00",
            )
        )
        for shuffle in ([b1, a2, a1], [a1, b1, a2], [a2, b1, a1]):
            ordered = sr.order_events(shuffle)
            assert [event.event_id for event in ordered] == [
                a2.event_id,
                a1.event_id,
                b1.event_id,
            ]


class TestPathOpacity:
    def test_windows_path_round_trips_opaquely(self, tmp_path: Path) -> None:
        worktree = r"A:\GitHub\_worktrees\wo570-demo"
        envelope = sr.envelope_from_mapping(_payload(WORKTREE=worktree))
        assert envelope.worktree == worktree
        log = tmp_path / "events.jsonl"
        sr.append_event(log, envelope)
        result = sr.read_events(log)
        assert result.events[0].worktree == worktree

    def test_posix_path_round_trips_opaquely(self, tmp_path: Path) -> None:
        worktree = "/Users/dev/GitHub/_worktrees/wo570-demo"
        envelope = sr.envelope_from_mapping(_payload(WORKTREE=worktree))
        log = tmp_path / "events.jsonl"
        sr.append_event(log, envelope)
        assert sr.read_events(log).events[0].worktree == worktree

    def test_nonexistent_path_is_never_resolved(self) -> None:
        sr.envelope_from_mapping(_payload(WORKTREE="/definitely/not/resolved/anywhere"))


class TestFrozenRepresentation:
    def test_envelope_is_frozen(self) -> None:
        envelope = _envelope()
        with pytest.raises(FrozenInstanceError):
            envelope.event_type = "GPT_WORK_LIMITED"

    def test_evidence_refs_is_tuple(self) -> None:
        assert _envelope().evidence_refs == (
            "docs/work-orders/WO-P1-570-a-relay-carrier-phase1.md",
        )

    def test_json_round_trip(self) -> None:
        envelope = _envelope()
        line = envelope.to_json()
        assert "\n" not in line
        restored = sr.envelope_from_json_line(line)
        assert restored == envelope


class TestCli:
    def test_validate_ok(self, tmp_path: Path, capsys) -> None:
        log = tmp_path / "events.jsonl"
        sr.append_event(log, _envelope())
        assert sr.main(["validate", str(log)]) == 0

    def test_validate_missing_file_exit(self, tmp_path: Path) -> None:
        assert sr.main(["validate", str(tmp_path / "no.jsonl")]) == 6

    def test_validate_corrupt_log_exit(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        log.write_bytes(b"{broken\n")
        assert sr.main(["validate", str(log)]) == 2

    def test_emit_and_tail(self, tmp_path: Path, capsys) -> None:
        log = tmp_path / "events.jsonl"
        line = _envelope().to_json()
        assert sr.main(["emit", str(log), line]) == 0
        assert capsys.readouterr().out.strip() == "evt-codex-0123456789abcdef"
        assert sr.main(["emit", str(log), "{not-json"]) == 2
        assert sr.main(["tail", str(log), "1"]) == 0
        out = capsys.readouterr().out.splitlines()
        assert out == [line]

    def test_emit_duplicate_exit(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        envelope = _envelope()
        sr.append_event(log, envelope)
        conflicting = sr.envelope_from_mapping(
            _payload(CREATED_AT="2026-09-30T07:07:07+00:00")
        )
        assert sr.main(["emit", str(log), conflicting.to_json()]) == 5

    def test_tail_invalid_count_usage_exit(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        sr.append_event(log, _envelope())
        assert sr.main(["tail", str(log), "zero"]) == 64

    def test_usage_errors_exit_64(self, tmp_path: Path) -> None:
        assert sr.main([]) == 64
        assert sr.main(["frobnicate", str(tmp_path)]) == 64
        assert sr.main(["emit", str(tmp_path / "x.jsonl")]) == 64

    def test_python_dash_m_smoke(self, tmp_path: Path) -> None:
        import os

        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get(
            "PYTHONPATH", ""
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "a_conductor.sidecar_relay",
                "validate",
                str(tmp_path / "missing.jsonl"),
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 6
        assert "RELAY_IO_ERROR" in result.stderr


class TestStructuralContract:
    def test_stdlib_only_no_network_no_subprocess(self) -> None:
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        allowed = {
            "__future__",
            "dataclasses",
            "datetime",
            "json",
            "pathlib",
            "re",
            "sys",
            "typing",
            "unicodedata",
            "uuid",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] in allowed
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] in allowed
            elif isinstance(node, ast.Call):
                name = (
                    node.func.id
                    if isinstance(node.func, ast.Name)
                    else node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else ""
                )
                assert name not in {
                    "Popen",
                    "system",
                    "urlopen",
                    "connect",
                    "send",
                    "recv",
                    "run",
                }

    def test_no_authority_api_names(self) -> None:
        tree = ast.parse(MODULE_SOURCE_PATH.read_text(encoding="utf-8"))
        forbidden = (
            "claim",
            "lease",
            "schedul",
            "dispatch",
            "review",
            "merge",
            "complete",
            "approve",
            "cancel",
            "retry",
            "execute",
        )
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lowered = node.name.lower()
                for token in forbidden:
                    assert token not in lowered

    def test_module_source_hygiene(self) -> None:
        raw = MODULE_SOURCE_PATH.read_bytes()
        raw.decode("utf-8", errors="strict")
        assert b"\r" not in raw
        assert raw.endswith(b"\n")
        text = raw.decode("utf-8")
        for line in text.splitlines():
            assert line == line.rstrip(), repr(line)
