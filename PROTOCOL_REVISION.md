# WhiteNet Protocol Revision Notes

This file summarizes the protocol work completed in `cli.py`, including command syntax and expected outputs so you can quickly revise.

## What Was Implemented

The CLI now matches the protocol flow described in the project design.

- Added protocol commands:
  - `handshake`
  - `send`
  - `resolve`
  - `list`
  - `security-demo`
- Extended identity binding:
  - `bind` now also creates a DNS-like trusted record in `dns_records.json`
  - Format: `<user_id>.whitenet.local -> <ipv6>`
- Improved trust handling:
  - `verify_node()` now returns `True` or `False` (besides printing status)
  - `send` and `handshake` enforce Zero Trust checks using this result
- Windows output compatibility fix:
  - UTF-8 stdout reconfigure added to avoid Unicode banner crash

---

## Commands and Syntax

## 1) Issue Certificate

```bash
python cli.py issue --user <username>
```

Example:

```bash
python cli.py issue --user user1
```

Expected output (sample):

- Certificate issuance section appears
- `✔ Certificate issued -> cert.json`

---

## 2) Bind Identity to IPv6

```bash
python cli.py bind --cert cert.json
```

Expected output (sample):

- Identity binding section appears
- `✔ IPv6 Assigned -> <generated_ipv6>`
- `✔ DNS Record Added -> user1.whitenet.local -> <generated_ipv6>`

Generated/updated files:

- `registry.json`
- `dns_records.json`

---

## 3) Verify Node Identity

```bash
python cli.py verify --ipv6 <ipv6_address>
```

Expected output (sample):

- Verification engine section appears
- Trusted case: `✔ Trusted Node (Identity Verified)`
- Failure case: `🚨 Tampered or Fake Node Detected`

---

## 4) Handshake (TLS-like Simulation)

```bash
python cli.py handshake --ipv6 <ipv6_address>
```

Expected output (sample):

- Handshake layer section appears
- Internally verifies certificate first
- On success:
  - `Challenge nonce: <random_hex>`
  - `✔ Handshake success: secure context established`
- On failure:
  - `✖ Handshake failed: untrusted node`

---

## 5) Secure Send (Zero Trust Communication)

```bash
python cli.py send --from <source_ipv6> --to <destination_ipv6>
```

Example:

```bash
python cli.py send --from 2001:db8::1 --to 2001:db8::2
```

Expected output (sample):

- Secure transport layer section appears
- Verifies both source and destination identities
- On success:
  - `✔ Secure packet sent: <source_ipv6> -> <destination_ipv6>`
- On failure:
  - `✖ Communication blocked (Zero Trust policy)`
- Validation:
  - `✖ Source and destination cannot be the same` if both are identical

---

  ## 6) Resolve Domain (DNSSEC-like)

  ```bash
  python cli.py resolve --domain <domain_name>
  ```

  Example:

  ```bash
  python cli.py resolve --domain user1.whitenet.local
  ```

  Expected output (sample):

  - DNSSEC-like resolution section appears
  - If found:
    - `✔ user1.whitenet.local -> <ipv6>`
    - Then runs trust verification for that IPv6
  - If not found:
    - `✖ Domain not found in trusted records`

  ---

## 7) Spoof Attack Test

```bash
python cli.py spoof-test
```

Expected output (sample):

- Attack simulation section appears
- Mutates first node identity to attacker value
- Verification should fail with tampering/fake node message

---

## 8) List Current State

```bash
-
```

Expected output (sample):

- Network state section appears
- Shows number of bound nodes from `registry.json`
- Lists each node in format:
  - `<index>. <user_id> | <ipv6> | cert_id=<cert_id>`
- Shows number of DNS records from `dns_records.json`
- Lists each DNS mapping:
  - `<index>. <domain> -> <ipv6>`
- Empty-state handling:
  - `✖ No bound identities found in registry.json`
  - `⚠ No DNS records found in dns_records.json`

---

## 9) Security Demo (End-to-End Attack Resilience)

```bash
python cli.py security-demo
```

Expected output (sample):

- Security resilience demo section appears
- Step 1: baseline verification
- Step 2: spoof injection
- Step 3: re-verification shows tamper detection

---

## Quick Revision Flow

Use this sequence for demo/revision:

```bash
python cli.py issue --user user1
python cli.py bind --cert cert.json

python cli.py issue --user user2
python cli.py bind --cert cert.json

# Use values from registry.json
python cli.py handshake --ipv6 <ip1>
python cli.py send --from <ip1> --to <ip2>
python cli.py resolve --domain user1.whitenet.local
python cli.py security-demo
```

---

## Output Style Notes

- Colored console output is used (`GREEN`, `RED`, `YELLOW`, `CYAN`).
- Banner and status lines include Unicode symbols.
- Windows console compatibility was improved via UTF-8 stdout configuration.

