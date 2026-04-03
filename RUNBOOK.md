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

## 2) Fresh Demo Data (Optional but recommended)

If you want a clean demo state, remove old generated files first:

```powershell
Remove-Item -ErrorAction SilentlyContinue registry.json,dns_records.json,cert.json
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
python cli.py security-demo
```

---

## 7) Demo Talking Points

- WhiteNet enforces identity-first participation (certificate + IPv6 binding).
- Trust checks happen before communication (Zero Trust behavior).
- Name resolution is tied to trusted identity records.
- Tampering/spoofing is detectible via signature verification.
- Prototype runs as an overlay model on existing infrastructure.
