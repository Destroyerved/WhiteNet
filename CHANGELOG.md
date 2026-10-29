# Changelog

All notable changes to the **WhiteNet** project are documented in this file.

## [3.1.0] - 2026-10-30

### Added
- **Trust-Based Multi-Hop Routing (`route` / `POST /api/route`)**:
  - Hop-by-hop Zero Trust verification (CA signature, revocation, expiry, and posture check at every intermediate node).
  - Chained SHA-256 cryptographic route proof across source, intermediate relay hops, and destination.
- **4-Vector Security Attack Simulation Suite (`attack-sim` / `POST /api/attack-sim`)**:
  - Live simulations and automatic state restoration for **IP Spoofing**, **Man-in-the-Middle (MITM)**, **Sybil Identity Flood**, and **Certificate Forgery**.
- **Interactive Attack Defense Matrix (`/attack-matrix`)**:
  - Integrated `WhiteNet_Attack_Defense_Matrix.html` into the Flask web server with unified navigation and a `▶ Execute Live Attack on Server` button connected to `/api/attack-sim`.
- **Interactive Sector Use Case Simulators (`/use-cases`)**:
  - Wired E-Governance (`POST /api/egov-demo`), Healthcare (`POST /api/health-demo`), and Corporate Intranet (`POST /api/corporate-demo`) demos to real backend execution.
- **12-Phase Full Network Showcase (`showcase` / `POST /api/showcase`)**:
  - One-click showcase execution in the React Trust Console, Desktop GUI, and CLI.
- **Expanded Automated Test Suite (`tests/test_cli.py`, `tests/test_server.py`)**:
  - 14 automated `pytest` tests covering identity lifecycle, revocation, expiry, TLS 1.3, DNSSEC poison detection, VPN tunnels, multi-hop routing, governance quorum, 4-vector attack simulations, and all Flask REST endpoints.

### Changed
- **Strict Zero-Trust Revocation & Expiry Enforcement**:
  - `verify_node()`, `tls_handshake()`, `vpn_establish_tunnel()`, and `route_packet()` now consistently reject both revoked and expired certificates.
  - `dnssec_verify()` now compares live `dns_records.json` mappings against signed `dnssec_signed.json` records to detect DNS cache/record poisoning.
  - `renew_certificate()` and `security-demo` restoration clear historical blocked audit flags for the renewed/restored IPv6 identity so `assess` returns to `TRUSTED (100/100)`.
- **Optional Firebase Cloud Sync**:
  - Firebase Firestore synchronization in `cli.py` is now lazy and opt-in (`WHITENET_FIREBASE_SYNC=1` with `serviceAccountKey.json`), preventing errors in local, offline, or CI environments.
- **Pre-built React Production Bundle**:
  - Tracked `web/client/dist` in git for zero-config Python deployments on Render (`render.yaml`).

---

## [3.0.0] - 2026-04-06

### Added
- **Certificate Lifecycle**: Certificate expiration (`valid_until`), `revoke`, and `renew` commands.
- **Security Protocol Stack**: Simulated **TLS 1.3** (`tls`), **DNSSEC** (`dnssec-sign`, `dnssec-verify`), and **VPN Tunnels** (`vpn`).
- **Decentralised Governance**: Community proposals (`propose`, `proposals`) and voting (`vote`) with automatic quorum resolution.
- **Full-Stack Web Console**: Flask API (`web/server.py`) + React/Vite/Tailwind/Framer Motion SPA (`web/client`) with interactive SVG topology graph.

---

## [2.1.0] - 2026-03-25

### Added
- **7-Factor Trust Posture Scorecard (`assess`)**: Unified `TRUSTED` / `WARNING` / `BLOCKED` verdict and 0–100 score.
- **Tamper-Evident Audit Trail (`audit`)**: SHA-256 hash-chained and RSA-PSS CA-signed event log (`audit_log.json`).
- **Desktop GUI (`gui.py`)**: Tkinter desktop interface sharing the `cli.py` engine.

---

## [1.0.0] - 2026-03-15

### Added
- Initial PKI certificate issuance (`issue`), deterministic IPv6 binding (`bind`), Zero Trust verification (`verify`, `handshake`, `send`), and `.whitenet.local` DNS resolution (`resolve`).
