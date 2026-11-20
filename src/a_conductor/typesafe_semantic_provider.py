"""WO-P1-505 JEV-2B live TypeSafe/Jev semantic provider adapter.

Minimal live adapter behind the accepted provider-neutral
``SemanticDecisionProvider`` seam from WO-P1-502 (#502). It renders one
deterministic ``POST /v1/systemone`` request per ``SemanticDecisionRequest``
through an injected transport boundary and normalizes the response into the
provider-neutral :class:`SemanticEvidence` envelope.

Reused, not reinvented:

- decision vocabulary, typed error kinds, evidence envelope and the
  fail-closed escalation policy come from ``semantic_decision`` (#502);
- endpoint, pinned versioned model, request/response field sets, error
  statuses and strict normalization mirror the accepted JEV-1B/JEV-1C
  contracts (``scripts/jev_typesafe_contract.py``,
  ``scripts/jev_shadow_benchmark.py``);
- credentials resolve only at the call boundary through an injected
  secret-reference resolver matching the accepted A-Wiki environment
  resolver (``awiki_environment_resolver``); no secret store is created.

Boundaries:

- unit tests are network-free: every test injects a fake transport;
  :class:`UrllibTypeSafeTransport` exists for the later live gate only;
- one transport call per ``evaluate``: no internal retry, and an ambiguous
  transport outcome is never blind-replayed by this adapter;
- every failure mode (timeout, 401/403, 429, 529, other 5xx, network,
  malformed JSON/shape, model mismatch, non-finite/out-of-range
  probabilities, invalid measurement) becomes typed non-authoritative
  evidence that deterministically escalates upstream;
- the adapter never raises across the provider boundary;
- ``evidence.authoritative_for_action`` is always ``False`` and this module
  grants no claim, mutation, review, merge, completion, routing or SSoT
  authority; modes OFF/SHADOW/ADVISORY remain decisions of the #502 core;
- the credential value is never persisted, logged or returned; it appears
  only inside the transport request headers.
"""

from __future__ import annotations

import json
import math
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from .semantic_decision import (
    SemanticDecisionFamily,
    SemanticDecisionRequest,
    SemanticEvidence,
    SemanticEvidenceErrorKind,
    SemanticPrimitive,
    SemanticProviderError,
)

TYPESAFE_PROVIDER_NAME = "typesafe"
TYPESAFE_SYSTEMONE_URL = "https://api.typesafe.ai/v1/systemone"
PINNED_TYPESAFE_MODEL = "jev-1.13.0"
DEFAULT_TYPESAFE_QUESTION_ID = "decision"
SECRET_REFERENCE_PREFIX = "secret-ref:"

# Mirrors the JEV-1B pinned-version rule: versioned model IDs only, never a
# moving alias such as "jev-latest".
_VERSIONED_JEV_RE = re.compile(r"^jev-\d+\.\d+\.\d+$")

TYPESAFE_MAX_REQUEST_BYTES = 262_144
TYPESAFE_MAX_RESPONSE_BYTES = 1_048_576
_PROBABILITY_SUM_TOLERANCE = 1e-6
_CREDENTIAL_MAX_LENGTH = 512
_REFERENCE_MAX_LENGTH = 512
_DETAIL_MAX = 512
_DEFAULT_TIMEOUT_SECONDS = 10.0
_MIN_TIMEOUT_SECONDS = 1.0
_MAX_TIMEOUT_SECONDS = 120.0

# JEV-1C strict field sets for the /v1/systemone response body.
_RESPONSE_TOP_LEVEL_FIELDS = frozenset({"model", "answers", "usage"})
_RESPONSE_USAGE_FIELDS = frozenset({"input_tokens", "output_tokens"})
_CHOICE_ANSWER_FIELDS = frozenset({"type", "choice", "probabilities", "confidence"})
_SCORE_ANSWER_FIELDS = frozenset(
    {"type", "score", "legend", "probabilities", "confidence"}
)
_NOUL_ANSWER_FIELDS = frozenset({"type", "noul"})

_FAMILY_TEMPLATES: Mapping[SemanticDecisionFamily, Mapping[str, Any]] = {
    SemanticDecisionFamily.TASK_CLASSIFICATION: {
        "type": "choice",
        "instructions": "Classify the requested repository task by its primary delivery intent.",
        "criteria": {
            "bugfix": "Restore existing behavior that is broken, regressed, or producing an incorrect result.",
            "feature": "Add a new product capability or behavior that did not previously exist.",
            "docs": "Change documentation, governance, plans, or explanatory text without product behavior mutation.",
            "review": "Inspect or evaluate an existing candidate and report findings without implementing the change.",
        },
    },
    SemanticDecisionFamily.SKILL_SUGGESTION: {
        "type": "choice",
        "instructions": "Select the one specialized workflow that best matches the requested work.",
        "criteria": {
            "repo_semantic": "Navigate repository code semantically: symbols, references, call graph, definitions, or code structure.",
            "pdf": "Create, edit, transform, or analyze a PDF artifact.",
            "slides": "Create or edit a slide presentation or PowerPoint artifact.",
            "spreadsheet": "Create, edit, transform, or analyze a spreadsheet or workbook artifact.",
            "none": "No specialized workflow above is needed.",
        },
    },
    SemanticDecisionFamily.FAILURE_CLASSIFICATION: {
        "type": "choice",
        "instructions": "Classify the observed failure by its primary failure class.",
        "criteria": {
            "CODE_FAILURE": "Production or implementation code is invalid or behaves incorrectly.",
            "TEST_FAILURE": "A test assertion, test setup, or test execution reports a failing expected behavior.",
            "TRANSPORT_FAILURE": "A connection, session, tunnel, or transport path failed without proving the underlying execution failed.",
            "RATE_LIMITED": "The provider rejected or delayed work because a quota or request/token rate limit was reached.",
            "AUTH_FAILURE": "Authentication or authorization failed because credentials or permissions are missing, invalid, expired, or denied.",
        },
    },
    SemanticDecisionFamily.EVIDENCE_RELEVANCE: {
        "type": "noul",
        "instructions": "Does the supplied evidence directly support the stated claim?",
        "criteria": {
            "true": "The evidence directly demonstrates the claim under the relevant identity, scope, or artifact.",
            "false": "The evidence is missing, indirect, from the wrong artifact/population, or does not establish the claim.",
        },
    },
    SemanticDecisionFamily.ESCALATION_DECISION: {
        "type": "noul",
        "instructions": "Should this case escalate to stronger reasoning, the integrator, or a human because authority, risk, ambiguity, or evidence remains unresolved?",
        "criteria": {
            "true": "The case has unresolved authority, consequential risk, conflicting evidence, or material ambiguity that bounded deterministic handling cannot safely resolve.",
            "false": "The case has a clear deterministic/local handling path and no unresolved consequential authority or ambiguity.",
        },
    },
}

_SECRET_PATTERNS = (
    re.compile(r"apikey_[A-Za-z0-9]{16,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{16,}", re.IGNORECASE),
    re.compile(
        r"(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)"
        r"\s*[:=]\s*[A-Za-z0-9+/=_-]{12,}",
        re.IGNORECASE,
    ),
)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class TypeSafeAdapterError(ValueError):
    """Raised when the adapter is constructed with an invalid pinned contract."""


class _ResponseContractError(ValueError):
    """Internal: a response violated the strict TypeSafe contract."""


@runtime_checkable
class TypeSafeSecretResolver(Protocol):
    """Matches the accepted A-Wiki environment resolver surface."""

    def resolve(self, reference: str) -> str: ...


@dataclass(frozen=True)
class TypeSafeHTTPRequest:
    """Bounded wire request handed to the transport boundary."""

    url: str
    headers: Mapping[str, str]
    body: str
    timeout_seconds: float


@dataclass(frozen=True)
class TypeSafeHTTPResponse:
    """Normalized transport outcome; timing is owned by the transport."""

    status_code: int
    body: str
    elapsed_ms: float


@runtime_checkable
class TypeSafeTransport(Protocol):
    """Injected transport boundary performing exactly one POST per call."""

    def post(self, request: TypeSafeHTTPRequest) -> TypeSafeHTTPResponse: ...


def _has_secret_shape(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)


def _redact_detail(detail: str) -> str:
    """Sanitize an error detail before it enters an evidence envelope."""

    if _has_secret_shape(detail):
        return "[REDACTED]"
    cleaned = _CONTROL_RE.sub(" ", detail).strip()
    if len(cleaned) > _DETAIL_MAX:
        cleaned = cleaned[:_DETAIL_MAX]
    return cleaned or "typesafe provider error"


def _reason_chain_is_timeout(exc: BaseException) -> bool:
    current: object = exc
    for _ in range(4):
        if isinstance(current, TimeoutError):
            return True
        current = getattr(current, "reason", None)
        if current is None:
            return False
    return False


def classify_transport_exception(
    exc: BaseException,
) -> SemanticEvidenceErrorKind:
    """Map a transport exception onto the provider-neutral error vocabulary."""

    if isinstance(exc, TimeoutError) or _reason_chain_is_timeout(exc):
        return SemanticEvidenceErrorKind.TIMEOUT
    if isinstance(exc, UnicodeDecodeError):
        return SemanticEvidenceErrorKind.SCHEMA
    if isinstance(exc, OSError):
        return SemanticEvidenceErrorKind.TRANSPORT
    return SemanticEvidenceErrorKind.UNKNOWN


def http_error_kind(status_code: int) -> SemanticEvidenceErrorKind | None:
    """Map a non-200 HTTP status onto the typed error vocabulary."""

    if 200 <= status_code < 300:
        return None
    if status_code in (401, 403):
        return SemanticEvidenceErrorKind.AUTH
    if status_code == 429:
        return SemanticEvidenceErrorKind.RATE_LIMIT
    if status_code == 422:
        return SemanticEvidenceErrorKind.SCHEMA
    if status_code == 529:
        return SemanticEvidenceErrorKind.OVERLOAD
    if status_code >= 500:
        return SemanticEvidenceErrorKind.TRANSPORT
    return SemanticEvidenceErrorKind.UNKNOWN


def _json_safe(value: Any) -> Any:
    """Convert frozen core state (MappingProxyType/tuple) to plain JSON data."""

    if isinstance(value, Mapping):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _build_question(request: SemanticDecisionRequest) -> dict[str, Any]:
    template = _FAMILY_TEMPLATES.get(request.family)
    if template is None:
        raise _ResponseContractError(
            f"decision family {request.family.value!r} is not admitted for live TypeSafe routing"
        )

    expected_type = template["type"]
    if request.primitive.value != expected_type:
        raise _ResponseContractError(
            "request primitive does not match the admitted family template"
        )

    criteria = template["criteria"]
    if request.primitive is SemanticPrimitive.CHOICE:
        assert isinstance(criteria, Mapping)
        if tuple(criteria.keys()) != request.options:
            raise _ResponseContractError(
                "choice options must exactly match the admitted family template"
            )
    elif request.primitive is not SemanticPrimitive.NOUL:
        raise _ResponseContractError(
            "only admitted Choice/Noul families may use the live TypeSafe adapter"
        )

    return {
        "type": expected_type,
        "instructions": template["instructions"],
        "criteria": dict(criteria) if isinstance(criteria, Mapping) else list(criteria),
    }


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _validated_probability(value: Any, field: str) -> float:
    number = _finite_number(value)
    if number is None or not 0.0 <= number <= 1.0:
        raise _ResponseContractError(f"{field} must be a probability in [0, 1]")
    return number


def _validated_confidence(answer: Mapping[str, Any]) -> float:
    if "confidence" not in answer:
        raise _ResponseContractError("answer confidence is required")
    return _validated_probability(answer["confidence"], "answer.confidence")


def _validated_probabilities(
    answer: Mapping[str, Any], expected_keys: tuple[str, ...]
) -> dict[str, float]:
    raw = answer.get("probabilities")
    if not isinstance(raw, Mapping):
        raise _ResponseContractError("answer probabilities must be an object")
    if set(raw) != set(expected_keys):
        raise _ResponseContractError(
            "answer probabilities must contain exactly the declared keys"
        )
    normalized = {
        key: _validated_probability(raw[key], f"answer.probabilities[{key!r}]")
        for key in expected_keys
    }
    total = math.fsum(normalized.values())
    if not math.isclose(total, 1.0, abs_tol=_PROBABILITY_SUM_TOLERANCE):
        raise _ResponseContractError(
            "answer probabilities must sum to 1 within tolerance"
        )
    return normalized


def _validated_usage(payload: Mapping[str, Any]) -> tuple[int, int]:
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        raise _ResponseContractError("usage must be an object")
    if set(usage) != set(_RESPONSE_USAGE_FIELDS):
        raise _ResponseContractError(
            "usage fields must be exactly input_tokens and output_tokens"
        )
    values: list[int] = []
    for name in ("input_tokens", "output_tokens"):
        value = usage[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise _ResponseContractError(f"usage.{name} must be a non-negative integer")
        values.append(value)
    return values[0], values[1]


def _validated_answer(
    payload: Mapping[str, Any], request: SemanticDecisionRequest
) -> tuple[Any, float | None, dict[str, float] | None]:
    answers = payload.get("answers")
    if not isinstance(answers, Mapping):
        raise _ResponseContractError("answers must be an object")
    if set(answers) != {DEFAULT_TYPESAFE_QUESTION_ID}:
        raise _ResponseContractError(
            "answers must contain exactly the requested question id"
        )
    answer = answers[DEFAULT_TYPESAFE_QUESTION_ID]
    if not isinstance(answer, Mapping):
        raise _ResponseContractError("answer must be an object")
    if answer.get("type") != request.primitive.value:
        raise _ResponseContractError("answer type does not match request primitive")

    primitive = request.primitive
    if primitive is SemanticPrimitive.CHOICE:
        if set(answer) != set(_CHOICE_ANSWER_FIELDS):
            raise _ResponseContractError(
                "choice answer fields must be exactly "
                "type, choice, probabilities, confidence"
            )
        confidence = _validated_confidence(answer)
        probabilities = _validated_probabilities(answer, tuple(request.options))
        return answer.get("choice"), confidence, probabilities

    if primitive is SemanticPrimitive.SCORE:
        if set(answer) != set(_SCORE_ANSWER_FIELDS):
            raise _ResponseContractError(
                "score answer fields must be exactly "
                "type, score, legend, probabilities, confidence"
            )
        legend = answer.get("legend")
        if not isinstance(legend, Mapping):
            raise _ResponseContractError("score legend must be an object")
        levels = request.score_levels
        assert levels is not None
        expected_keys = tuple(str(index) for index in range(levels))
        if set(legend) != set(expected_keys):
            raise _ResponseContractError(
                "score legend keys must match declared levels"
            )
        for key, value in legend.items():
            if not isinstance(value, str):
                raise _ResponseContractError(
                    f"score legend[{key!r}] must be a string"
                )
        confidence = _validated_confidence(answer)
        probabilities = _validated_probabilities(answer, expected_keys)
        return answer.get("score"), confidence, probabilities

    if set(answer) != set(_NOUL_ANSWER_FIELDS):
        raise _ResponseContractError(
            "noul answer fields must be exactly type and noul; "
            "invented confidence or probabilities are rejected"
        )
    return answer.get("noul"), None, None


def _validated_response_payload(
    response: TypeSafeHTTPResponse, request: SemanticDecisionRequest, model: str
) -> SemanticEvidence:
    try:
        payload = json.loads(response.body)
    except (ValueError, RecursionError) as exc:
        raise _ResponseContractError("response body is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise _ResponseContractError("response payload must be an object")
    if set(payload) != set(_RESPONSE_TOP_LEVEL_FIELDS):
        raise _ResponseContractError(
            "response top-level fields must be exactly model, answers, usage"
        )
    if payload.get("model") != model:
        raise _ResponseContractError("response model does not match pinned model")

    input_usage, output_usage = _validated_usage(payload)
    answer, confidence, probabilities = _validated_answer(payload, request)
    return SemanticEvidence(
        provider=TYPESAFE_PROVIDER_NAME,
        model=model,
        primitive=request.primitive,
        answer=answer,
        confidence=confidence,
        probabilities=probabilities,
        input_usage=input_usage,
        output_usage=output_usage,
        latency_ms=float(response.elapsed_ms),
    )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject every redirect so Authorization can never follow a new target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibTypeSafeTransport:
    """Production stdlib transport for the still-gated live TypeSafe call.

    Redirects are rejected, reads are bounded, HTTP error bodies are discarded,
    and response bytes must be strict UTF-8. Timeout/network failures propagate
    for :func:`classify_transport_exception`.
    """

    def __init__(
        self,
        *,
        opener: Any | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if opener is None:
            opener = urllib.request.build_opener(_NoRedirectHandler())
        if not callable(getattr(opener, "open", None)):
            raise TypeSafeAdapterError("opener must provide open()")
        if not callable(monotonic):
            raise TypeSafeAdapterError("monotonic must be callable")
        self._opener = opener
        self._monotonic = monotonic

    def post(self, request: TypeSafeHTTPRequest) -> TypeSafeHTTPResponse:
        started = self._monotonic()
        wire = urllib.request.Request(
            request.url,
            data=request.body.encode("utf-8"),
            headers=dict(request.headers),
            method="POST",
        )
        try:
            with self._opener.open(wire, timeout=request.timeout_seconds) as resp:
                status = int(resp.status)
                raw = resp.read(TYPESAFE_MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            raw = b""
        elapsed_ms = (self._monotonic() - started) * 1000.0
        return TypeSafeHTTPResponse(
            status_code=status,
            body=raw.decode("utf-8", errors="strict"),
            elapsed_ms=elapsed_ms,
        )


class TypeSafeSemanticDecisionProvider:
    """Live TypeSafe/Jev adapter for the #502 SemanticDecisionProvider seam.

    Configuration is pinned at construction (endpoint constant, versioned
    model, secret reference, timeout); the credential is resolved from the
    injected resolver only inside :meth:`evaluate`.
    """

    def __init__(
        self,
        *,
        transport: TypeSafeTransport,
        secret_resolver: TypeSafeSecretResolver,
        api_key_reference: str = "secret-ref:awiki-env/TYPESAFE_API_KEY",
        model: str = PINNED_TYPESAFE_MODEL,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not callable(getattr(transport, "post", None)):
            raise TypeSafeAdapterError("transport must provide post()")
        if not callable(getattr(secret_resolver, "resolve", None)):
            raise TypeSafeAdapterError("secret_resolver must provide resolve()")

        if not isinstance(api_key_reference, str) or not (
            api_key_reference.startswith(SECRET_REFERENCE_PREFIX)
            and len(api_key_reference) <= _REFERENCE_MAX_LENGTH
            and not _CONTROL_RE.search(api_key_reference)
        ):
            raise TypeSafeAdapterError(
                "api_key_reference must be a bounded secret-ref: reference"
            )
        if not isinstance(model, str) or _VERSIONED_JEV_RE.fullmatch(model) is None:
            raise TypeSafeAdapterError(
                "model must be a pinned versioned Jev model ID such as "
                f"{PINNED_TYPESAFE_MODEL!r}; moving aliases are rejected"
            )
        timeout = timeout_seconds
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(float(timeout))
            or not _MIN_TIMEOUT_SECONDS <= float(timeout) <= _MAX_TIMEOUT_SECONDS
        ):
            raise TypeSafeAdapterError(
                "timeout_seconds must be finite and within "
                f"[{_MIN_TIMEOUT_SECONDS}, {_MAX_TIMEOUT_SECONDS}]"
            )

        self._transport = transport
        self._secret_resolver = secret_resolver
        self._api_key_reference = api_key_reference
        self._model = model
        self._timeout_seconds = float(timeout)

    @property
    def model(self) -> str:
        return self._model

    def _error(
        self,
        primitive: SemanticPrimitive,
        kind: SemanticEvidenceErrorKind,
        detail: str,
        *,
        elapsed_ms: float = 0.0,
    ) -> SemanticEvidence:
        latency = _finite_number(elapsed_ms)
        if latency is None or latency < 0.0:
            latency = 0.0
        return SemanticEvidence(
            provider=TYPESAFE_PROVIDER_NAME,
            model=self._model,
            primitive=primitive,
            error=SemanticProviderError(kind=kind, detail=_redact_detail(detail)),
            latency_ms=latency,
        )

    def _request_primitive(self, request: object) -> SemanticPrimitive:
        primitive = getattr(request, "primitive", None)
        return primitive if isinstance(primitive, SemanticPrimitive) else (
            SemanticPrimitive.CHOICE
        )

    def _resolve_credential(self) -> str:
        credential = self._secret_resolver.resolve(self._api_key_reference)
        if not isinstance(credential, str):
            raise _ResponseContractError("credential must be text")
        if not credential.strip() or len(credential) > _CREDENTIAL_MAX_LENGTH:
            raise _ResponseContractError("credential value is missing or invalid")
        if _CONTROL_RE.search(credential):
            raise _ResponseContractError("credential value contains invalid characters")
        return credential

    def _build_wire_request(
        self,
        request: SemanticDecisionRequest,
        question: Mapping[str, Any],
    ) -> str:
        payload = {
            "state": _json_safe(request.state),
            "model": self._model,
            "questions": {
                DEFAULT_TYPESAFE_QUESTION_ID: dict(question),
            },
        }
        return json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    def evaluate(self, request: SemanticDecisionRequest) -> SemanticEvidence:
        primitive = self._request_primitive(request)
        try:
            if not isinstance(request, SemanticDecisionRequest):
                return self._error(
                    primitive,
                    SemanticEvidenceErrorKind.SCHEMA,
                    "request must be a SemanticDecisionRequest",
                )

            try:
                question = _build_question(request)
            except _ResponseContractError as exc:
                return self._error(
                    primitive,
                    SemanticEvidenceErrorKind.SCHEMA,
                    str(exc),
                )

            try:
                credential = self._resolve_credential()
            except Exception as exc:
                if isinstance(exc, _ResponseContractError):
                    return self._error(
                        primitive,
                        SemanticEvidenceErrorKind.AUTH,
                        f"credential invalid: {exc}",
                    )
                return self._error(
                    primitive,
                    SemanticEvidenceErrorKind.AUTH,
                    f"credential resolution failed: {type(exc).__name__}",
                )

            body = self._build_wire_request(request, question)
            if len(body.encode("utf-8")) > TYPESAFE_MAX_REQUEST_BYTES:
                return self._error(
                    primitive,
                    SemanticEvidenceErrorKind.SCHEMA,
                    "serialized request exceeds the bounded request size",
                )

            wire_request = TypeSafeHTTPRequest(
                url=TYPESAFE_SYSTEMONE_URL,
                headers={
                    "Authorization": f"Bearer {credential}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body=body,
                timeout_seconds=self._timeout_seconds,
            )

            try:
                response = self._transport.post(wire_request)
            except Exception as exc:
                kind = classify_transport_exception(exc)
                if kind is SemanticEvidenceErrorKind.TIMEOUT:
                    detail = "transport timed out; outcome is ambiguous"
                elif kind is SemanticEvidenceErrorKind.TRANSPORT:
                    detail = f"transport failed: {type(exc).__name__}"
                else:
                    detail = f"transport raised {type(exc).__name__}"
                return self._error(primitive, kind, detail)

            elapsed = _finite_number(getattr(response, "elapsed_ms", None))
            if elapsed is None or elapsed < 0.0:
                return self._error(
                    primitive,
                    SemanticEvidenceErrorKind.SCHEMA,
                    "transport reported an invalid elapsed measurement",
                )
            if not isinstance(response.body, str) or len(response.body) > (
                TYPESAFE_MAX_RESPONSE_BYTES
            ):
                return self._error(
                    primitive,
                    SemanticEvidenceErrorKind.SCHEMA,
                    "response body exceeds the bounded response size",
                )
            status = response.status_code
            if isinstance(status, bool) or not isinstance(status, int):
                return self._error(
                    primitive,
                    SemanticEvidenceErrorKind.SCHEMA,
                    "transport reported an invalid status code",
                )
            if status != 200:
                kind = http_error_kind(status) or SemanticEvidenceErrorKind.UNKNOWN
                return self._error(
                    primitive,
                    kind,
                    f"{TYPESAFE_PROVIDER_NAME} systemone returned HTTP {status}",
                    elapsed_ms=elapsed,
                )

            try:
                return _validated_response_payload(response, request, self._model)
            except _ResponseContractError as exc:
                return self._error(
                    primitive, SemanticEvidenceErrorKind.SCHEMA, str(exc),
                    elapsed_ms=elapsed,
                )
        except Exception as exc:  # never raise across the provider boundary
            return self._error(
                primitive,
                SemanticEvidenceErrorKind.UNKNOWN,
                f"adapter failed closed: {type(exc).__name__}",
            )
