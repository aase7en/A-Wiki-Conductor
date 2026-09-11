"""WO193-GLM-BYTE-VALIDATION-001 — sustained byte-integrity validation campaign.

Validates the frozen WO193 helper repair (source f1dbb65212a737f7a4f88dcd88bdb713f190ad51)
on real Windows against an INDEPENDENT byte oracle (tests/fixtures/wo193_byte_integrity/corpus.json):

- B02 multilingual/composition corpus (oracle agreement + anti-vacuity negatives)
- B03 newline/BOM/control shapes through hostile TextIOWrapper configurations
- B04 real helper subprocess E2E: binary file redirect (production "ab" mode),
  hostile PYTHONIOENCODING, Unicode/spaces parent dir, known nonzero child exit,
  EXIT_PENDING (no result fabrication)
- B05 publication interleavings: report/result write failures, deterministic
  collector barriers, no replay within one execution
- B06 protocol budget boundaries measured in UTF-8 BYTES + segmentation invariance
- B07 collector contract over a sacrificial store: failed publication is never
  RESULT_AVAILABLE; successful collect is CAS-fenced (no double collect)

Every test names its invariant; ids are stable for -k selection. Synthetic
children only — no installed ZCode, no real provider, no production ports.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from a_conductor import zcode_protocol
from a_conductor import zcode_supervised_helper as helper
from a_conductor.supervised_execution import SupervisedInspectionState
from a_conductor.zcode_protocol import ZCodeProtocolDriver, ZCodeProtocolError

# Reuse existing test scaffolding (WO193 packet B09: no mechanical duplication).
from tests.test_zcode_helper_execution import _runtime_metadata_env
from tests.test_zcode_stdout_boundary import _invoke
from tests.test_zcode_phase_c import (
    ScriptedTransport,
    _completed,
    _create,
    _delta,
    _prefs,
    _subscribe_ok,
)
from tests.test_supervised_execution import make_record

CORPUS_PATH = Path(__file__).parent / "fixtures" / "wo193_byte_integrity" / "corpus.json"
CORPUS = {c["name"]: c for c in json.loads(CORPUS_PATH.read_text(encoding="utf-8"))["cases"]}
EXECUTION_ID = "exec-0123456789abcdef"

# ---------------------------------------------------------------------------
# Self-contained synthetic app-server (config-driven; no edits to Astra's file).
# ---------------------------------------------------------------------------

FAKE_APP_SERVER = r'''
import json, os, sys, time

def out(obj):
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()

here = os.path.dirname(os.path.abspath(sys.argv[0]))
with open(os.path.join(here, "wo193_fake.config.json"), encoding="utf-8") as f:
    config = json.load(f)
receipt_dir = config["receipt_dir"]
response = config["response"]

with open(os.path.join(receipt_dir, "spawn.pid"), "a", encoding="utf-8") as f:
    f.write(str(os.getpid()) + "\n")

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    mid, method = msg.get("id"), msg.get("method")
    if method == "session/create":
        model_ref = msg.get("params", {}).get("model") or msg.get("params", {}).get("runtimeModel", {}).get("model")
        with open(receipt_dir + "/create_receipts.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"model": model_ref}, separators=(",", ":")) + "\n")
        out({"id": 1000, "method": "session/requestRuntimePreferences"})
        out({"id": mid, "result": {"session": {"sessionId": "wo193-fake"},
            "settings": {"model": {"current": model_ref, "available": []}}}})
    elif method == "session/subscribe":
        out({"id": mid, "result": {"ok": True}})
    elif method == "session/setThoughtLevel":
        out({"id": mid, "result": {"ok": True}})
    elif method == "session/send":
        with open(receipt_dir + "/send_receipt.json", "w", encoding="utf-8") as f:
            f.write(json.dumps({"content": msg.get("params", {}).get("content", "")},
                               separators=(",", ":"), ensure_ascii=False))
        out({"method": "session/event", "params": {"type": "model.streaming",
            "payload": {"kind": "text_delta", "delta": response}}})
        out({"method": "session/event", "params": {"type": "turn.completed"}})
if config.get("hang_after_turn"):
    time.sleep(600)
raise SystemExit(config.get("exit_code", 0))
'''


def _write_fake(tmp_path: Path, config: dict) -> Path:
    fake_dir = tmp_path / "fake"
    fake_dir.mkdir(parents=True, exist_ok=True)
    (fake_dir / "wo193_fake_app_server.py").write_text(FAKE_APP_SERVER, encoding="utf-8")
    (fake_dir / "wo193_fake.config.json").write_text(
        json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return fake_dir / "wo193_fake_app_server.py"


def _helper_env(tmp_path: Path, packet_text: str, *, encoding: str) -> dict[str, str]:
    packet = tmp_path / "task.md"
    packet.write_text(packet_text, encoding="utf-8")
    env = {k: os.environ[k] for k in ("PATH", "SystemRoot", "SYSTEMROOT", "TEMP", "TMP")
           if k in os.environ}
    env.update(_runtime_metadata_env())
    env.update({
        "ZCODE_TASK_PACKET_PATH": str(packet),
        "ZCODE_TASK_PACKET_TRUSTED_ROOT": str(tmp_path),
        "ZCODE_TASK_PACKET_SHA256": hashlib.sha256(packet.read_bytes()).hexdigest(),
        "PYTHONIOENCODING": encoding,
    })
    return env


def _run_helper(
    tmp_path: Path,
    *,
    response: str,
    packet_text: str = "WO193 synthetic task",
    exit_code: int = 0,
    hang_after_turn: bool = False,
    encoding: str = "cp874",
    stdout_mode: str = "file",
    result_path: Path | None = None,
    report_path: Path | None = None,
    timeout: float = 90.0,
) -> subprocess.CompletedProcess:
    """Run the REAL helper as a subprocess with a synthetic app-server child.

    stdout_mode 'file' mirrors production: the handle passed to Popen is opened
    "ab", buffering=0 exactly like owned_process.WindowsOwnedProcessController.
    """
    receipts = tmp_path / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    fake = _write_fake(tmp_path, {
        "receipt_dir": str(receipts), "response": response,
        "exit_code": exit_code, "hang_after_turn": hang_after_turn,
    })
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    result_path = result_path if result_path is not None else run_dir / "result.json"
    report_path = report_path if report_path is not None else run_dir / "report.json"
    executable = getattr(sys, "_base_executable", None) or sys.executable
    command = [
        executable, str(Path(helper.__file__).resolve()),
        "--execution-id", EXECUTION_ID,
        "--pid-path", str(run_dir / "child.pid"),
        "--result-path", str(result_path),
        "--report-path", str(report_path),
        "--cwd", str(tmp_path), "--",
        executable, str(fake), "app-server", "--stdio", "--surface", "desktop",
    ]
    env = _helper_env(tmp_path, packet_text, encoding=encoding)
    if stdout_mode == "file":
        stdout_file = run_dir / "stdout.log"
        with stdout_file.open("ab", buffering=0) as handle:
            return subprocess.run(command, env=env, stdout=handle,
                                  stderr=subprocess.PIPE, timeout=timeout)
    return subprocess.run(command, env=env, capture_output=True, timeout=timeout)


# ===========================================================================
# B02 — corpus oracle
# ===========================================================================

@pytest.mark.parametrize("name", sorted(CORPUS), ids=lambda n: f"oracle-{n}")
def test_b02_corpus_oracle_self_agreement(name):
    """The fixture's own hex/sha/length must agree — the oracle is usable."""
    case = CORPUS[name]
    raw = bytes.fromhex(case["utf8_hex"])
    assert raw.decode("utf-8") == case["text"]
    assert len(raw) == case["byte_length"]
    assert hashlib.sha256(raw).hexdigest() == case["sha256"]


def test_b02_negative_controls_are_real_negatives():
    """Anti-vacuity: one-code-point/byte neighbors and NFC/CRLF transforms of a
    case must produce DIFFERENT byte identities (hash + hex)."""
    base = CORPUS["ascii"]
    for neg in ("neg_codepoint", "neg_byte_prefix", "neg_nfc_of_decomposed", "neg_crlf_transform"):
        case = CORPUS[neg]
        assert case["sha256"] != base["sha256"] or case["utf8_hex"] != base["utf8_hex"]
    decomp = CORPUS["combining_decomposed"]
    pre = CORPUS["combining_precomposed"]
    nfc = CORPUS["neg_nfc_of_decomposed"]
    # visually identical, byte-different: the decomposed form differs from BOTH
    # the precomposed text and its NFC transform; NFC(decomposed) collapses to
    # exactly the precomposed bytes — the corruption a Unicode-normalizing
    # consumer would silently produce.
    assert decomp["sha256"] not in {pre["sha256"], nfc["sha256"]}
    assert nfc["sha256"] == pre["sha256"]
    assert nfc["utf8_hex"] == pre["utf8_hex"]
    assert CORPUS["trailing_single"]["sha256"] != CORPUS["neg_crlf_transform"]["sha256"]


@pytest.mark.parametrize("name", sorted(
    n for n in CORPUS if not n.startswith("neg_")), ids=lambda n: f"helper-{n}")
def test_b02_helper_main_preserves_corpus_bytes_under_hostile_wrapper(monkeypatch, tmp_path, name):
    """Invariant: helper output bytes == oracle bytes even when sys.stdout is a
    hostile TextIOWrapper (cp874 + forced CRLF translation)."""
    case = CORPUS[name]
    raw = io.BytesIO()
    output = io.TextIOWrapper(raw, encoding="cp874", newline="\r\n")
    try:
        rc, report = _invoke(monkeypatch, tmp_path, case["text"], output)
        captured = raw.getvalue()
        assert rc == 0
        assert captured.hex() == case["utf8_hex"]
        assert report["response_bytes"] == case["byte_length"]
        assert report["response_sha256"] == case["sha256"]
    finally:
        output.close()


# ===========================================================================
# B03 — newline / BOM / control shapes (distinct from Astra's matrix)
# ===========================================================================

B03_SHAPES = {
    "lone-cr": ("cp1252", None, "x\ry\rz"),
    "trailing-none": ("cp1252", "\r\n", "end without newline"),
    "consecutive-blanks": ("utf-8", "\r\n", "a\n\n\n\nb"),
    "whitespace-only": ("cp874", "\r\n", " \t \r\n "),
    "nul-middle": ("cp1252", None, "a\x00b\x00"),
    "bom-interior": ("cp874", "\r\n", "x\ufeffy"),
}


@pytest.mark.parametrize("shape", sorted(B03_SHAPES),
    ids=lambda s: f"shape-{s}")
def test_b03_newline_and_control_shapes_preserved(monkeypatch, tmp_path, shape):
    encoding, newline, response = B03_SHAPES[shape]
    raw = io.BytesIO()
    output = io.TextIOWrapper(raw, encoding=encoding, newline=newline)
    try:
        rc, report = _invoke(monkeypatch, tmp_path, response, output)
        captured = raw.getvalue()
        assert rc == 0
        assert captured == response.encode("utf-8")
        assert len(captured) == report["response_bytes"]
        assert hashlib.sha256(captured).hexdigest() == report["response_sha256"]
    finally:
        output.close()


def test_b03_wrapper_simulation_is_labelled_not_native():
    """B03 wrapper cases simulate host TextIOWrapper only; native OS proof is
    B04's real subprocess file evidence (this marker keeps the distinction
    explicit in the suite)."""
    assert io.TextIOWrapper(io.BytesIO(), encoding="utf-8", newline=None) is not None


# ===========================================================================
# B04 — real Windows helper subprocess E2E (synthetic child)
# ===========================================================================

@pytest.mark.parametrize("name", ["thai_inherent", "emoji_supplementary",
                                  "newlines_mixed", "nul_inside", "bom_inside"],
    ids=lambda n: f"e2e-{n}")
def test_b04_real_helper_binary_file_redirect_corpus(tmp_path, name):
    """Invariant: through a production-shaped binary file redirect ("ab",
    buffering=0) and hostile PYTHONIOENCODING=cp874, the durable stdout file
    equals the oracle bytes; report length/hash attest those exact bytes."""
    case = CORPUS[name]
    result = _run_helper(tmp_path, response=case["text"])
    assert result.returncode == 0, result.stderr
    stdout_bytes = (tmp_path / "run" / "stdout.log").read_bytes()
    assert stdout_bytes.hex() == case["utf8_hex"]
    report = json.loads((tmp_path / "run" / "report.json").read_bytes())
    outcome = json.loads((tmp_path / "run" / "result.json").read_bytes())
    assert report["response_bytes"] == case["byte_length"] == len(stdout_bytes)
    assert report["response_sha256"] == case["sha256"]
    assert outcome["exit_code"] == 0
    assert outcome["execution_id"] == EXECUTION_ID


def test_b04_unicode_and_spaces_parent_directory(tmp_path):
    """The whole E2E works under a Thai + spaces parent path (ASCII-first is
    proven by every other test's pytest tmp_path; this is the Unicode case)."""
    uni = tmp_path / "ทดสอบ ไดเรกทอรี ที่ มี ช่องว่าง"
    uni.mkdir()
    case = CORPUS["rtl_mixed"]
    result = _run_helper(uni, response=case["text"])
    assert result.returncode == 0, result.stderr
    stdout_bytes = (uni / "run" / "stdout.log").read_bytes()
    assert stdout_bytes.hex() == case["utf8_hex"]
    report = json.loads((uni / "run" / "report.json").read_bytes())
    assert report["response_sha256"] == case["sha256"]


def test_b04_one_spawn_one_send_exact_identity(tmp_path):
    """Invariant: exactly one child spawn and one protocol send; the sent
    prompt bytes equal the verified task packet; the runtime model binding
    reached the child intact."""
    case = CORPUS["ascii"]
    packet_text = "WO193 exact-identity packet หนึ่ง"
    result = _run_helper(tmp_path, response=case["text"], packet_text=packet_text)
    assert result.returncode == 0, result.stderr
    receipts = tmp_path / "receipts"
    spawn_lines = (receipts / "spawn.pid").read_text().splitlines()
    assert spawn_lines == [str(json.loads(
        (tmp_path / "run" / "result.json").read_bytes())["child_pid"])]
    sent = json.loads((receipts / "send_receipt.json").read_text(encoding="utf-8"))
    assert sent["content"] == packet_text
    create = json.loads((receipts / "create_receipts.jsonl")
                        .read_text(encoding="utf-8").splitlines()[0])
    assert create["model"]["modelId"] == "glm-5.3"


def test_b04_known_nonzero_child_exit_preserved(tmp_path):
    """Invariant: complete bytes with a known NONZERO child exit are delivered
    truthfully — result retains exit 3; complete bytes are not success
    authority and never rewritten to zero."""
    case = CORPUS["ascii"]
    result = _run_helper(tmp_path, response=case["text"], exit_code=3)
    assert result.returncode == 0, result.stderr
    stdout_bytes = (tmp_path / "run" / "stdout.log").read_bytes()
    assert stdout_bytes.hex() == case["utf8_hex"]
    outcome = json.loads((tmp_path / "run" / "result.json").read_bytes())
    assert outcome["exit_code"] == 3
    report = json.loads((tmp_path / "run" / "report.json").read_bytes())
    assert report["response_sha256"] == case["sha256"]


def test_b04_exit_pending_never_fabricates_result(tmp_path):
    """Invariant: protocol turn completed but child never exits within the
    bounded wait -> EXIT_PENDING report only; NO stdout bytes, NO result."""
    case = CORPUS["ascii"]
    result = _run_helper(tmp_path, response=case["text"], hang_after_turn=True,
                         timeout=120.0)
    assert result.returncode != 0
    assert b"EXIT_PENDING" in result.stderr
    run = tmp_path / "run"
    assert not (run / "result.json").exists()
    report = json.loads((run / "report.json").read_bytes())
    assert report["exit_state"] == "EXIT_PENDING"
    assert (run / "stdout.log").read_bytes() == b""


# ===========================================================================
# B05 — publication interleavings
# ===========================================================================

def _inject_writer(monkeypatch, helper_module, failures: list[str]):
    """Inject typed failures into _write_atomic by target kind ('report'/'result')."""
    real = helper_module._write_atomic
    state = {"report_done": False}
    seen: list[str] = []

    def fake(path, text):
        name = Path(str(path)).name
        seen.append(name)
        if name == "report.json":
            state["report_done"] = True
            if "report" in failures:
                raise OSError("synthetic report publication failure")
        elif name == "result.json":
            if "result" in failures:
                raise OSError("synthetic result publication failure")
        return real(path, text)

    monkeypatch.setattr(helper_module, "_write_atomic", fake)
    return seen, state


def test_b05_report_write_failure_after_output_leaves_no_result(monkeypatch, tmp_path):
    """Invariant: output succeeded but report publication failed -> result must
    be absent (incomplete publication); stdout bytes may exist as partial
    evidence; exactly one spawn/turn (no replay).

    FINDING F1 (labeled characterization): the artifact-publication OSError
    escapes helper.main UNHANDLED — an untyped traceback exit instead of the
    helper's documented 'typed codes go to stderr in every failure path'.
    Authority invariants hold; the typed-diagnostics contract does not.
    """
    seen, _ = _inject_writer(monkeypatch, helper, ["report"])
    raw = io.BytesIO()
    output = io.TextIOWrapper(raw, encoding="utf-8")
    try:
        with pytest.raises(OSError, match="synthetic report publication failure"):
            _invoke(monkeypatch, tmp_path, "report fails after bytes", output)
        assert "report.json" in seen  # reached the failing call order
        assert not (tmp_path / "result.json").exists()
        assert raw.getvalue() == "report fails after bytes".encode("utf-8")
    finally:
        output.close()


def test_b05_result_write_failure_keeps_report_without_result(monkeypatch, tmp_path):
    """Invariant: report published, result write failed -> report may exist,
    result must NOT exist (completion authority withheld). F1 applies here
    too (untyped escape); the publication invariants hold."""
    seen, state = _inject_writer(monkeypatch, helper, ["result"])
    raw = io.BytesIO()
    output = io.TextIOWrapper(raw, encoding="utf-8")
    try:
        with pytest.raises(OSError, match="synthetic result publication failure"):
            _invoke(monkeypatch, tmp_path, "result write fails", output)
        assert state["report_done"]
        published = json.loads((tmp_path / "report.json").read_bytes())
        assert published["response_sha256"] == hashlib.sha256(
            raw.getvalue()).hexdigest()
        assert not (tmp_path / "result.json").exists()
    finally:
        output.close()


def test_b05_collector_barrier_never_observes_result_before_flush(monkeypatch, tmp_path):
    """Deterministic barrier: while the report is being written (after output
    flush), result.json must not yet exist for a concurrent collector; the
    result becomes visible only after both artifacts are published."""
    import unittest.mock as mock
    flushed = threading.Event()
    observed: list[bool] = []
    real_write = helper._write_atomic

    class BarrierBinary(io.BytesIO):
        def flush(self):
            flushed.set()
            return super().flush()

    def probing_write(path, text):
        if Path(str(path)).name == "report.json":
            observed.append((tmp_path / "result.json").exists())
        return real_write(path, text)

    def watcher():
        if flushed.wait(10):
            observed.append((tmp_path / "result.json").exists())

    thread = threading.Thread(target=watcher, daemon=True)
    thread.start()
    raw = BarrierBinary()
    output = io.TextIOWrapper(raw, encoding="utf-8")
    try:
        with mock.patch.object(helper, "_write_atomic", side_effect=probing_write):
            rc, report = _invoke(monkeypatch, tmp_path, "barrier case", output)
        assert rc == 0
        assert report["response_sha256"] == hashlib.sha256(raw.getvalue()).hexdigest()
    finally:
        output.close()
        thread.join(5)
    assert observed, "barrier probes must have run"
    assert not any(observed), "result visible before report publication completed"


def test_b05_no_second_send_after_publication_failure(monkeypatch, tmp_path):
    """Invariant: publication failure never re-drives the provider turn within
    this execution. _invoke itself asserts calls == ["spawn", "turn"] on the
    success path; on the F1 untyped-escape path this test pins that the
    failure happens strictly AFTER the single spawn+turn (no replay)."""
    _inject_writer(monkeypatch, helper, ["result"])
    raw = io.BytesIO()
    output = io.TextIOWrapper(raw, encoding="utf-8")
    try:
        with pytest.raises(OSError, match="synthetic result publication failure"):
            _invoke(monkeypatch, tmp_path, "no replay after failure", output)
        # bytes were fully delivered by the single turn before publication
        assert raw.getvalue() == "no replay after failure".encode("utf-8")
        assert not (tmp_path / "result.json").exists()
    finally:
        output.close()


# ===========================================================================
# B06 — protocol budget (UTF-8 BYTES) + segmentation invariance
# ===========================================================================

def _drive_deltas(deltas, *, budget):
    transport = ScriptedTransport(
        [_create(), _prefs(), _subscribe_ok(), *[_delta(d) for d in deltas], _completed()])
    driver = ZCodeProtocolDriver(transport, max_response_bytes=budget)
    return driver.run_turn("prompt", workspace="A:/fake", deadline_seconds=10)


B06_BOUNDARIES = [
    ("ascii-exact", ["a" * 10], 10, True),
    ("ascii-one-over", ["a" * 11], 10, False),
    ("thai-exact", ["ไทย"], 9, True),          # 3 code points x 3 bytes
    ("thai-one-over", ["ไทย"], 8, False),
    ("emoji-exact", ["😀"], 4, True),           # 4-byte supplementary
    ("emoji-one-over", ["😀"], 3, False),
    ("combining-cross", ["e\u0301"], 2, False),  # 1 + 2 bytes > 2
    ("combining-exact", ["e\u0301"], 3, True),
]


@pytest.mark.parametrize("name,deltas,budget,ok", B06_BOUNDARIES,
    ids=[b[0] for b in B06_BOUNDARIES])
def test_b06_budget_counts_utf8_bytes_not_characters(name, deltas, budget, ok):
    """Invariant: the budget accumulates len(delta.encode('utf-8')); a valid
    turn at exactly the budget passes, one byte above fails closed."""
    if ok:
        turn = _drive_deltas(deltas, budget=budget)
        expected = "".join(deltas).encode("utf-8")
        assert turn.bytes_received == len(expected) == budget
        assert turn.response_text == "".join(deltas)
    else:
        with pytest.raises(ZCodeProtocolError) as exc:
            _drive_deltas(deltas, budget=budget)
        assert exc.value.code == "RESPONSE_BUDGET_EXCEEDED"


B06_SEGMENTATIONS = [
    ("whole", ["ไทย\r\n😀e\u0301\n"]),
    ("per-char", list("ไทย\r\n😀e\u0301\n")),
    ("crlf-split", ["ไทย\r", "\n😀e\u0301\n"]),   # delta boundary inside CRLF pair
    ("grapheme-split", ["ไทย\r\n", "😀", "e", "\u0301", "\n"]),  # combining mark split
]


@pytest.mark.parametrize("name,deltas", B06_SEGMENTATIONS,
    ids=[s[0] for s in B06_SEGMENTATIONS])
def test_b06_segmentation_invariance(name, deltas):
    """Invariant: identical logical text split across any text_delta
    segmentation yields identical final UTF-8 bytes and hash."""
    budget = 65536
    turn = _drive_deltas(deltas, budget=budget)
    expected = "ไทย\r\n😀e\u0301\n"
    assert turn.response_text == expected
    raw = turn.response_text.encode("utf-8")
    assert turn.bytes_received == len(raw)
    assert hashlib.sha256(raw).hexdigest() == hashlib.sha256(
        _drive_deltas([expected], budget=budget).response_text.encode("utf-8")).hexdigest()


def test_b06_budget_above_cap_rejected_before_spawn():
    """Invariant: validate_output_budget fails closed above the production cap."""
    from a_conductor.zcode_supervised_helper import (
        ZCODE_MAX_RESPONSE_BYTES, validate_output_budget)
    with pytest.raises(ValueError):
        validate_output_budget(ZCODE_MAX_RESPONSE_BYTES + 1)
    assert validate_output_budget(1) == 1


# ===========================================================================
# B07 — collector contract over a sacrificial store (no replay, CAS collect)
# ===========================================================================

def _service_with_record(tmp_path: Path):
    """Sacrificial store + real service; record refs point at the exact run
    directory the real helper just produced (copied into runs/<exec-id>/)."""
    from a_conductor.execution_store import SQLiteExecutionStore
    from a_conductor.supervised_execution import SupervisedExecutionService
    from tests.test_supervised_execution import FakeController, FakeObserver
    record_dir = tmp_path / "runs" / EXECUTION_ID
    record_dir.mkdir(parents=True, exist_ok=True)
    for name in ("stdout.log", "result.json", "report.json"):
        source = tmp_path / "run" / name
        if source.exists():
            (record_dir / name).write_bytes(source.read_bytes())
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    service = SupervisedExecutionService(
        store=store, controller=FakeController(), observer=FakeObserver(),
        allowed_target_executables=("python.exe",),
        python_executable=sys.executable, startup_poll_attempts=2)
    created = store.create(make_record(tmp_path, EXECUTION_ID))
    return service, created


def test_b07_failed_publication_is_never_result_available(tmp_path):
    """Invariant (end-to-end): a REAL helper run whose artifact directory is
    unusable fails TYPED (IDENTITY_WRITE_FAILED, after child spawn but BEFORE
    any protocol send) -> no stdout bytes, no report, no result; the collector
    sees recovery-required, NOT completion; exactly one spawn, zero sends
    (the provider turn never ran — no replay by construction).
    (Late publication failure after output is proven in-process by B05.)"""
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    result_path = blocker / "nested" / "result.json"
    case = CORPUS["ascii"]
    result = _run_helper(tmp_path, response=case["text"], result_path=result_path)
    assert result.returncode != 0
    assert b"IDENTITY_WRITE_FAILED" in result.stderr
    run = tmp_path / "run"
    assert (run / "stdout.log").read_bytes() == b""
    assert not (run / "report.json").exists()
    assert not result_path.exists()

    service, created = _service_with_record(tmp_path)  # result.json not copied
    (tmp_path / "runs" / EXECUTION_ID / "result.json").unlink(missing_ok=True)
    inspection = service.inspect(created.execution_id)
    assert inspection.state is not SupervisedInspectionState.RESULT_AVAILABLE
    assert not inspection.result_available
    # exactly one spawn, zero protocol sends — the turn never ran
    assert len((tmp_path / "receipts" / "spawn.pid").read_text().splitlines()) == 1
    assert not (tmp_path / "receipts" / "send_receipt.json").exists()


def test_b07_successful_collect_is_cas_fenced(tmp_path):
    """Invariant: with result.json present the collector reports
    RESULT_AVAILABLE and collect consumes it exactly once under version CAS;
    a repeat collect at the same version is rejected, not double-consumed."""
    case = CORPUS["thai_inherent"]
    result = _run_helper(tmp_path, response=case["text"])
    assert result.returncode == 0, result.stderr
    service, created = _service_with_record(tmp_path)
    inspection = service.inspect(created.execution_id)
    assert inspection.state is SupervisedInspectionState.RESULT_AVAILABLE
    outcome = service.collect(created.execution_id, expected_version=created.version)
    assert outcome.record.execution_id == created.execution_id
    from a_conductor.execution_store import ExecutionStoreError
    with pytest.raises(ExecutionStoreError):
        service.collect(created.execution_id, expected_version=created.version)
    # collecting artifacts did NOT spawn a new child anywhere
    assert len((tmp_path / "receipts" / "spawn.pid").read_text().splitlines()) == 1
