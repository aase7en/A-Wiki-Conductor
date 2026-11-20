# WO-P1-699 — SF-WEB-7: Authenticated remote operator mode

Issue: #699
Status: SECURITY ANALYSIS (offline-safe first slice)
Risk: R3 (network security, authentication boundary extension)
Topology: CONTROL_PLANE_ONLY

## Security Analysis: Remote Access Options

### Current State
- Web API binds to 127.0.0.1 only (loopback)
- Bearer token per-boot + Host/Origin exact match
- No TLS (loopback doesn't need it)
- Rate limiting + connection bounding

### Option A: Tailscale (RECOMMENDED for personal use)
- Run Tailscale on the host machine
- Web API binds to Tailscale IP (100.x.x.x) in addition to loopback
- Authentication handled by Tailscale's WireGuard mesh
- Pros: zero config on the app side, encrypted by default, ACL via Tailscale
- Cons: requires Tailscale account/app on both devices
- Implementation: add `--host` flag to bind to additional interface
- Human decision: NONE (Tailscale is already installed on the network)

### Option B: mTLS reverse proxy
- Caddy/nginx reverse proxy with client certificate authentication
- Web API stays loopback-only; proxy forwards from public interface
- Pros: standard TLS, fine-grained client auth, no mesh dependency
- Cons: certificate management, proxy configuration
- Implementation: proxy config templates only
- Human decision: Certificate authority setup (human-gated)

### Option C: SSH tunnel
- User SSH-tunnels to the host, Web API stays loopback
- Pros: zero app changes, uses existing SSH auth
- Cons: requires manual tunnel setup per session
- Implementation: none (documentation only)
- Human decision: NONE

## Recommended First Slice (this document)
Document all three options + provide config templates for Option A (Tailscale).
The actual network binding extension (`--host` flag) is a bounded code change.
TLS termination and certificate management are deferred to the human gate.

## What Can Be Done Now (offline-safe)
1. This analysis document
2. `--host` flag addition to `a-conductor-web web` CLI (allow binding to non-loopback)
3. Documentation for SSH tunnel setup
4. Tailscale integration guide

## What Requires Human Decision
- Enabling network exposure (which option to use)
- TLS certificate strategy (for Option B)
- Whether to expose mutations remotely or read-only only
