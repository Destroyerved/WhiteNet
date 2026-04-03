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

Open **http://127.0.0.1:5050** — animated trust console with live registry/assess cards, audit tail, and actions (issue, bind, verify, send, assess, demos). The API is the same data as `cli.py` (`/api/meta`, `/api/report`, etc.).

**Dev mode (hot reload UI):** terminal A: `python web/server.py` · terminal B: `cd web/client` then `npm run dev` — Vite proxies `/api` to port 5050; open **http://127.0.0.1:5173**.

---

## 2) Fresh Demo Data (Optional but recommended)

If you want a clean demo state, remove old generated files first:

```powershell
Remove-Item -ErrorAction SilentlyContinue registry.json,dns_records.json,cert.json,audit_log.json
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

- `✔ Certificate issued -> cert.json`
- `✔ IPv6 Assigned -> <ipv6>`
- `✔ DNS Record Added -> <user>.whitenet.local -> <ipv6>`
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

Security-relevant actions append events to `audit_log.json`. Each event links to the previous hash (`prev_hash`), carries a SHA-256 `event_hash`, and is signed with the CA private key so tampering is detectable.

View recent events and verify the full chain:

```powershell
python cli.py audit --limit 20
python cli.py audit --limit 50 --verify-chain
```

Expected:

- `✔ Total Events: N | Showing: ...` with lines for `issue_certificate`, `verify_node`, `handshake`, `send_secure`, `resolve_domain`, etc.
- With `--verify-chain`: `✔ Audit chain verified (hash+signature valid)` on an intact log; otherwise a failure at a specific event index.

---

## 4c) Trust Posture Scorecard (Differentiator: `assess`)

One command summarizes **verdict** (TRUSTED / WARNING / BLOCKED), a **0–100 score**, and checks for: registry presence, CA signature, DNS name alignment with `{user_id}.whitenet.local`, audit-chain integrity, and recent blocked/tamper signals for that node.

```powershell
python cli.py assess --ipv6 "<NODE_IP>"
python cli.py assess --domain "alice.whitenet.local"
python cli.py assess --ipv6 "<NODE_IP>" --json
```

Expected:

- On a healthy bound node with matching DNS and a valid audit chain: `Verdict: TRUSTED | Score: 100/100` with green check lines.
- After tamper demos or DNS mismatch: `WARNING` or `BLOCKED` with specific failing checks.

---

## 4d) “+5” Tier: Automated Demo, Export Bundle, Operations

**One-command full demo** (issue/bind alice & bob, handshake, send, resolve, assess, audit verify). For a clean slate first:

```powershell
python cli.py demo --fresh --quiet
```

- `--fresh` removes `registry.json`, `dns_records.json`, `cert.json`, `audit_log.json` (your CA keys stay unless you add `--regen-ca`).
- `--quiet` skips loading-dot delays (faster for stage demos).

**Judge-ready export** — single JSON file with version, CA public-key fingerprint, every node’s computed `assess`, audit tail, and chain summary:

```powershell
python cli.py report -o trust_report.json
python cli.py report -o - | Out-File -Encoding utf8 report.json   # stdout: no banner, JSON only
```

**Operations snapshot** — counts, CA SHA-256, audit chain status:

```powershell
python cli.py status
python cli.py version
```

---

## 5) Attack/Tamper Demonstration

Run:

```powershell
python cli.py security-demo
```

Expected:

- Baseline verification succeeds
- Spoof/tamper step is injected
- Re-verification fails with tamper/fake detection message

---

## 6) One-Line Demo Sequence (Quick Copy/Paste)

```powershell
python -m pip install -r requirements.txt; `
python cli.py issue --user "alice"; `
python cli.py bind --cert "cert.json"; `
python cli.py issue --user "bob"; `
python cli.py bind --cert "cert.json"; `
python cli.py list; `
python cli.py resolve --domain "alice.whitenet.local"; `
python cli.py security-demo; `
python cli.py audit --limit 30 --verify-chain; `
python cli.py assess --domain "alice.whitenet.local"
```

---

## 7) Demo Talking Points

- WhiteNet enforces identity-first participation (certificate + IPv6 binding).
- Trust checks happen before communication (Zero Trust behavior).
- Name resolution is tied to trusted identity records.
- Tampering/spoofing is detectible via signature verification.
- The audit trail provides governance-style traceability: append-only hash chain plus per-event CA signatures (`audit` command).
- **`assess` is the judge-friendly differentiator**: one screen explains trust posture across crypto, naming, and operations—not just a single pass/fail check.
- Prototype runs as an overlay model on existing infrastructure.
- **`demo` + `report` + `status`** turn the prototype into something you can hand to judges as a reproducible bundle (version **2.0.0**).

---

## 8) Automated tests (optional, for credibility)

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Expected: all tests pass (isolated temp directories; no changes to your repo’s JSON files).
