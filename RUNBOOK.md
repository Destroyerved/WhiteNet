# WhiteNet Demo Runbook

This runbook is designed for quick evaluator/judge demos on Windows PowerShell.

## 1) Setup

```powershell
python --version
python -m pip install -r requirements.txt
```

Expected:

- Python 3.x is available
- Dependencies install without errors

---

## 1b) Desktop GUI (same features as CLI)

From the project folder (so `registry.json` and CA keys resolve the same as the CLI):

```powershell
python gui.py
```

- Uses **tkinter** (included with Python on Windows; on Linux install `python3-tk` if `ModuleNotFoundError: tkinter`).
- Tabs cover **Identity**, **Verify**, **Send / DNS**, **Trust + Audit**, **Network + Report**, and **Demos**. Output appears in the bottom pane; long operations run in the background so the window stays responsive.
- The CLI remains the primary automation interface: `python cli.py …` and `python gui.py` share the same `cli.py` engine and JSON files.

---

## 1c) Web dashboard (Flask API + React)

**Requires:** Node.js (for building the UI) and Python packages from `requirements-web.txt`.

**One-time — build the React app:**

```powershell
cd web/client
npm install
npm run build
cd ../..
```

**Install server deps and run:**

```powershell
python -m pip install -r requirements-web.txt
python web/server.py
```

Open **http://127.0.0.1:5050** — five-tab animated trust console:

| Tab | Features |
|-----|----------|
| **Dashboard** | Live stats (8 metric cards), node cards with posture badges, revoke/renew per-node, recent audit tail |
| **Topology** | SVG force-directed graph — nodes colored by trust posture, VPN tunnels (solid green lines) and TLS sessions (dashed blue lines) as edges |
| **Actions** | Identity (issue, bind, quick onboard), verify/handshake/send, DNS resolve/assess, TLS 1.3 handshake, DNSSEC sign/verify, VPN tunnel, demos |
| **Governance** | Create proposals, cast votes (for/against), live proposal cards with status |
| **Audit** | Full scrollable event log with color-coded status badges |

**Auto-refresh:** Dashboard polls every 5 seconds with toast notifications for new events.

**Dev mode (hot reload UI):** terminal A: `python web/server.py` · terminal B: `cd web/client` then `npm run dev` — Vite proxies `/api` to port 5050; open **http://127.0.0.1:5173**.

---

## 2) Fresh Demo Data (Optional but recommended)

If you want a clean demo state, remove old generated files first:

```powershell
Remove-Item -ErrorAction SilentlyContinue registry.json,dns_records.json,cert.json,audit_log.json,revoked_nodes.json,proposals.json,tls_sessions.json,vpn_tunnels.json,dnssec_signed.json
```

---

## 3) Happy-Path Identity + Trust Flow

Issue and bind two identities:

```powershell
python cli.py issue --user "alice"
python cli.py bind --cert "cert.json"
python cli.py issue --user "bob"
python cli.py bind --cert "cert.json"
python cli.py list
```

Expected:

- `✔ Certificate issued → cert.json`
- `  Expires: <UTC timestamp 24h from now>`
- `✔ IPv6 Assigned → <ipv6>`
- `✔ DNS Record Added → <user>.whitenet.local → <ipv6>`
- `list` shows 2 bound nodes and 2 DNS records

---

## 4) Collect IPv6 Values for Next Commands

Read `registry.json` and copy the IPv6 of:

- `alice` as `<ALICE_IP>`
- `bob` as `<BOB_IP>`

Then run:

```powershell
python cli.py handshake --ipv6 "<ALICE_IP>"
python cli.py send --from "<ALICE_IP>" --to "<BOB_IP>"
python cli.py resolve --domain "alice.whitenet.local"
```

Expected:

- Handshake success with challenge nonce
- Secure packet allowed
- Domain resolves and trust verification passes

---

## 4b) Trust Audit Trail (Hash Chain + CA Signatures)

```powershell
python cli.py audit --limit 20
python cli.py audit --limit 50 --verify-chain
```

Expected:

- `✔ Total Events: N | Showing: ...` with event lines
- With `--verify-chain`: `✔ Audit chain verified (hash+signature valid)`

---

## 4c) Trust Posture Scorecard (`assess`)

Now includes **revocation status** and **certificate expiry** checks in addition to registry, certificate, DNS, audit chain, and recent signals.

```powershell
python cli.py assess --ipv6 "<NODE_IP>"
python cli.py assess --domain "alice.whitenet.local"
python cli.py assess --ipv6 "<NODE_IP>" --json
```

Expected:

- On a healthy bound node: `Verdict: TRUSTED | Score: 100/100` with 7 green check lines
- After revocation: `Verdict: BLOCKED` with `✖ revocation: CERTIFICATE REVOKED`

---

## 5) Certificate Lifecycle (v3.0)

### 5a) Revocation

```powershell
python cli.py revoke --ipv6 "<ALICE_IP>"
python cli.py assess --domain "alice.whitenet.local"
```

Expected: Assess shows `BLOCKED` with revocation check failed.

### 5b) Renewal

```powershell
python cli.py renew --user "alice"
python cli.py assess --domain "alice.whitenet.local"
```

Expected: New certificate issued with fresh expiry, previous revocation cleared, assess returns to `TRUSTED`.

---

## 6) Security Protocols (v3.0)

### 6a) TLS 1.3 Handshake

```powershell
python cli.py tls --client "<ALICE_IP>" --server "<BOB_IP>"
```

Expected:

- `✔ TLS 1.3 session established`
- Session ID, cipher suite (`TLS_AES_256_GCM_SHA384`)
- Session persisted to `tls_sessions.json`

### 6b) DNSSEC

```powershell
python cli.py dnssec-sign
python cli.py dnssec-verify --domain "alice.whitenet.local"
```

Expected:

- `✔ N DNS records signed (DNSSEC)`
- `✔ DNSSEC VERIFIED: alice.whitenet.local → <ipv6>`

### 6c) VPN Tunnel

```powershell
python cli.py vpn --node-a "<ALICE_IP>" --node-b "<BOB_IP>"
```

Expected:

- `✔ VPN Tunnel established`
- Tunnel ID, peers, encryption (`AES-256-GCM + HMAC-SHA384`)
- Tunnel persisted to `vpn_tunnels.json`
- Visible as green edge in web dashboard Topology tab

---

## 7) Governance (v3.0)

```powershell
python cli.py propose --title "Rotate CA keys quarterly" --proposer "alice"
python cli.py proposals
python cli.py vote --proposal "<PROPOSAL_ID>" --voter "bob"
python cli.py vote --proposal "<PROPOSAL_ID>" --voter "charlie"
python cli.py vote --proposal "<PROPOSAL_ID>" --voter "dave"
python cli.py proposals
```

Expected:

- Proposal created with unique ID
- Votes tallied; after 3 votes, proposal auto-resolves to `APPROVED` or `REJECTED`
- All governance events logged in audit trail

---

## 8) One-Command Full Demo

```powershell
python cli.py demo --fresh --quiet
```

- `--fresh` removes all data files (registry, DNS, cert, audit, revoked, proposals, TLS, VPN, DNSSEC)
- `--quiet` skips loading delays

---

## 9) Export & Operations

```powershell
python cli.py report -o trust_report.json
python cli.py status
python cli.py version
```

---

## 10) Web Dashboard Quick Tour

1. Start server: `python web/server.py`
2. Open **http://127.0.0.1:5050**
3. **Dashboard tab**: See all 8 stat cards, node posture cards
4. Click **Actions tab** → enter a user ID → click **⚡ Quick Onboard** (issues + binds in one step)
5. Use **source/destination IPv6** fields with **TLS 1.3 Handshake** and **VPN Tunnel** buttons
6. Click **DNSSEC Sign All** → then **DNSSEC Verify** to validate
7. **Topology tab**: See nodes as circles colored by posture, with VPN/TLS connections drawn
8. **Governance tab**: Create a proposal, cast votes
9. **Audit tab**: Full scrollable event log with status badges
10. Watch **toast notifications** appear as actions execute

---

## 11) Demo Talking Points

- WhiteNet enforces identity-first participation (certificate + IPv6 binding).
- Trust checks happen before communication (Zero Trust behavior).
- **Certificate lifecycle**: issuance with expiry, renewal, and revocation.
- **TLS 1.3**: cipher suite negotiation and session management between verified nodes.
- **DNSSEC**: CA-signed DNS records with independent verification.
- **VPN**: encrypted tunnel establishment with peer authentication.
- **Governance**: decentralised proposal and voting system with audit trail.
- Name resolution is tied to trusted identity records.
- Tampering/spoofing is detectible via signature verification.
- **`assess` is the judge-friendly differentiator**: 7-factor trust scorecard including revocation and expiry.
- **Network topology visualization**: live graph showing nodes and secure connections.
- Prototype runs as an overlay model on existing infrastructure.
- **Version 3.0.0** with full-stack web dashboard, CLI, and desktop GUI.

---

## 12) Automated tests (optional, for credibility)

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Expected: all tests pass (isolated temp directories; no changes to your repo's JSON files).
