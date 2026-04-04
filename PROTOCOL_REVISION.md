# WhiteNet Protocol Revision Notes

This document is updated using the current `Problemstatement.md` goals and live execution of the CLI in this repo.

## Problem Statement -> Implementation Status

Based on `Problemstatement.md`, WhiteNet should be identity-first, Zero Trust, IPv6-bound, and resistant to spoofing.

### Covered in current prototype (v3.0.0)

- **Certified identity issuance** via `issue` (certificate JSON signed by CA key, now with `valid_until` expiry and `issued_at` timestamps).
- **IPv6 identity binding** via `bind` (cert <-> generated IPv6 in `registry.json`).
- **Certificate expiry & renewal** via `renew` (re-issues with fresh validity window, preserves IPv6 binding, clears revocation if applicable).
- **Certificate revocation** via `revoke` (appends to `revoked_nodes.json`; revoked nodes are BLOCKED in `assess` and rejected by TLS/VPN).
- **Trust verification before communication** via `verify`, `handshake`, and `send`.
- **Spoof/tamper detection** via signature verification and `security-demo` / `spoof-test`.
- **Trust audit trail** (`audit_log.json`): append-only event log with `prev_hash` linkage, per-event SHA-256 `event_hash`, and RSA signature of each hash by the CA. Use `python cli.py audit --verify-chain` to validate integrity.
- **Trust posture scorecard** (`assess`): multi-factor verdict (TRUSTED / WARNING / BLOCKED) and 0–100 score combining: registry presence, certificate validity, **revocation status**, **certificate expiry**, `{user_id}.whitenet.local` DNS alignment, audit-chain health, and recent risk signals. Optional `--json` for tooling.
- **Automated demo** (`demo`): end-to-end happy path (alice/bob) with optional `--fresh` / `--regen-ca` / `--quiet`.
- **Trust report export** (`report`): JSON bundle with `WHITENET_VERSION` (**3.0.0**), CA public key SHA-256, per-node `assess` via `compute_assess_posture`, `audit_tail`, and audit summary.
- **Operations** (`status`, `version`): live counts, CA fingerprint, audit chain OK/FAIL; version string for CI/scripts.
- **Desktop GUI** (`gui.py`): tkinter front-end calling the same functions as `cli.py`.
- **Web dashboard** (`web/server.py` + `web/client`): Flask JSON API (`/api/*`) and a React (Vite) + Tailwind + Framer Motion SPA. Five-tab interface: **Dashboard** (live stats, node cards with posture badges, revoke/renew actions), **Topology** (SVG force-directed graph showing nodes colored by trust posture with VPN/TLS edge visualization), **Actions** (identity, verify, send, TLS, DNSSEC, VPN controls), **Governance** (proposal creation, voting), **Audit** (full event log with color-coded statuses). Auto-refresh (5s polling) with toast notifications.
- **Overlay-style software prototype** (runs on existing internet stack as CLI, no hardware dependency).

### Security protocol integrations (v3.0.0 — simulated)

- **TLS 1.3 Simulation** (`tls` command / `/api/tls-handshake`): Full handshake workflow with client/server random generation, pre-master secret derivation, master secret computation, cipher suite negotiation (`TLS_AES_256_GCM_SHA384`), and session persistence in `tls_sessions.json`. Only verified, non-revoked nodes can participate.
- **DNSSEC Simulation** (`dnssec-sign` / `dnssec-verify` commands / `/api/dnssec-sign` / `/api/dnssec-verify`): Signs all DNS records with the CA private key (RRSIG-style), persists to `dnssec_signed.json`, and provides independent verification of any signed record against the CA public key. Tampered records are detected.
- **VPN Tunnel Simulation** (`vpn` command / `/api/vpn-tunnel`): Establishes encrypted tunnels with shared key derivation (AES-256-GCM + HMAC-SHA384), peer authentication via registry + revocation checks, and session persistence in `vpn_tunnels.json`. Tunnels visible in the topology graph.

### Governance (v3.0.0 — functional)

- **Decentralised Governance** (`propose`, `vote`, `proposals` commands / `/api/governance/*`): Community-managed proposal system with title, proposer, category, and voting. Proposals auto-resolve after 3 votes (simple majority: approved/rejected). Full audit trail for all governance actions. Web dashboard provides a dedicated Governance tab for proposal creation and voting.

### Partially covered / next step items

- **Real TLS 1.3 integration** — current implementation simulates the cryptographic workflow; actual TLS socket wrapping would require OS-level network stack integration.
- **Real DNSSEC delegation chain** — current CA-signing is self-contained; real DNSSEC would chain to root DNS servers.
- **Real VPN tunnel encapsulation** — current simulation models key exchange and session state; actual packet encapsulation needs tun/tap interfaces.
- **Multi-authority governance** — current single-CA model could be extended to multi-CA with authority rotation.
- **Trust-based routing protocol** — represented by policy checks in CLI, not a full packet-forwarding router.

---

## Commands Run (Actual Session)

### 0) Environment and dependency check

```powershell
python --version
python -m pip install -r requirements.txt
```

Observed:

- Python available: `Python 3.11.9`
- `requirements.txt` contains only `cryptography` (stdlib modules removed).

### 1) End-to-end protocol demo

```powershell
python cli.py demo --fresh --quiet
```

This single command runs: issue/bind alice & bob, handshake, send, resolve, assess, audit verify.

### 2) New v3.0 commands

```powershell
# Revocation
python cli.py revoke --ipv6 "<NODE_IP>"

# Certificate renewal
python cli.py renew --user "alice"

# Governance
python cli.py propose --title "Rotate CA keys quarterly" --proposer "alice"
python cli.py vote --proposal "<PROPOSAL_ID>" --voter "bob"
python cli.py proposals

# TLS 1.3
python cli.py tls --client "<ALICE_IP>" --server "<BOB_IP>"

# DNSSEC
python cli.py dnssec-sign
python cli.py dnssec-verify --domain "alice.whitenet.local"

# VPN
python cli.py vpn --node-a "<ALICE_IP>" --node-b "<BOB_IP>"
```

---

## What This Demonstrates

- The core trust pipeline is functional: issue -> bind -> verify -> communicate.
- Identity is mandatory for trust decisions (Zero Trust behavior is enforced).
- Spoofing attempts are detectable by certificate/signature mismatch.
- DNS-like trusted name resolution connects identity to routing/lookup workflow.
- **Certificate lifecycle is managed**: issuance with expiry, renewal, and revocation.
- **Security protocols are simulated**: TLS 1.3 key exchange, DNSSEC record signing/verification, VPN encrypted tunnel establishment.
- **Governance is operational**: community proposals, voting, automatic resolution.
- Operations can be reviewed after the fact via the signed audit trail.
- **Network topology is visualized**: nodes colored by trust posture, VPN/TLS connections drawn as edges.
- Stakeholders get a **single explainable trust decision** (`assess`) with 7 checks instead of many low-level commands.

---

## What I Like In This Project

- Clear identity-first architecture aligned with the problem statement.
- Practical CLI command flow that is easy to demo and explain in a hackathon/review.
- Good security narrative: baseline trust, attack injection, and tamper detection evidence.
- **Full protocol stack simulation**: TLS 1.3, DNSSEC, and VPN show the vision of how WhiteNet would integrate with real network security.
- **Governance adds credibility**: shows the decentralised management model from the problem statement is not just theory.
- **Premium web dashboard**: animated, tabbed, auto-refreshing, with network topology visualization.
- Modular command structure makes it easy to extend toward real protocol integrations later.

---

## Recommended Next Revisions

1. Add real TLS socket wrapping for actual encrypted communication between demo processes.
2. Implement multi-CA governance with authority rotation ceremonies.
3. Add rate limiting / throttling to the governance voting system.
4. Implement certificate transparency log (append-only public record of all issued certificates).
5. Add network metrics dashboard (latency simulation, bandwidth allocation per tunnel).
