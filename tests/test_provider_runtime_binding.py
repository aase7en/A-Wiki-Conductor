"""WO-P1-158 Phase B — provider runtime binding (schema 1.1.0) proofs.

Typed per-model runtime bindings travel inside the existing models_json of a
provider profile (no DB DDL): schema 1.0.0 decodes with empty bindings, schema
1.1.0 carries at most one typed binding per model, binding changes bump the
provider generation through the canonical save path, and the sanitized
selection digest excludes every secret-shaped field by construction.
"""

from __future__ import annotations

import hashlib

import pytest

from a_conductor.provider_config_store import SQLiteProviderConfigStore
from a_conductor.provider_configuration import (
    ActorCapabilityEvidence,
    EgressBoundary,
    HarnessRuntimeBinding,
    HarnessStrategy,
    ProviderConfiguration,
    ProviderModelConfiguration,
    ProviderTrustClass,
    ProtocolFamily,
    runtime_selection_sha256,
)


def _model(model_id="glm-5.3-max", binding=None):
    return ProviderModelConfiguration(
        model_id=model_id,
        display_name=f"Model {model_id}",
        actor_capabilities=(ActorCapabilityEvidence("code", "DECLARED", "wo158"),),
        runtime_binding=binding,
    )


def _binding(strategy=HarnessStrategy.ZCODE_APP_SERVER):
    return HarnessRuntimeBinding(
        harness_strategy=strategy,
        runtime_provider_ref="zcode-runtime/glm-main",
        runtime_model_ref="zcode-runtime/glm-5.3",
    )


def _profile(models, schema="1.0.0"):
    return ProviderConfiguration(
        provider_id="zcode-glm",
        display_name="ZCode GLM",
        provider_type="zcode-app-server",
        protocol_family=ProtocolFamily.CUSTOM,
        endpoint_ref="zcode-desktop",
        credential_ref="secret-ref:zcode-credential",
        trust_class=ProviderTrustClass.FIRST_PARTY,
        egress_boundary=EgressBoundary.LOCAL_MACHINE,
        harness_strategies=(HarnessStrategy.ZCODE_APP_SERVER,),
        max_concurrency=1,
        models=models,
        enabled=True,
        schema_version=schema,
    )


# ---------------- 1) schema 1.0 legacy decode ----------------

def test_schema_1_0_profile_without_bindings_decodes(tmp_path):
    store = SQLiteProviderConfigStore(tmp_path / "providers.sqlite")
    generation = store.save_provider(_profile((_model(),)))
    assert generation == 1
    snapshot = store.load_provider_snapshot("zcode-glm")
    assert snapshot is not None
    loaded = snapshot.profile
    assert loaded.schema_version == "1.0.0"
    assert all(model.runtime_binding is None for model in loaded.models)
    assert loaded.as_dict()["models"][0]["runtime_binding"] is None


# ---------------- 2) schema 1.1 round trip ----------------

def test_schema_1_1_binding_round_trip(tmp_path):
    store = SQLiteProviderConfigStore(tmp_path / "providers.sqlite")
    store.save_provider(_profile((_model(binding=_binding()),), schema="1.1.0"))
    snapshot = store.load_provider_snapshot("zcode-glm")
    assert snapshot is not None
    loaded = snapshot.profile
    assert loaded.schema_version == "1.1.0"
    binding = loaded.models[0].runtime_binding
    assert isinstance(binding, HarnessRuntimeBinding)
    assert binding.harness_strategy is HarnessStrategy.ZCODE_APP_SERVER
    assert binding.runtime_provider_ref == "zcode-runtime/glm-main"
    assert binding.runtime_model_ref == "zcode-runtime/glm-5.3"
    assert loaded.as_dict()["models"][0]["runtime_binding"] == binding.as_dict()


# ---------------- 3) 1.0 + binding rejects ----------------

def test_schema_1_0_with_binding_rejects():
    with pytest.raises(ValueError, match="runtime bindings require schema_version 1.1.0"):
        _profile((_model(binding=_binding()),), schema="1.0.0")


# ---------------- 4) malformed bindings reject ----------------

@pytest.mark.parametrize(
    "kwargs",
    [
        {"harness_strategy": "NOT_A_STRATEGY"},
        {"harness_strategy": HarnessStrategy.LOCAL_CLI, "runtime_provider_ref": "X"*200},
        {"harness_strategy": HarnessStrategy.LOCAL_CLI, "runtime_model_ref": "bad ref!"},
        {"harness_strategy": HarnessStrategy.LOCAL_CLI, "runtime_provider_ref": ""},
        {"harness_strategy": HarnessStrategy.LOCAL_CLI, "runtime_model_ref": "-leading-dash"},
    ],
)
def test_malformed_binding_rejects(kwargs):
    base = {
        "harness_strategy": HarnessStrategy.LOCAL_CLI,
        "runtime_provider_ref": "prov/ref",
        "runtime_model_ref": "model/ref",
    }
    base.update(kwargs)
    with pytest.raises(ValueError):
        HarnessRuntimeBinding(**base)


def test_binding_from_dict_rejects_extra_and_missing_keys():
    with pytest.raises(ValueError):
        HarnessRuntimeBinding.from_dict(
            {"harness_strategy": "LOCAL_CLI", "runtime_provider_ref": "a/b",
             "runtime_model_ref": "m/b", "extra": "x"}
        )
    with pytest.raises(ValueError):
        HarnessRuntimeBinding.from_dict({"harness_strategy": "LOCAL_CLI"})
    with pytest.raises(ValueError):
        HarnessRuntimeBinding.from_dict("not-a-mapping")


def test_unknown_schema_version_rejects():
    with pytest.raises(ValueError, match="schema_version is unsupported"):
        _profile((_model(),), schema="1.2.0")


# ---------------- 5) binding change bumps generation ----------------

def test_binding_change_bumps_generation_via_canonical_save(tmp_path):
    store = SQLiteProviderConfigStore(tmp_path / "providers.sqlite")
    gen1 = store.save_provider(_profile((_model(),), schema="1.0.0"))
    assert gen1 == 1
    upgraded = _profile((_model(binding=_binding()),), schema="1.1.0")
    gen2 = store.save_provider(upgraded, expected_generation=gen1)
    assert gen2 == 2
    changed = HarnessRuntimeBinding(
        harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
        runtime_provider_ref="zcode-runtime/glm-main",
        runtime_model_ref="zcode-runtime/glm-5.3-different",
    )
    gen3 = store.save_provider(
        _profile((_model(binding=changed),), schema="1.1.0"), expected_generation=gen2
    )
    assert gen3 == 3


# ---------------- 6) stale requirement rejects ----------------

def test_stale_expected_generation_rejects(tmp_path):
    store = SQLiteProviderConfigStore(tmp_path / "providers.sqlite")
    store.save_provider(_profile((_model(binding=_binding()),), schema="1.1.0"))
    from a_conductor.provider_config_store import ProviderConfigStoreError
    with pytest.raises(ProviderConfigStoreError):
        store.save_provider(_profile((_model(binding=_binding()),), schema="1.1.0"),
                            expected_generation=99)


# ---------------- 7) selection digest semantics ----------------

def test_selection_digest_stable_and_field_sensitive():
    binding = _binding()
    a = runtime_selection_sha256(
        runtime_binding=binding, runtime_base_url="http://127.0.0.1:1"
    )
    b = runtime_selection_sha256(
        runtime_binding=binding, runtime_base_url="http://127.0.0.1:1"
    )
    assert a == b  # deterministic
    assert len(a) == 64
    other_url = runtime_selection_sha256(
        runtime_binding=binding, runtime_base_url="http://127.0.0.2:1"
    )
    assert other_url != a  # base URL participates
    other_model = runtime_selection_sha256(
        runtime_binding=HarnessRuntimeBinding(
            harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
            runtime_provider_ref="zcode-runtime/glm-main",
            runtime_model_ref="zcode-runtime/other",
        ),
        runtime_base_url="http://127.0.0.1:1",
    )
    assert other_model != a  # model ref participates
    enabled = runtime_selection_sha256(
        runtime_binding=binding, runtime_base_url="http://127.0.0.1:1",
        runtime_source_enabled=True,
    )
    assert enabled != a  # enabled/source state participates when declared


def test_selection_digest_excludes_secret_shapes():
    binding = _binding()
    secret = "sk-ant-supersecretvalue123456"
    digest = runtime_selection_sha256(
        runtime_binding=binding, runtime_base_url="http://127.0.0.1:1"
    )
    manual = hashlib.sha256(
        "\x1f".join(
            (
                "ZCODE_APP_SERVER",
                binding.runtime_provider_ref,
                binding.runtime_model_ref,
                "http://127.0.0.1:1",
                "",
            )
        ).encode("utf-8")
    ).hexdigest()
    assert digest == manual  # canonical composition is exactly the public fields
    assert secret not in digest


# ---------------- 8) binding does not match by display name ----------------

def test_display_name_is_not_binding_authority(tmp_path):
    store = SQLiteProviderConfigStore(tmp_path / "providers.sqlite")
    binding = _binding()
    profile = _profile(
        (_model(model_id="display-name-decoy", binding=binding),), schema="1.1.0"
    )
    store.save_provider(profile)
    snapshot = store.load_provider_snapshot("zcode-glm")
    assert snapshot is not None
    loaded = snapshot.profile
    model = loaded.models[0]
    # display name differs from refs and is never consulted for binding truth
    assert model.display_name != model.runtime_binding.runtime_model_ref
    assert model.runtime_binding.runtime_model_ref == "zcode-runtime/glm-5.3"


# ---------------- 9) corrupt models_json stays fail-closed ----------------

def test_corrupt_models_json_still_fails_closed(tmp_path):
    import sqlite3
    path = tmp_path / "providers.sqlite"
    store = SQLiteProviderConfigStore(path)
    store.save_provider(_profile((_model(binding=_binding()),), schema="1.1.0"))
    con = sqlite3.connect(path)
    con.execute("UPDATE provider_configurations SET models_json='not-json'")
    con.commit()
    con.close()
    from a_conductor.provider_config_store import ProviderConfigStoreError
    with pytest.raises(ProviderConfigStoreError):
        store.load_provider_snapshot("zcode-glm")
