# Kilo hook adapter fixtures (fake, bounded)

All files under this directory are FAKE, bounded, native-shaped test data
for `tests/test_kilo_hook_adapter_contract.py` (WO-P1-376; authored under
the WO-P1-262 alias before the identity rebind — fixture provenance is
unchanged). They encode
the fixture grammar declared in `docs/contracts/kilo-hook-adapter-v1.md`
§3: observed stream families (top-level `type`/`timestamp`/`sessionID` +
`part`; `step_start`; `tool_use` with name + `state.status/input/output`;
`text` parts) plus ASSUMED details that are explicitly NOT proven native
behavior (status vocabulary, timestamp offsets). Any secret-looking
string comes exclusively from the shared `fake-secret-corpus/1`
(Hook Contract §11) or matches the dispatch harness's redaction patterns;
no real credentials, tokens, or share URLs exist here.

- `capability.json` — adapter capability discovery document.
- `native/session-basic/` — mappable stream plus one unknown-type record.
- `native/session-redaction/` — corpus-bearing stream proving digest-only
  redaction.
- `native/provider-mismatch/`, `native/version-drift/`,
  `native/version-unverified/` — fail-closed mismatch streams.
- `native/invalid-records/` — malformed/unknown-status records plus one
  offset-timestamp record that must convert to UTC.
- `normalized/expected-*.json` — exact expected normalized envelopes,
  deterministically derived from the reference mapper in the test module.
