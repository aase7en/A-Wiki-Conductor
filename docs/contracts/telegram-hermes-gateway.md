# Contract — Telegram / Hermes Gateway for A-Conductor

Status: architecture contract; implementation deferred

## Goal

Make Telegram a first-class operator surface for A-Conductor while preserving the user's existing 24/7 Hermes Agent conversation on the Raspberry Pi 5.

## Preferred topology

```text
Telegram
   |
   v
Hermes Agent on Pi5
   |  conversational intent / A-Wiki knowledge
   |  bounded /a operator requests
   v
A-Conductor Operator API
   |
   v
Durable Job Control + Native Execution
```

Hermes remains the preferred Telegram gateway. A-Conductor does not need to become part of Hermes and Hermes does not become A-Conductor's durable execution authority.

## Why Hermes should own Telegram ingestion

The existing Hermes process already owns the user's Telegram conversation. Running a second process against the same Telegram bot token with competing long-poll `getUpdates` consumers is forbidden because updates may be consumed by the wrong process or appear missing.

Preferred integration order:

1. Hermes receives Telegram update.
2. Normal conversation remains Hermes-owned.
3. Explicit `/a ...` commands or an approved Hermes intent bridge are translated into `operator.v1` requests.
4. Hermes calls the A-Conductor gateway endpoint/client.
5. A-Conductor validates operator protocol + durable job authority and performs/declines the requested bounded action.
6. Hermes renders the bounded result back into Telegram.

## Telegram command UX target

Initial commands may map to protocol actions such as:

- `/a status`
- `/a job <job-id>`
- `/a events <job-id>`
- `/a ready <job-id> <version>`
- `/a claim <job-id> <version> <worker-id>`
- `/a gate <job-id> <version> <worker-id>`
- `/a exec <job-id> <version> <worker-id> <operation-ref>`

Human-friendly macros such as `/a run wastewater` are NOT protocol-v1 primitives. Hermes/A-Wiki may later interpret them into a work order and bounded lifecycle sequence, but that conversational planning layer stays outside the A-Conductor transport protocol.

## Telegram Mini App

A Telegram Mini App is an optional later UI, not a second execution plane. It should use the same operator API to display:

- A-Conductor online/offline
- active jobs
- job state/version/attempt budget
- A-Worker state/project assignment
- bounded checkpoint/evidence history
- explicitly authorized lifecycle buttons

The Mini App must not receive native executable paths, bot tokens, tunnel IDs, secret values, or raw subprocess output by default.

## Credential boundary

P1-039 and the protocol layer contain no Telegram token handling.

Future Telegram implementation requires explicit operator-supplied configuration for:

- bot/application identity if a separate A-Conductor bot is chosen
- Hermes integration endpoint/transport if Hermes forwards commands
- allowlisted Telegram user/chat identity
- network placement and authentication between Pi5 Hermes and A-Conductor host

These are external authorization/configuration steps and must not be auto-provisioned.

## Deployment options

### Preferred: Hermes bridge

Use existing Hermes bot/session as the single Telegram update consumer and forward bounded A-Conductor requests.

Advantages:
- one existing user conversation
- no competing poller
- conversational interpretation can reuse Hermes/A-Wiki
- fewer credentials and Telegram bots to manage

### Development fallback: separate A-Conductor bot

Useful for isolated testing before Hermes integration, but must use a distinct bot token/application. Do not reuse the active Hermes bot token with another long-poll process.

### Future: shared webhook/router

Possible after an explicit architecture decision, but unnecessary for the first working integration.

## Failure behavior

If A-Conductor is unreachable, Hermes should report a bounded unavailable state and must not pretend the job was submitted.

If a version conflict occurs, Hermes should show the current job/version and request/reconcile the next intended action instead of silently replaying the mutation.

If an execution action enters `RECOVERY_NEEDED`, Telegram should present the durable state and evidence refs; it must not automatically issue repeated execution requests.
