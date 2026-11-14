"""Read-only local inspector collectors for WO-P1-739.

Guarantee: never write files, spawn processes, load secret environments,
or grant runtime authority. Only discovery and bounded health reads are allowed.
Each collector returns (rows, degraded_notes), with code-only degradation.
Omitted probe uses the existing health check; explicit None is discovery-only.
Marker discovery is per-instance and tolerant; pairing IDs are never emitted.
"""

from __future__ import annotations

import errno
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import EllipsisType
from typing import Callable

from .inspector_projection import (
    HookInspectorRow,
    SkillInspectorRow,
    ToolInspectorRow,
    build_inspector_views,
)


def _read_text(path: Path, limit: int = 262144) -> str:
    with path.open("r", encoding="utf-8-sig") as handle:
        text = handle.read(limit + 1)
    if len(text) > limit:
        raise ValueError("INSPECTOR_SOURCE_OVERSIZED")
    return text


def _json_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("INSPECTOR_SOURCE_DUPLICATE_KEY")
        result[key] = value
    return result


def _safe_row(
    row: ToolInspectorRow | HookInspectorRow | SkillInspectorRow,
) -> ToolInspectorRow | HookInspectorRow | SkillInspectorRow:
    section = {ToolInspectorRow: "tools", HookInspectorRow: "hooks", SkillInspectorRow: "skills"}[type(row)]
    inputs = {"tools": (), "hooks": (), "skills": (), section: (row,)}
    projected = build_inspector_views(**inputs)
    return type(row)(**projected[section][0])


# Only these generic OSError errnos establish transport failure. ConnectionError
# and TimeoutError also establish transport failure; permissions/config do not.
_TRANSPORT_ERRNOS = frozenset({
    errno.ECONNREFUSED, errno.ECONNRESET, errno.EHOSTUNREACH, errno.ETIMEDOUT,
})


def collect_local_tool_rows(
    instances_root: Path | str | None = None,
    *,
    probe: Callable[[object], object] | None | EllipsisType = ...,
) -> tuple[tuple[ToolInspectorRow, ...], tuple[str, ...]]:
    """Tolerantly parse shared marker syntax; None disables all health probes."""
    rows, notes = [], []
    try:
        from . import local_instances

        root = Path(instances_root if instances_root is not None
                    else local_instances.default_instances_root()).expanduser().resolve(strict=False)
        if not root.is_dir():
            return (), ()
        active_probe = local_instances.instance_health_state if probe is ... else probe
        for child in sorted(root.iterdir()):
            try:
                marker = child / "instance.ps1"
                if not child.is_dir() or not marker.is_file():
                    continue
                fields = {key: value.replace("''", "'") for key, value in
                          local_instances._INSTANCE_LINE_RE.findall(_read_text(marker))}
                name = fields.get("InstanceName", "").strip()
                project = fields.get("ProjectPath", "").strip()
                address = fields.get("HealthListenAddress", "").strip()
                if not name or not project or not address:
                    raise ValueError("TOOL_MARKER_INVALID")
                tunnel_path = child / "config" / "tunnel-id.txt"
                configured = False
                if tunnel_path.is_file():
                    configured = local_instances._TUNNEL_ID_RE.fullmatch(
                        _read_text(tunnel_path, 256).strip(),
                    ) is not None
                instance = local_instances.LocalInstance(
                    name=name, project_path=project, health_address=address,
                    instance_root=child.resolve(strict=False), tunnel_configured=configured,
                )
            except Exception:
                suffix = hashlib.sha256(child.name.encode("utf-8", errors="replace")).hexdigest()[:12]
                notes.append(f"TOOL_MARKER_UNREADABLE:{suffix}")
                continue
            try:
                state, phase, error = "UNKNOWN", "REGISTERED", ""
                verified = None
                if active_probe is not None:
                    try:
                        health = active_probe(instance)
                        health = getattr(health, "value", health)
                        verified = datetime.now(timezone.utc).isoformat()
                        if health == "READY":
                            state = "READY"
                            phase = "CONNECTED" if instance.tunnel_configured else "STARTED"
                        elif health in ("STOPPED", "TRANSPORT_ERROR"):
                            state = "DISCONNECTED"
                    except OSError as exc:
                        if isinstance(exc, (ConnectionError, TimeoutError)) or exc.errno in _TRANSPORT_ERRNOS:
                            state, error = "DISCONNECTED", "TOOL_PROBE_TRANSPORT_ERROR"
                        else:
                            state, error = "DEGRADED", "TOOL_PROBE_FAILED"
                    except Exception:
                        state, error = "DEGRADED", "TOOL_PROBE_FAILED"
                if error:
                    notes.append(error)
                rows.append(_safe_row(ToolInspectorRow(
                    name=instance.name, device="windows-local", category="connector",
                    source="instance.ps1 discovery", phase=phase, state=state,
                    registration_evidence="instance.ps1", last_verified=verified,
                    last_error=error, next_safe_action="Inspect health evidence",
                    provenance="discovery-only" if active_probe is None else "probe:readyz",
                )))
            except Exception:
                notes.append("TOOL_ENTRY_INVALID")
    except Exception:
        notes.append("TOOLS_DISCOVERY_UNAVAILABLE")
    return tuple(rows), tuple(dict.fromkeys(notes))


def collect_local_hook_rows(
    repo_root: Path | str,
) -> tuple[tuple[HookInspectorRow, ...], tuple[str, ...]]:
    """Read static contracts, never infer runtime hook liveness from presence."""
    rows, notes = [], []
    try:
        root = Path(repo_root)
        contracts = root / "docs" / "contracts"
        guard_mode = "UNKNOWN"
        policy = contracts / "hook-contract-v1.md"
        if policy.is_file():
            try:
                text = _read_text(policy)
                # A vocabulary listing both modes is not policy evidence.
                if re.search(r"GUARD hooks MUST use FAIL_CLOSED", text) or re.search(
                    r"`FAIL_CLOSED` is the default", text,
                ):
                    guard_mode = "FAIL_CLOSED"
            except Exception:
                notes.append("HOOK_CONTRACT_UNAVAILABLE")
        sources = (
            ("HookBus", contracts / "hook-contract-v1.schema.json"),
            ("control-hook-adapter", root / "src" / "a_conductor" / "control_hook_adapter.py"),
            ("claude-hook-adapter", contracts / "claude-hook-adapter-v1.md"),
            ("kilo-hook-adapter", contracts / "kilo-hook-adapter-v1.md"),
        )
        for name, path in sources:
            try:
                text = _read_text(path)
            except Exception:
                notes.append("HOOK_CONTRACT_UNAVAILABLE")
                continue
            try:
                if name == "HookBus":
                    schema = json.loads(text, object_pairs_hook=_json_object)
                    if schema.get("$id") != "urn:a-conductor:schema:hook-contract:1.0.0":
                        raise ValueError("HOOK_CONTRACT_INVALID")
                    classes = schema["properties"]["hook_class"]["enum"]
                    if (type(classes) is not list or len(classes) != 4
                            or set(classes) != {"OBSERVE", "ADVISORY", "GUARD", "COMMAND"}):
                        raise ValueError("HOOK_CONTRACT_INVALID")
                else:
                    if "1.0.0" not in text or "OBSERVE" not in text:
                        raise ValueError("HOOK_CONTRACT_INVALID")
                    classes = ["OBSERVE"]
                for hook_class in classes:
                    rows.append(_safe_row(HookInspectorRow(
                        name=f"HookBus:{hook_class}" if name == "HookBus" else name,
                        hook_class=hook_class,
                        authority_source=f"{path.relative_to(root).as_posix()}:1.0.0",
                        enabled=True, fail_mode=guard_mode if hook_class == "GUARD" else "UNKNOWN",
                        state="UNKNOWN", last_event="", last_error="", provenance="contract-only",
                    )))
            except Exception:
                notes.append("HOOK_CONTRACT_INVALID")
    except Exception:
        notes.append("HOOK_CONTRACT_UNAVAILABLE")
    return tuple(rows), tuple(dict.fromkeys(notes))


@dataclass(frozen=True, slots=True)
class SkillRegistrySnapshot:
    """Validated raw-entry snapshot of schema-v3 skills-registry.json (WO-P1-755).

    ``entries`` are the validated raw registry dicts in registry order, aligned
    with ``entry_states`` (per-entry inspector staleness) and ``duplicate_flags``
    (computed over RAW entry names, so invalid entries with repeated names still
    count). ``invalid_entry_count`` lets callers reproduce the per-entry
    ``SKILL_ENTRY_INVALID`` degradation notes. ``generated_at`` mirrors the
    registry meta string (None when absent or non-string), ``staleness`` is the
    registry-level mtime freshness (``AVAILABLE``/``STALE``/``UNKNOWN``) and
    ``source_path`` is the resolved registry file path.
    """

    entries: tuple[dict[str, object], ...]
    entry_states: tuple[str, ...]
    duplicate_flags: tuple[bool, ...]
    invalid_entry_count: int
    generated_at: str | None
    staleness: str
    source_path: str


def _validate_skill_entry(entry: object) -> None:
    required = ("name", "domain", "lifecycle_phase", "category", "source", "path", "status")
    if type(entry) is not dict or any(key not in entry for key in required):
        raise ValueError("SKILL_ENTRY_INVALID")
    for key in ("name", "lifecycle_phase", "category", "source", "path", "status"):
        if type(entry[key]) is not str or not entry[key].strip():
            raise ValueError("SKILL_ENTRY_INVALID")
    if entry["status"] not in ("canonical", "alias", "deprecated"):
        raise ValueError("SKILL_ENTRY_INVALID")
    for key in ("domain", "agents", "triggers", "aliases"):
        if type(entry.get(key, [])) is not list or any(
            type(item) is not str for item in entry.get(key, [])
        ):
            raise ValueError("SKILL_ENTRY_INVALID")
    for key in ("invocation_hint", "a_phase", "canonical", "version", "description"):
        if key in entry and type(entry[key]) is not str:
            raise ValueError("SKILL_ENTRY_INVALID")


def load_skill_registry(
    awiki_root: Path | str,
    *,
    max_age_seconds: int,
    now: datetime | None = None,
) -> SkillRegistrySnapshot:
    """Load and validate schema-v3 skills-registry.json into a snapshot.

    Either returns a :class:`SkillRegistrySnapshot` or raises
    ``ValueError("SKILLS_REGISTRY_UNAVAILABLE")`` — never any other failure
    type. Freshness uses file mtime, never JSON text. This is the shared read
    path for every skills-registry consumer; callers must not re-read or
    re-validate the file themselves.
    """
    try:
        root = Path(awiki_root).resolve()
        registry = root / "skills-registry.json"
        current = datetime.now(timezone.utc) if now is None else now
        if (type(max_age_seconds) is not int or max_age_seconds < 0
                or not isinstance(current, datetime) or current.tzinfo is None
                or current.utcoffset() is None):
            raise ValueError("SKILLS_REGISTRY_UNAVAILABLE")
        data = json.loads(_read_text(registry, 4 * 1024 * 1024), object_pairs_hook=_json_object)
        if (type(data) is not dict or data.get("schema_version") != 3
                or type(data.get("skills")) is not list or len(data["skills"]) > 4096):
            raise ValueError("SKILLS_REGISTRY_UNAVAILABLE")
        age = current.timestamp() - registry.stat().st_mtime
        entries = data["skills"]
        raw_name_counts = Counter(entry["name"] for entry in entries
                                  if type(entry) is dict and type(entry.get("name")) is str)
        valid: list[dict[str, object]] = []
        states: list[str] = []
        duplicates: list[bool] = []
        invalid_count = 0
        for entry in entries:
            try:
                _validate_skill_entry(entry)
            except Exception:
                invalid_count += 1
                continue
            state = "UNKNOWN"
            path = Path(entry["path"])
            # Do not follow absolute, home-relative or escaping registry paths.
            # Those describe another environment, not this explicit repo root.
            if not path.is_absolute() and not entry["path"].startswith("~"):
                skill_path = (root / path).resolve()
                if skill_path.is_relative_to(root) and skill_path.exists():
                    if age >= 0:
                        state = "STALE" if age > max_age_seconds else "AVAILABLE"
            valid.append(entry)
            states.append(state)
            duplicates.append(raw_name_counts[entry["name"]] > 1)
        generated_at = data.get("generated_at")
        staleness = "UNKNOWN" if age < 0 else ("STALE" if age > max_age_seconds else "AVAILABLE")
        return SkillRegistrySnapshot(
            entries=tuple(valid),
            entry_states=tuple(states),
            duplicate_flags=tuple(duplicates),
            invalid_entry_count=invalid_count,
            generated_at=generated_at if type(generated_at) is str else None,
            staleness=staleness,
            source_path=str(registry),
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("SKILLS_REGISTRY_UNAVAILABLE") from exc


def collect_local_skill_rows(
    awiki_root: Path | str = Path(r"A:\GitHub\A-Wiki"),
    *,
    max_age_seconds: int = 7 * 24 * 60 * 60,
    now: datetime | None = None,
) -> tuple[tuple[SkillInspectorRow, ...], tuple[str, ...]]:
    """Read schema-v3 skills-registry.json; freshness uses file mtime, not JSON."""
    rows, notes = [], []
    try:
        snapshot = load_skill_registry(awiki_root, max_age_seconds=max_age_seconds, now=now)
    except Exception:
        notes.append("SKILLS_REGISTRY_UNAVAILABLE")
        return tuple(rows), tuple(dict.fromkeys(notes))
    notes.extend(["SKILL_ENTRY_INVALID"] * snapshot.invalid_entry_count)
    for entry, state, duplicate in zip(
        snapshot.entries, snapshot.entry_states, snapshot.duplicate_flags,
    ):
        try:
            hint = ", ".join(entry.get("triggers", []))
            if entry.get("invocation_hint"):
                hint = "; ".join(filter(None, (hint, entry["invocation_hint"])))
            rows.append(_safe_row(SkillInspectorRow(
                name=entry["name"], state=state, registry_source="skills-registry.json",
                routing_hint=hint, harness=", ".join(entry.get("agents", [])),
                deprecated=entry["status"] == "deprecated", duplicate=duplicate,
                provenance="registry-only",
            )))
        except Exception:
            notes.append("SKILL_ENTRY_INVALID")
    return tuple(rows), tuple(dict.fromkeys(notes))
