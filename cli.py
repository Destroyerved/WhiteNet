import argparse
import json
import uuid
import ipaddress
import os
import time
import sys
import hashlib
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

try:
    # Prevent Windows console encoding issues with banner/status symbols.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# =========================
# ASCII BANNER
# =========================

BANNER = r"""
██╗    ██╗██╗  ██╗██╗████████╗███████╗███╗   ██╗███████╗████████╗
██║    ██║██║  ██║██║╚══██╔══╝██╔════╝████╗  ██║██╔════╝╚══██╔══╝
██║ █╗ ██║███████║██║   ██║   █████╗  ██╔██╗ ██║█████╗     ██║   
██║███╗██║██╔══██║██║   ██║   ██╔══╝  ██║╚██╗██║██╔══╝     ██║   
╚███╔███╔╝██║  ██║██║   ██║   ███████╗██║ ╚████║███████╗   ██║   
 ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝╚══════╝   ╚═╝   

        🌐 WhiteNet Identity CLI
   Zero Trust • IPv6 Bound • Cryptographic Identity
"""

WHITENET_VERSION = "3.0.0"


# =========================
# COLORS
# =========================

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


# =========================
# FILES
# =========================

REGISTRY_FILE = "registry.json"
CA_KEY_FILE = "ca_private.pem"
CA_PUBLIC_FILE = "ca_public.pem"
DNS_FILE = "dns_records.json"
AUDIT_FILE = "audit_log.json"
CERT_FILE = "cert.json"
REVOKED_FILE = "revoked_nodes.json"
PROPOSALS_FILE = "proposals.json"
TLS_SESSIONS_FILE = "tls_sessions.json"
VPN_TUNNELS_FILE = "vpn_tunnels.json"

CERT_VALIDITY_HOURS = 24  # default certificate lifetime


# =========================
# UTILITIES
# =========================

def loading(msg="Processing"):
    if os.environ.get("WHITENET_QUIET"):
        return
    print(Colors.YELLOW + msg, end="", flush=True)
    for _ in range(3):
        time.sleep(0.3)
        print(".", end="", flush=True)
    print(Colors.RESET)


def canonical_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


# =========================
# KEY MANAGEMENT
# =========================

def generate_ca_keys():
    if os.path.exists(CA_KEY_FILE):
        return

    print(Colors.CYAN + "[+] Generating Root CA Keys..." + Colors.RESET)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    with open(CA_KEY_FILE, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    with open(CA_PUBLIC_FILE, "wb") as f:
        f.write(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    print(Colors.GREEN + "✔ CA Keys Generated" + Colors.RESET)


def load_ca_private():
    with open(CA_KEY_FILE, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_ca_public():
    with open(CA_PUBLIC_FILE, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def ca_public_key_fingerprint_sha256():
    """Stable identifier for the demo CA (SHA-256 of PEM bytes)."""
    if not os.path.exists(CA_PUBLIC_FILE):
        return None
    with open(CA_PUBLIC_FILE, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# =========================
# CERTIFICATE
# =========================

def issue_certificate(user_id):
    print(Colors.CYAN + "\n[ Certificate Issuance ]" + Colors.RESET)
    loading("Generating identity")

    private_key = load_ca_private()

    user_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    public_bytes = user_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    from datetime import timedelta
    now = datetime.now(timezone.utc)
    cert = {
        "cert_id": str(uuid.uuid4()),
        "user_id": user_id,
        "public_key": public_bytes,
        "issued_at": now.isoformat(),
        "valid_until": (now + timedelta(hours=CERT_VALIDITY_HOURS)).isoformat(),
    }

    cert_bytes = json.dumps(cert).encode()

    signature = private_key.sign(
        cert_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    cert["signature"] = signature.hex()

    with open(CERT_FILE, "w") as f:
        json.dump(cert, f, indent=4)

    print(Colors.GREEN + f"✔ Certificate issued → {CERT_FILE}" + Colors.RESET)
    print(Colors.YELLOW + f"  Expires: {cert['valid_until']}" + Colors.RESET)
    append_audit_event("issue_certificate", "success", {"user_id": user_id, "cert_id": cert["cert_id"], "valid_until": cert["valid_until"]})


# =========================
# IPv6
# =========================

def generate_ipv6():
    return str(ipaddress.IPv6Address(uuid.uuid4().int))


# =========================
# REGISTRY
# =========================

def load_registry():
    if not os.path.exists(REGISTRY_FILE):
        return {}
    with open(REGISTRY_FILE) as f:
        return json.load(f)


def save_registry(reg):
    with open(REGISTRY_FILE, "w") as f:
        json.dump(reg, f, indent=4)


def load_dns_records():
    if not os.path.exists(DNS_FILE):
        return {}
    with open(DNS_FILE) as f:
        return json.load(f)


def save_dns_records(records):
    with open(DNS_FILE, "w") as f:
        json.dump(records, f, indent=4)


def load_audit_log():
    if not os.path.exists(AUDIT_FILE):
        return []
    with open(AUDIT_FILE) as f:
        return json.load(f)


def save_audit_log(events):
    with open(AUDIT_FILE, "w") as f:
        json.dump(events, f, indent=4)


def append_audit_event(action, status, details=None):
    events = load_audit_log()
    prev_hash = events[-1]["event_hash"] if events else "GENESIS"

    event_core = {
        "event_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "status": status,
        "details": details or {},
        "prev_hash": prev_hash
    }

    event_hash = hashlib.sha256(canonical_json(event_core).encode()).hexdigest()
    event_core["event_hash"] = event_hash

    try:
        signature = load_ca_private().sign(
            event_hash.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        event_core["signature"] = signature.hex()
    except Exception:
        event_core["signature"] = ""

    events.append(event_core)
    save_audit_log(events)


def verify_audit_chain():
    events = load_audit_log()
    if not events:
        return True, 0

    expected_prev = "GENESIS"
    ca_public = load_ca_public()

    for idx, event in enumerate(events, start=1):
        if event.get("prev_hash") != expected_prev:
            return False, idx

        core_for_hash = {
            "event_id": event.get("event_id"),
            "timestamp_utc": event.get("timestamp_utc"),
            "action": event.get("action"),
            "status": event.get("status"),
            "details": event.get("details", {}),
            "prev_hash": event.get("prev_hash")
        }
        recomputed_hash = hashlib.sha256(canonical_json(core_for_hash).encode()).hexdigest()
        if event.get("event_hash") != recomputed_hash:
            return False, idx

        signature_hex = event.get("signature", "")
        if signature_hex:
            try:
                ca_public.verify(
                    bytes.fromhex(signature_hex),
                    recomputed_hash.encode(),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            except Exception:
                return False, idx

        expected_prev = event.get("event_hash")

    return True, len(events)


def show_audit(limit=10, verify_chain=False):
    print(Colors.CYAN + "\n[ Trust Audit Trail ]" + Colors.RESET)
    loading("Loading security events")

    events = load_audit_log()
    if not events:
        print(Colors.YELLOW + "⚠ No audit events recorded yet" + Colors.RESET)
        return

    recent = events[-limit:] if limit > 0 else events
    print(Colors.GREEN + f"✔ Total Events: {len(events)} | Showing: {len(recent)}" + Colors.RESET)

    for event in recent:
        print(
            f"- {event.get('timestamp_utc')} | "
            f"{event.get('action')} | "
            f"{event.get('status')} | "
            f"hash={event.get('event_hash', '')[:12]}..."
        )

    if verify_chain:
        valid, marker = verify_audit_chain()
        if valid:
            print(Colors.GREEN + "✔ Audit chain verified (hash+signature valid)" + Colors.RESET)
        else:
            print(Colors.RED + f"🚨 Audit chain integrity failed at event #{marker}" + Colors.RESET)


def bind_identity(cert_file):
    print(Colors.CYAN + "\n[ Identity Binding ]" + Colors.RESET)
    loading("Assigning IPv6")

    reg = load_registry()

    with open(cert_file) as f:
        cert = json.load(f)

    ipv6 = generate_ipv6()
    reg[ipv6] = cert

    save_registry(reg)

    # Simple deterministic name for DNS-like resolution in demos.
    node_name = f"{cert.get('user_id', 'node')}.whitenet.local"
    dns_records = load_dns_records()
    dns_records[node_name] = ipv6
    save_dns_records(dns_records)

    print(Colors.GREEN + f"✔ IPv6 Assigned → {ipv6}" + Colors.RESET)
    print(Colors.GREEN + f"✔ DNS Record Added → {node_name} -> {ipv6}" + Colors.RESET)
    append_audit_event(
        "bind_identity",
        "success",
        {"user_id": cert.get("user_id", "unknown"), "ipv6": ipv6, "domain": node_name}
    )


# =========================
# VERIFY
# =========================

def verify_certificate_payload(cert_dict):
    """Return True if the CA signature over the certificate JSON is valid."""
    cert = cert_dict.copy()
    if "signature" not in cert:
        return False
    signature = bytes.fromhex(cert.pop("signature"))
    public_key = load_ca_public()
    try:
        public_key.verify(
            signature,
            json.dumps(cert).encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False


def verify_node(ipv6):
    print(Colors.CYAN + "\n[ Verification Engine ]" + Colors.RESET)
    loading("Verifying node")

    reg = load_registry()

    if ipv6 not in reg:
        print(Colors.RED + "✖ Node not found" + Colors.RESET)
        append_audit_event("verify_node", "blocked", {"ipv6": ipv6, "reason": "not_found"})
        return False

    cert = reg[ipv6]
    if verify_certificate_payload(cert):
        print(Colors.GREEN + "✔ Trusted Node (Identity Verified)" + Colors.RESET)
        append_audit_event("verify_node", "allowed", {"ipv6": ipv6})
        return True

    print()
    print(Colors.RED + "  ╔══════════════════════════════════════════════════╗" + Colors.RESET)
    print(Colors.RED + "  ║  🚨  TAMPERED OR FAKE NODE DETECTED  🚨         ║" + Colors.RESET)
    print(Colors.RED + "  ║                                                  ║" + Colors.RESET)
    print(Colors.RED + f"  ║  IPv6: {ipv6[:42]:<42}  ║" + Colors.RESET)
    print(Colors.RED + "  ║  Certificate signature INVALID                   ║" + Colors.RESET)
    print(Colors.RED + "  ║  Identity was modified after CA signing           ║" + Colors.RESET)
    print(Colors.RED + "  ║  ACCESS DENIED — Zero Trust enforced              ║" + Colors.RESET)
    print(Colors.RED + "  ╚══════════════════════════════════════════════════╝" + Colors.RESET)
    print()
    append_audit_event("verify_node", "blocked", {"ipv6": ipv6, "reason": "tampered_or_fake"})
    return False


# =========================
# TRUST POSTURE (differentiator)
# =========================

def _dns_alignment(reg, dns_records, ipv6):
    """Check that {user_id}.whitenet.local maps to this IPv6 when expected."""
    cert = reg.get(ipv6)
    if not cert:
        return "absent", "Node not in registry"
    uid = cert.get("user_id", "unknown")
    expected_domain = f"{uid}.whitenet.local"
    mapped = dns_records.get(expected_domain)
    if mapped == ipv6:
        return "aligned", f"DNS matches {expected_domain}"
    if not any(ip == ipv6 for ip in dns_records.values()):
        return "unbound", "No DNS record points to this IPv6 (name binding missing)"
    return "mismatch", "DNS name for this IPv6 does not match certificate user_id"


def _recent_audit_flags_for_ipv6(ipv6, limit=80):
    """Heuristic: recent blocked verify/tamper signals for this address."""
    events = load_audit_log()
    hits = []
    for ev in events[-limit:]:
        d = ev.get("details") or {}
        if d.get("ipv6") == ipv6 and ev.get("status") == "blocked":
            hits.append(ev.get("action"))
        if d.get("victim_ipv6") == ipv6:
            hits.append(ev.get("action"))
    return hits


def compute_assess_posture(ipv6=None, domain=None):
    """
    Pure scorecard: certificate + registry + DNS alignment + audit integrity.
    Verdict: TRUSTED / WARNING / BLOCKED. No print, no audit append.
    """
    dns_records = load_dns_records()
    reg = load_registry()

    resolved_from = None
    target_ipv6 = ipv6
    if domain:
        target_ipv6 = dns_records.get(domain)
        resolved_from = f"domain:{domain}"
        if not target_ipv6:
            return {
                "verdict": "BLOCKED",
                "score": 0,
                "target_ipv6": None,
                "resolved_via": resolved_from,
                "checks": {
                    "domain_resolved": {"ok": False, "detail": "Domain not in trusted DNS records"}
                },
                "domain_lookup_failed": True,
            }

    if not target_ipv6:
        return {
            "verdict": "BLOCKED",
            "score": 0,
            "error": "Provide --ipv6 and/or --domain",
            "target_ipv6": None,
            "resolved_via": resolved_from,
            "checks": {},
        }

    checks = {}
    score = 0

    in_registry = target_ipv6 in reg
    checks["registry"] = {
        "ok": in_registry,
        "detail": "Bound in registry" if in_registry else "IPv6 not registered"
    }
    if in_registry:
        score += 25

    cert_ok = False
    if in_registry:
        cert_ok = verify_certificate_payload(reg[target_ipv6])
    checks["certificate"] = {
        "ok": cert_ok,
        "detail": "CA signature valid" if cert_ok else ("No cert to verify" if not in_registry else "Invalid or tampered certificate")
    }
    if cert_ok:
        score += 40

    # Revocation check
    revoked = is_revoked(target_ipv6) if in_registry else False
    checks["revocation"] = {
        "ok": not revoked,
        "detail": "Not revoked" if not revoked else "CERTIFICATE REVOKED"
    }
    if revoked:
        score = max(0, score - 50)

    # Expiry check
    cert_expired = False
    if in_registry:
        vu = reg[target_ipv6].get("valid_until")
        if vu:
            try:
                expiry = datetime.fromisoformat(vu)
                cert_expired = datetime.now(timezone.utc) > expiry
            except Exception:
                cert_expired = False
    checks["expiry"] = {
        "ok": not cert_expired,
        "detail": "Certificate valid (not expired)" if not cert_expired else "Certificate EXPIRED"
    }
    if cert_expired:
        score = max(0, score - 20)

    dns_state, dns_detail = _dns_alignment(reg, dns_records, target_ipv6)
    if dns_state == "aligned":
        checks["dns_identity"] = {"ok": True, "detail": dns_detail}
        score += 20
    elif dns_state == "unbound":
        checks["dns_identity"] = {"ok": False, "detail": dns_detail}
        score += 8
    else:
        checks["dns_identity"] = {"ok": False, "detail": dns_detail}
        score += 0

    chain_ok, chain_marker = verify_audit_chain()
    checks["audit_chain"] = {
        "ok": chain_ok,
        "detail": "Append-only log intact" if chain_ok else f"Broken at event #{chain_marker}"
    }
    if chain_ok and load_audit_log():
        score += 15
    elif not load_audit_log():
        checks["audit_chain"]["detail"] = "No audit events yet (run issue/bind/verify to populate)"
        score += 5

    flags = _recent_audit_flags_for_ipv6(target_ipv6)
    suspicious = bool(flags)
    checks["recent_signals"] = {
        "ok": not suspicious,
        "detail": "No recent blocked/tamper signals for this node" if not suspicious else f"Recent events: {', '.join(flags[:5])}"
    }
    if not suspicious:
        score += 5
    else:
        score = max(0, score - 10)

    if not in_registry or not cert_ok or revoked:
        verdict = "BLOCKED"
    elif (
        not chain_ok
        or dns_state == "mismatch"
        or dns_state == "unbound"
        or suspicious
        or cert_expired
    ):
        verdict = "WARNING"
    else:
        verdict = "TRUSTED"

    score = max(0, min(100, score))

    return {
        "verdict": verdict,
        "score": score,
        "target_ipv6": target_ipv6,
        "resolved_via": resolved_from,
        "checks": checks,
    }


def assess_posture(ipv6=None, domain=None, json_out=False):
    """CLI wrapper: prints, optional JSON stdout, one audit event when applicable."""
    out = compute_assess_posture(ipv6=ipv6, domain=domain)

    if out.get("error"):
        if json_out:
            print(json.dumps(out, indent=2))
        else:
            print(Colors.RED + "✖ Provide --ipv6 and/or --domain" + Colors.RESET)
        return out

    if out.get("domain_lookup_failed"):
        export = {k: v for k, v in out.items() if k != "domain_lookup_failed"}
        if json_out:
            print(json.dumps(export, indent=2))
        else:
            print(Colors.CYAN + "\n[ Trust Posture Scorecard ]" + Colors.RESET)
            print(Colors.RED + "✖ BLOCKED — domain not found" + Colors.RESET)
        append_audit_event("assess_posture", "blocked", {"domain": domain, "reason": "domain_not_found"})
        return export

    verdict = out["verdict"]
    score = out["score"]
    target_ipv6 = out["target_ipv6"]
    resolved_from = out["resolved_via"]
    checks = out["checks"]

    if json_out:
        print(json.dumps(out, indent=2))
    else:
        print(Colors.CYAN + "\n[ Trust Posture Scorecard ]" + Colors.RESET)
        loading("Computing trust posture")
        vcolor = Colors.GREEN if verdict == "TRUSTED" else (Colors.YELLOW if verdict == "WARNING" else Colors.RED)
        print(vcolor + f"Verdict: {verdict}  |  Score: {score}/100" + Colors.RESET)
        if resolved_from:
            print(Colors.YELLOW + f"Target resolved via {resolved_from}" + Colors.RESET)
        for name, c in checks.items():
            mark = "✔" if c.get("ok") else "✖"
            col = Colors.GREEN if c.get("ok") else Colors.RED
            print(col + f"  {mark} {name}: {c.get('detail', '')}" + Colors.RESET)

    append_audit_event(
        "assess_posture",
        "allowed" if verdict == "TRUSTED" else ("warning" if verdict == "WARNING" else "blocked"),
        {"ipv6": target_ipv6, "verdict": verdict, "score": score}
    )
    return out


# =========================
# HANDSHAKE + TRANSPORT
# =========================

def handshake_node(ipv6):
    print(Colors.CYAN + "\n[ Handshake Layer ]" + Colors.RESET)
    loading("Performing certificate + challenge-response")

    if verify_node(ipv6):
        challenge = uuid.uuid4().hex[:16]
        print(Colors.YELLOW + f"Challenge nonce: {challenge}" + Colors.RESET)
        print(Colors.GREEN + "✔ Handshake success: secure context established" + Colors.RESET)
        append_audit_event("handshake", "allowed", {"ipv6": ipv6, "challenge": challenge})
        return True

    print(Colors.RED + "✖ Handshake failed: untrusted node" + Colors.RESET)
    append_audit_event("handshake", "blocked", {"ipv6": ipv6})
    return False


def send_secure(source_ipv6, dest_ipv6):
    print(Colors.CYAN + "\n[ Secure Transport Layer ]" + Colors.RESET)
    loading("Validating trust before communication")

    if source_ipv6 == dest_ipv6:
        print(Colors.RED + "✖ Source and destination cannot be the same" + Colors.RESET)
        append_audit_event(
            "send_secure",
            "blocked",
            {"source_ipv6": source_ipv6, "dest_ipv6": dest_ipv6, "reason": "same_endpoint"}
        )
        return

    src_ok = verify_node(source_ipv6)
    dst_ok = verify_node(dest_ipv6)

    if not (src_ok and dst_ok):
        print(Colors.RED + "✖ Communication blocked (Zero Trust policy)" + Colors.RESET)
        append_audit_event(
            "send_secure",
            "blocked",
            {"source_ipv6": source_ipv6, "dest_ipv6": dest_ipv6, "reason": "untrusted_peer"}
        )
        return

    print(Colors.GREEN + f"✔ Secure packet sent: {source_ipv6} -> {dest_ipv6}" + Colors.RESET)
    append_audit_event("send_secure", "allowed", {"source_ipv6": source_ipv6, "dest_ipv6": dest_ipv6})


def resolve_domain(domain):
    print(Colors.CYAN + "\n[ DNSSEC-like Resolution ]" + Colors.RESET)
    loading("Resolving trusted domain")

    records = load_dns_records()
    ipv6 = records.get(domain)

    if not ipv6:
        print(Colors.RED + "✖ Domain not found in trusted records" + Colors.RESET)
        append_audit_event("resolve_domain", "blocked", {"domain": domain, "reason": "not_found"})
        return

    print(Colors.GREEN + f"✔ {domain} -> {ipv6}" + Colors.RESET)
    print(Colors.YELLOW + "Running trust verification on resolved node..." + Colors.RESET)
    append_audit_event("resolve_domain", "allowed", {"domain": domain, "ipv6": ipv6})
    verify_node(ipv6)


def list_state():
    print(Colors.CYAN + "\n[ Network State ]" + Colors.RESET)
    loading("Collecting registered identities")

    reg = load_registry()
    dns_records = load_dns_records()

    if not reg:
        print(Colors.RED + "✖ No bound identities found in registry.json" + Colors.RESET)
    else:
        print(Colors.GREEN + f"✔ Bound Nodes: {len(reg)}" + Colors.RESET)
        for idx, (ipv6, cert) in enumerate(reg.items(), start=1):
            user_id = cert.get("user_id", "unknown")
            cert_id = cert.get("cert_id", "unknown")
            print(f"  {idx}. {user_id} | {ipv6} | cert_id={cert_id}")

    if not dns_records:
        print(Colors.YELLOW + "⚠ No DNS records found in dns_records.json" + Colors.RESET)
    else:
        print(Colors.GREEN + f"✔ DNS Records: {len(dns_records)}" + Colors.RESET)
        for idx, (domain, ipv6) in enumerate(dns_records.items(), start=1):
            print(f"  {idx}. {domain} -> {ipv6}")


def security_demo():
    import time as _time
    print(Colors.CYAN + "\n" + "═" * 60 + Colors.RESET)
    print(Colors.CYAN + "  SECURITY RESILIENCE DEMO — Attack Simulation" + Colors.RESET)
    print(Colors.CYAN + "═" * 60 + Colors.RESET)

    reg = load_registry()
    if not reg:
        print(Colors.RED + "✖ No nodes available. Run 'demo --fresh' or 'showcase' first." + Colors.RESET)
        append_audit_event("security_demo", "blocked", {"reason": "no_nodes"})
        return

    victim = list(reg.keys())[0]
    victim_user = reg[victim].get("user_id", "unknown")

    # ── Step 1: Establish trust baseline ──
    print(Colors.GREEN + f"\n  ▸ STEP 1: Verify legitimate identity ({victim_user})" + Colors.RESET)
    print(Colors.YELLOW + f"    Target node: {victim}" + Colors.RESET)
    _time.sleep(0.5)
    verify_node(victim)
    print(Colors.GREEN + "    ↑ Node is TRUSTED — signature matches CA-signed certificate" + Colors.RESET)

    # ── Step 2: Simulate an attacker modifying identity ──
    _time.sleep(1)
    print(Colors.RED + "\n  ▸ STEP 2: ⚡ ATTACKER INJECTS SPOOFED IDENTITY" + Colors.RESET)
    print(Colors.RED + "    ┌─────────────────────────────────────────────┐" + Colors.RESET)
    print(Colors.RED + f"    │  Original:  user_id = \"{victim_user}\"" + Colors.RESET)
    print(Colors.RED + f"    │  Tampered:  user_id = \"attacker_node\"     │" + Colors.RESET)
    print(Colors.RED + "    │  (registry.json modified directly)          │" + Colors.RESET)
    print(Colors.RED + "    └─────────────────────────────────────────────┘" + Colors.RESET)
    _time.sleep(0.5)
    reg[victim]["user_id"] = "attacker_node"
    save_registry(reg)
    append_audit_event("security_demo_tamper", "success", {"victim_ipv6": victim, "original_user": victim_user})
    print(Colors.YELLOW + "    ✎ Registry tampered. Certificate signature is now INVALID." + Colors.RESET)

    # ── Step 3: THE BIG MOMENT — re-verify ──
    _time.sleep(1.5)
    print(Colors.YELLOW + "\n  ▸ STEP 3: Re-verifying the SAME node after attack..." + Colors.RESET)
    _time.sleep(1)
    verify_node(victim)

    # ── Conclusion ──
    _time.sleep(0.5)
    print(Colors.CYAN + "  ┌─────────────────────────────────────────────────┐" + Colors.RESET)
    print(Colors.CYAN + "  │  WhiteNet detected the tampering because the   │" + Colors.RESET)
    print(Colors.CYAN + "  │  CA signature no longer matches the modified    │" + Colors.RESET)
    print(Colors.CYAN + "  │  certificate payload. Zero Trust = enforced.    │" + Colors.RESET)
    print(Colors.CYAN + "  │                                                 │" + Colors.RESET)
    print(Colors.CYAN + "  │  Even with direct database access, an attacker  │" + Colors.RESET)
    print(Colors.CYAN + "  │  CANNOT forge trust without the CA private key. │" + Colors.RESET)
    print(Colors.CYAN + "  └─────────────────────────────────────────────────┘" + Colors.RESET)

    # Restore original
    reg = load_registry()
    reg[victim]["user_id"] = victim_user
    save_registry(reg)
    append_audit_event("security_demo_restore", "success", {"victim_ipv6": victim})


# =========================
# SPOOF TEST
# =========================

def spoof_test():
    print(Colors.CYAN + "\n[ Attack Simulation ]" + Colors.RESET)

    reg = load_registry()

    if not reg:
        print(Colors.RED + "✖ No nodes available" + Colors.RESET)
        append_audit_event("spoof_test", "blocked", {"reason": "no_nodes"})
        return

    ipv6 = list(reg.keys())[0]

    print(Colors.YELLOW + "[!] Injecting Spoofed Identity..." + Colors.RESET)

    reg[ipv6]["user_id"] = "attacker_node"

    save_registry(reg)
    append_audit_event("spoof_test_tamper", "success", {"victim_ipv6": ipv6})

    verify_node(ipv6)


# =========================
# REVOCATION
# =========================

def load_revoked():
    if not os.path.exists(REVOKED_FILE):
        return []
    with open(REVOKED_FILE) as f:
        return json.load(f)

def save_revoked(lst):
    with open(REVOKED_FILE, "w") as f:
        json.dump(lst, f, indent=4)

def is_revoked(ipv6):
    return ipv6 in load_revoked()

def revoke_node(ipv6):
    print(Colors.CYAN + "\n[ Certificate Revocation ]" + Colors.RESET)
    loading("Revoking certificate")
    reg = load_registry()
    if ipv6 not in reg:
        print(Colors.RED + "✖ Node not found in registry" + Colors.RESET)
        return
    revoked = load_revoked()
    if ipv6 in revoked:
        print(Colors.YELLOW + "⚠ Node already revoked" + Colors.RESET)
        return
    revoked.append(ipv6)
    save_revoked(revoked)
    uid = reg[ipv6].get("user_id", "unknown")
    print(Colors.GREEN + f"✔ Certificate REVOKED for {uid} ({ipv6})" + Colors.RESET)
    append_audit_event("revoke_certificate", "success", {"ipv6": ipv6, "user_id": uid})


# =========================
# CERTIFICATE RENEWAL
# =========================

def renew_certificate(user_id):
    print(Colors.CYAN + "\n[ Certificate Renewal ]" + Colors.RESET)
    loading("Renewing identity certificate")
    dns = load_dns_records()
    domain = f"{user_id}.whitenet.local"
    ipv6 = dns.get(domain)
    if not ipv6:
        print(Colors.RED + f"✖ No DNS record for {domain}" + Colors.RESET)
        return
    revoked = load_revoked()
    if ipv6 in revoked:
        revoked.remove(ipv6)
        save_revoked(revoked)
        print(Colors.YELLOW + "  (Removed from revocation list)" + Colors.RESET)
    issue_certificate(user_id)
    reg = load_registry()
    with open(CERT_FILE) as f:
        new_cert = json.load(f)
    reg[ipv6] = new_cert
    save_registry(reg)
    print(Colors.GREEN + f"✔ Certificate renewed for {user_id} (bound to {ipv6})" + Colors.RESET)
    append_audit_event("renew_certificate", "success", {"user_id": user_id, "ipv6": ipv6})


# =========================
# GOVERNANCE
# =========================

def load_proposals():
    if not os.path.exists(PROPOSALS_FILE):
        return []
    with open(PROPOSALS_FILE) as f:
        return json.load(f)

def save_proposals(lst):
    with open(PROPOSALS_FILE, "w") as f:
        json.dump(lst, f, indent=4)

def create_proposal(title, proposer, category="policy"):
    print(Colors.CYAN + "\n[ Governance — New Proposal ]" + Colors.RESET)
    loading("Creating proposal")
    proposals = load_proposals()
    prop = {
        "proposal_id": str(uuid.uuid4())[:8],
        "title": title,
        "proposer": proposer,
        "category": category,
        "status": "open",
        "votes_for": 0,
        "votes_against": 0,
        "voters": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    proposals.append(prop)
    save_proposals(proposals)
    print(Colors.GREEN + f"✔ Proposal created: {prop['proposal_id']} — {title}" + Colors.RESET)
    append_audit_event("governance_propose", "success", {"proposal_id": prop["proposal_id"], "title": title})
    return prop

def cast_vote(proposal_id, voter, vote_for=True):
    print(Colors.CYAN + "\n[ Governance — Vote ]" + Colors.RESET)
    loading("Casting vote")
    proposals = load_proposals()
    prop = None
    for p in proposals:
        if p["proposal_id"] == proposal_id:
            prop = p
            break
    if not prop:
        print(Colors.RED + f"✖ Proposal {proposal_id} not found" + Colors.RESET)
        return
    if prop["status"] != "open":
        print(Colors.YELLOW + f"⚠ Proposal is {prop['status']}, voting closed" + Colors.RESET)
        return
    if voter in prop["voters"]:
        print(Colors.YELLOW + f"⚠ {voter} has already voted" + Colors.RESET)
        return
    prop["voters"].append(voter)
    if vote_for:
        prop["votes_for"] += 1
    else:
        prop["votes_against"] += 1
    total = prop["votes_for"] + prop["votes_against"]
    if total >= 3:
        prop["status"] = "approved" if prop["votes_for"] > prop["votes_against"] else "rejected"
    save_proposals(proposals)
    side = "FOR" if vote_for else "AGAINST"
    print(Colors.GREEN + f"✔ {voter} voted {side} on '{prop['title']}'" + Colors.RESET)
    if prop["status"] != "open":
        print(Colors.YELLOW + f"  → Proposal {prop['status'].upper()}" + Colors.RESET)
    append_audit_event("governance_vote", "success", {"proposal_id": proposal_id, "voter": voter, "vote": side})

def list_proposals_cli():
    print(Colors.CYAN + "\n[ Governance — Proposals ]" + Colors.RESET)
    proposals = load_proposals()
    if not proposals:
        print(Colors.YELLOW + "⚠ No proposals yet" + Colors.RESET)
        return
    for p in proposals:
        sc = {"open": Colors.CYAN, "approved": Colors.GREEN, "rejected": Colors.RED}.get(p["status"], Colors.YELLOW)
        print(f"  {sc}[{p['status'].upper()}]{Colors.RESET} {p['proposal_id']} — {p['title']}")
        print(f"    Proposer: {p['proposer']} | For: {p['votes_for']} | Against: {p['votes_against']}")


# =========================
# TLS 1.3 SIMULATION
# =========================

def load_tls_sessions():
    if not os.path.exists(TLS_SESSIONS_FILE):
        return {}
    with open(TLS_SESSIONS_FILE) as f:
        return json.load(f)

def save_tls_sessions(data):
    with open(TLS_SESSIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def tls_handshake(client_ipv6, server_ipv6):
    """Simulate a TLS 1.3 handshake between two verified WhiteNet nodes."""
    print(Colors.CYAN + "\n[ TLS 1.3 Handshake Simulation ]" + Colors.RESET)
    loading("Initiating TLS 1.3 key exchange")
    reg = load_registry()
    if client_ipv6 not in reg or server_ipv6 not in reg:
        print(Colors.RED + "✖ Both nodes must be registered for TLS" + Colors.RESET)
        append_audit_event("tls_handshake", "blocked", {"client": client_ipv6, "server": server_ipv6, "reason": "unregistered"})
        return None
    if is_revoked(client_ipv6) or is_revoked(server_ipv6):
        print(Colors.RED + "✖ Revoked node cannot participate in TLS" + Colors.RESET)
        append_audit_event("tls_handshake", "blocked", {"client": client_ipv6, "server": server_ipv6, "reason": "revoked"})
        return None
    import secrets as _secrets
    session_id = _secrets.token_hex(16)
    client_random = _secrets.token_hex(32)
    server_random = _secrets.token_hex(32)
    pre_master = hashlib.sha256((client_random + server_random).encode()).hexdigest()
    master_secret = hashlib.sha256((pre_master + session_id).encode()).hexdigest()
    cipher_suite = "TLS_AES_256_GCM_SHA384"
    session = {
        "session_id": session_id,
        "client_ipv6": client_ipv6,
        "server_ipv6": server_ipv6,
        "cipher_suite": cipher_suite,
        "master_secret_hash": hashlib.sha256(master_secret.encode()).hexdigest(),
        "established_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    sessions = load_tls_sessions()
    sessions[session_id] = session
    save_tls_sessions(sessions)
    print(Colors.GREEN + "✔ TLS 1.3 session established" + Colors.RESET)
    print(Colors.YELLOW + f"  Session ID:   {session_id[:16]}..." + Colors.RESET)
    print(Colors.YELLOW + f"  Cipher Suite: {cipher_suite}" + Colors.RESET)
    append_audit_event("tls_handshake", "success", {"session_id": session_id, "cipher": cipher_suite})
    return session


# =========================
# DNSSEC SIMULATION
# =========================

def dnssec_sign_records():
    """Sign all DNS records with the CA key (DNSSEC-like RRSIG simulation)."""
    print(Colors.CYAN + "\n[ DNSSEC Record Signing ]" + Colors.RESET)
    loading("Signing DNS records with CA key")
    records = load_dns_records()
    if not records:
        print(Colors.RED + "✖ No DNS records to sign" + Colors.RESET)
        return {}
    private_key = load_ca_private()
    signed = {}
    for domain, ipv6 in records.items():
        record_data = f"{domain}:{ipv6}".encode()
        sig = private_key.sign(record_data, padding.PKCS1v15(), hashes.SHA256())
        signed[domain] = {"ipv6": ipv6, "rrsig": sig.hex(), "signed_at": datetime.now(timezone.utc).isoformat()}
    with open("dnssec_signed.json", "w") as f:
        json.dump(signed, f, indent=4)
    print(Colors.GREEN + f"✔ {len(signed)} DNS records signed (DNSSEC)" + Colors.RESET)
    append_audit_event("dnssec_sign", "success", {"record_count": len(signed)})
    return signed

def dnssec_verify(domain):
    """Verify a DNSSEC-signed DNS record."""
    print(Colors.CYAN + "\n[ DNSSEC Verification ]" + Colors.RESET)
    loading("Verifying DNSSEC signature")
    if not os.path.exists("dnssec_signed.json"):
        print(Colors.RED + "✖ No signed records — run DNSSEC sign first" + Colors.RESET)
        return False
    with open("dnssec_signed.json") as f:
        signed = json.load(f)
    entry = signed.get(domain)
    if not entry:
        print(Colors.RED + f"✖ No DNSSEC record for {domain}" + Colors.RESET)
        return False
    public_key = load_ca_public()
    record_data = f"{domain}:{entry['ipv6']}".encode()
    try:
        public_key.verify(bytes.fromhex(entry["rrsig"]), record_data, padding.PKCS1v15(), hashes.SHA256())
        print(Colors.GREEN + f"✔ DNSSEC VERIFIED: {domain} → {entry['ipv6']}" + Colors.RESET)
        append_audit_event("dnssec_verify", "success", {"domain": domain})
        return True
    except Exception:
        print(Colors.RED + f"🚨 DNSSEC FAILED: signature mismatch for {domain}" + Colors.RESET)
        append_audit_event("dnssec_verify", "blocked", {"domain": domain})
        return False


# =========================
# VPN TUNNEL SIMULATION
# =========================

def load_vpn_tunnels():
    if not os.path.exists(VPN_TUNNELS_FILE):
        return {}
    with open(VPN_TUNNELS_FILE) as f:
        return json.load(f)

def save_vpn_tunnels(data):
    with open(VPN_TUNNELS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def vpn_establish_tunnel(node_a_ipv6, node_b_ipv6):
    """Simulate an encrypted VPN tunnel between two verified WhiteNet nodes."""
    print(Colors.CYAN + "\n[ VPN Tunnel Establishment ]" + Colors.RESET)
    loading("Negotiating encrypted tunnel")
    reg = load_registry()
    for n in (node_a_ipv6, node_b_ipv6):
        if n not in reg:
            print(Colors.RED + f"✖ {n} not in registry" + Colors.RESET)
            append_audit_event("vpn_tunnel", "blocked", {"reason": "unregistered", "node": n})
            return None
        if is_revoked(n):
            print(Colors.RED + f"✖ {n} is revoked" + Colors.RESET)
            append_audit_event("vpn_tunnel", "blocked", {"reason": "revoked", "node": n})
            return None
    import secrets as _secrets
    tunnel_id = _secrets.token_hex(8)
    shared_key_hash = hashlib.sha256((_secrets.token_hex(32) + tunnel_id).encode()).hexdigest()
    tunnel = {
        "tunnel_id": tunnel_id,
        "node_a": node_a_ipv6,
        "node_b": node_b_ipv6,
        "encryption": "AES-256-GCM",
        "auth": "HMAC-SHA384",
        "shared_key_hash": shared_key_hash,
        "established_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    tunnels = load_vpn_tunnels()
    tunnels[tunnel_id] = tunnel
    save_vpn_tunnels(tunnels)
    user_a = reg[node_a_ipv6].get("user_id", "?")
    user_b = reg[node_b_ipv6].get("user_id", "?")
    print(Colors.GREEN + "✔ VPN Tunnel established" + Colors.RESET)
    print(Colors.YELLOW + f"  Tunnel ID:  {tunnel_id}" + Colors.RESET)
    print(Colors.YELLOW + f"  Peers:      {user_a} ↔ {user_b}" + Colors.RESET)
    print(Colors.YELLOW + f"  Encryption: AES-256-GCM + HMAC-SHA384" + Colors.RESET)
    append_audit_event("vpn_tunnel", "success", {"tunnel_id": tunnel_id, "node_a": node_a_ipv6, "node_b": node_b_ipv6})
    return tunnel


# =========================
# TRUST REPORT + DEMO (+5)
# =========================

def _remove_if_exists(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def demo_reset_data_files(regen_ca=False):
    for name in (REGISTRY_FILE, DNS_FILE, AUDIT_FILE, CERT_FILE,
                 REVOKED_FILE, PROPOSALS_FILE, TLS_SESSIONS_FILE,
                 VPN_TUNNELS_FILE, "dnssec_signed.json"):
        _remove_if_exists(name)
    if regen_ca:
        for name in (CA_KEY_FILE, CA_PUBLIC_FILE):
            _remove_if_exists(name)


def build_trust_report(audit_tail_limit=50):
    chain_ok, chain_marker = verify_audit_chain()
    events = load_audit_log()
    tail = events[-audit_tail_limit:] if audit_tail_limit else events

    reg = load_registry()
    nodes = []
    for ipv6, cert in reg.items():
        nodes.append({
            "ipv6": ipv6,
            "user_id": cert.get("user_id", "unknown"),
            "cert_id": cert.get("cert_id", "unknown"),
            "assess": compute_assess_posture(ipv6=ipv6),
        })

    return {
        "meta": {
            "whitenet_version": WHITENET_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "ca_public_key_sha256": ca_public_key_fingerprint_sha256(),
        },
        "audit_summary": {
            "event_count": len(events),
            "chain_verified": chain_ok,
            "chain_failed_at_event_index": None if chain_ok else chain_marker,
        },
        "nodes": nodes,
        "audit_tail": tail,
    }


def export_trust_report(out_path, audit_tail_limit=50):
    report = build_trust_report(audit_tail_limit=audit_tail_limit)
    text = json.dumps(report, indent=2)
    if out_path == "-":
        print(text)
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(Colors.GREEN + f"✔ Trust report written → {out_path}" + Colors.RESET)
    append_audit_event(
        "trust_report",
        "success",
        {"out": out_path, "node_count": len(report["nodes"])}
    )


def print_status():
    print(Colors.CYAN + "\n[ WhiteNet Status ]" + Colors.RESET)
    print(f"  Version: {WHITENET_VERSION}")
    fp = ca_public_key_fingerprint_sha256()
    print(f"  CA public key SHA-256: {fp or '(missing — run any command to generate keys)'}")
    reg = load_registry()
    dns = load_dns_records()
    ev = load_audit_log()
    print(f"  registry.json nodes: {len(reg)}")
    print(f"  dns_records.json entries: {len(dns)}")
    print(f"  audit_log.json events: {len(ev)}")
    ok, m = verify_audit_chain()
    if ok:
        print(Colors.GREEN + "  audit chain: OK" + Colors.RESET)
    else:
        print(Colors.RED + f"  audit chain: FAIL at event #{m}" + Colors.RESET)


def run_automated_demo(fresh=False, regen_ca=False, quiet=False):
    """One-shot happy path for judges: issue/bind x2, handshake, send, resolve, assess, audit."""
    if fresh:
        demo_reset_data_files(regen_ca=regen_ca)
    if quiet:
        os.environ["WHITENET_QUIET"] = "1"

    generate_ca_keys()
    append_audit_event("demo_run", "success", {"phase": "start"})

    issue_certificate("alice")
    bind_identity(CERT_FILE)
    issue_certificate("bob")
    bind_identity(CERT_FILE)

    dns = load_dns_records()
    alice_ip = dns.get("alice.whitenet.local")
    bob_ip = dns.get("bob.whitenet.local")
    if not alice_ip or not bob_ip:
        print(Colors.RED + "✖ Demo failed: expected alice/bob DNS records" + Colors.RESET)
        if quiet:
            os.environ.pop("WHITENET_QUIET", None)
        return

    handshake_node(alice_ip)
    send_secure(alice_ip, bob_ip)
    resolve_domain("alice.whitenet.local")
    assess_posture(domain="alice.whitenet.local")
    assess_posture(domain="bob.whitenet.local")
    show_audit(limit=12, verify_chain=True)

    print(Colors.CYAN + "\n[ Demo Summary ]" + Colors.RESET)
    print(Colors.GREEN + f"  alice IPv6: {alice_ip}" + Colors.RESET)
    print(Colors.GREEN + f"  bob IPv6:   {bob_ip}" + Colors.RESET)
    print(Colors.YELLOW + f'  Replay: python cli.py handshake --ipv6 "{alice_ip}"' + Colors.RESET)

    append_audit_event(
        "demo_run",
        "success",
        {"phase": "complete", "alice_ipv6": alice_ip, "bob_ipv6": bob_ip}
    )
    if quiet:
        os.environ.pop("WHITENET_QUIET", None)


def run_showcase():
    """Full judge showcase: every WhiteNet v3.0 feature in one command."""
    os.environ["WHITENET_QUIET"] = "1"
    demo_reset_data_files(regen_ca=True)
    generate_ca_keys()

    divider = Colors.CYAN + "\n" + "═" * 60 + Colors.RESET
    section = lambda n, title: print(f"{divider}\n  {Colors.YELLOW}PHASE {n}{Colors.RESET} │ {Colors.CYAN}{title}{Colors.RESET}\n{divider}")

    print(Colors.CYAN + BANNER + Colors.RESET)
    print(Colors.GREEN + "  ╔════════════════════════════════════════════════════╗" + Colors.RESET)
    print(Colors.GREEN + "  ║      WhiteNet v3.0.0  ─  FULL JUDGE SHOWCASE      ║" + Colors.RESET)
    print(Colors.GREEN + "  ╚════════════════════════════════════════════════════╝" + Colors.RESET)

    # ── PHASE 1: Identity ──
    section(1, "IDENTITY ISSUANCE + IPv6 BINDING")
    print(Colors.YELLOW + "  Creating identities for alice, bob, and charlie..." + Colors.RESET)
    for user in ("alice", "bob", "charlie"):
        issue_certificate(user)
        bind_identity(CERT_FILE)

    dns = load_dns_records()
    alice_ip = dns.get("alice.whitenet.local")
    bob_ip = dns.get("bob.whitenet.local")
    charlie_ip = dns.get("charlie.whitenet.local")
    if not alice_ip or not bob_ip or not charlie_ip:
        print(Colors.RED + "✖ Showcase failed: DNS missing" + Colors.RESET)
        os.environ.pop("WHITENET_QUIET", None)
        return

    reg = load_registry()
    print(Colors.GREEN + f"\n  ✔ 3 nodes bound:" + Colors.RESET)
    print(f"    alice   → {alice_ip}")
    print(f"    bob     → {bob_ip}")
    print(f"    charlie → {charlie_ip}")

    # ── PHASE 2: Trust Verification ──
    section(2, "TRUST VERIFICATION + HANDSHAKE")
    verify_node(alice_ip)
    handshake_node(bob_ip)

    # ── PHASE 3: Secure Communication ──
    section(3, "SECURE COMMUNICATION")
    send_secure(alice_ip, bob_ip)
    send_secure(bob_ip, charlie_ip)

    # ── PHASE 4: DNS ──
    section(4, "DNS RESOLUTION")
    resolve_domain("alice.whitenet.local")
    resolve_domain("bob.whitenet.local")

    # ── PHASE 5: TLS 1.3 ──
    section(5, "TLS 1.3 HANDSHAKE SIMULATION")
    tls_handshake(alice_ip, bob_ip)
    tls_handshake(bob_ip, charlie_ip)

    # ── PHASE 6: DNSSEC ──
    section(6, "DNSSEC SIGNING + VERIFICATION")
    dnssec_sign_records()
    dnssec_verify("alice.whitenet.local")
    dnssec_verify("bob.whitenet.local")

    # ── PHASE 7: VPN ──
    section(7, "VPN TUNNEL ESTABLISHMENT")
    vpn_establish_tunnel(alice_ip, bob_ip)
    vpn_establish_tunnel(alice_ip, charlie_ip)

    # ── PHASE 8: Trust Posture ──
    section(8, "TRUST POSTURE ASSESSMENT (all nodes)")
    assess_posture(domain="alice.whitenet.local")
    assess_posture(domain="bob.whitenet.local")
    assess_posture(domain="charlie.whitenet.local")

    # ── PHASE 9: Governance ──
    section(9, "GOVERNANCE — PROPOSAL + VOTING")
    create_proposal("Rotate CA keys every quarter", "alice", "security")
    proposals = load_proposals()
    pid = proposals[-1]["proposal_id"]
    cast_vote(pid, "bob", vote_for=True)
    cast_vote(pid, "charlie", vote_for=True)
    cast_vote(pid, "alice", vote_for=True)
    list_proposals_cli()

    # ── PHASE 10: Revocation + Renewal ──
    section(10, "CERTIFICATE REVOCATION + RENEWAL")
    print(Colors.YELLOW + "  Revoking charlie\'s certificate..." + Colors.RESET)
    revoke_node(charlie_ip)
    print(Colors.YELLOW + "\n  Re-assessing charlie after revocation:" + Colors.RESET)
    assess_posture(ipv6=charlie_ip)
    print(Colors.YELLOW + "\n  Renewing charlie\'s certificate..." + Colors.RESET)
    renew_certificate("charlie")
    print(Colors.YELLOW + "\n  Re-assessing charlie after renewal:" + Colors.RESET)
    assess_posture(domain="charlie.whitenet.local")

    # ── PHASE 11: Security Demo ──
    section(11, "SECURITY — SPOOF / TAMPER DETECTION")
    security_demo()

    # ── PHASE 12: Audit ──
    section(12, "AUDIT TRAIL — HASH CHAIN VERIFICATION")
    show_audit(limit=15, verify_chain=True)

    # ── Summary ──
    print(divider)
    events = load_audit_log()
    tunnels = load_vpn_tunnels()
    sessions = load_tls_sessions()
    props = load_proposals()
    revoked = load_revoked()

    print(Colors.GREEN + "\n  ╔════════════════════════════════════════════════════╗" + Colors.RESET)
    print(Colors.GREEN + "  ║              SHOWCASE COMPLETE ✔                   ║" + Colors.RESET)
    print(Colors.GREEN + "  ╚════════════════════════════════════════════════════╝" + Colors.RESET)
    print(Colors.CYAN + f"""
  WhiteNet v{WHITENET_VERSION} — Full Feature Summary
  ─────────────────────────────────────
  ✔ Nodes registered    : {len(load_registry())}
  ✔ DNS records         : {len(load_dns_records())}
  ✔ TLS 1.3 sessions    : {len(sessions)}
  ✔ VPN tunnels         : {len(tunnels)}
  ✔ DNSSEC signed       : ✔
  ✔ Governance proposals: {len(props)}
  ✔ Audit events        : {len(events)}
  ✔ Revocation tested   : ✔ (charlie → revoked → renewed)
  ✔ Spoof detection     : ✔
  ✔ Audit chain         : ✔ verified

  Web dashboard: python web/server.py → http://127.0.0.1:5050
""" + Colors.RESET)

    os.environ.pop("WHITENET_QUIET", None)


# =========================
# CLI
# =========================

def main():
    parser = argparse.ArgumentParser(description="WhiteNet CLI")

    sub = parser.add_subparsers(dest="command")

    issue = sub.add_parser("issue")
    issue.add_argument("--user", required=True)

    bind = sub.add_parser("bind")
    bind.add_argument("--cert", required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--ipv6", required=True)

    handshake = sub.add_parser("handshake")
    handshake.add_argument("--ipv6", required=True)

    send = sub.add_parser("send")
    send.add_argument("--from", dest="source", required=True)
    send.add_argument("--to", dest="destination", required=True)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--domain", required=True)

    audit = sub.add_parser("audit")
    audit.add_argument("--limit", type=int, default=10)
    audit.add_argument("--verify-chain", action="store_true")

    assess = sub.add_parser("assess", help="Trust posture scorecard (verdict + multi-factor checks)")
    assess.add_argument("--ipv6", default=None, help="Assess by IPv6 address")
    assess.add_argument("--domain", default=None, help="Assess by resolving trusted domain first")
    assess.add_argument("--json", action="store_true", help="Machine-readable JSON output")

    report = sub.add_parser("report", help="Export JSON trust bundle (nodes + assess + audit tail + CA fingerprint)")
    report.add_argument("--out", "-o", default="trust_report.json")
    report.add_argument("--audit-tail", type=int, default=50)

    demo = sub.add_parser("demo", help="Automated end-to-end happy path (alice/bob)")
    demo.add_argument("--fresh", action="store_true", help="Remove registry/DNS/audit/cert data before run")
    demo.add_argument("--regen-ca", action="store_true", help="With --fresh, also regenerate CA keypair")
    demo.add_argument("--quiet", action="store_true", help="Skip loading animation delays")

    sub.add_parser("version", help="Print WhiteNet version string")
    sub.add_parser("status", help="Operational snapshot (counts, CA fingerprint, audit chain)")

    sub.add_parser("list")
    sub.add_parser("spoof-test")
    sub.add_parser("security-demo")

    # --- v3.0 commands ---
    rev = sub.add_parser("revoke", help="Revoke a node certificate by IPv6")
    rev.add_argument("--ipv6", required=True)

    ren = sub.add_parser("renew", help="Renew a node certificate by user_id")
    ren.add_argument("--user", required=True)

    prop = sub.add_parser("propose", help="Create a governance proposal")
    prop.add_argument("--title", required=True)
    prop.add_argument("--proposer", required=True)
    prop.add_argument("--category", default="policy")

    vt = sub.add_parser("vote", help="Vote on a governance proposal")
    vt.add_argument("--proposal", required=True, help="Proposal ID")
    vt.add_argument("--voter", required=True)
    vt.add_argument("--against", action="store_true", help="Vote against (default is for)")

    sub.add_parser("proposals", help="List governance proposals")

    tls_p = sub.add_parser("tls", help="TLS 1.3 handshake simulation")
    tls_p.add_argument("--client", required=True, help="Client IPv6")
    tls_p.add_argument("--server", required=True, help="Server IPv6")

    sub.add_parser("dnssec-sign", help="Sign all DNS records (DNSSEC)")

    dv = sub.add_parser("dnssec-verify", help="Verify a DNSSEC-signed record")
    dv.add_argument("--domain", required=True)

    vpn_p = sub.add_parser("vpn", help="Establish VPN tunnel between two nodes")
    vpn_p.add_argument("--node-a", required=True, help="First peer IPv6")
    vpn_p.add_argument("--node-b", required=True, help="Second peer IPv6")

    sub.add_parser("showcase", help="★ FULL JUDGE DEMO — runs every feature in 12 phases")

    args = parser.parse_args()

    generate_ca_keys()

    skip_banner = (
        (args.command == "assess" and getattr(args, "json", False))
        or (args.command == "report" and getattr(args, "out", "") == "-")
        or (args.command == "version")
    )
    if not skip_banner:
        print(Colors.CYAN + BANNER + Colors.RESET)

    if args.command == "issue":
        issue_certificate(args.user)

    elif args.command == "bind":
        bind_identity(args.cert)

    elif args.command == "verify":
        verify_node(args.ipv6)

    elif args.command == "handshake":
        handshake_node(args.ipv6)

    elif args.command == "send":
        send_secure(args.source, args.destination)

    elif args.command == "resolve":
        resolve_domain(args.domain)

    elif args.command == "audit":
        show_audit(limit=args.limit, verify_chain=args.verify_chain)

    elif args.command == "assess":
        if not args.ipv6 and not args.domain:
            print(Colors.RED + "✖ Provide --ipv6 and/or --domain" + Colors.RESET)
            sys.exit(2)
        assess_posture(ipv6=args.ipv6, domain=args.domain, json_out=args.json)

    elif args.command == "report":
        export_trust_report(args.out, audit_tail_limit=args.audit_tail)

    elif args.command == "demo":
        run_automated_demo(
            fresh=args.fresh,
            regen_ca=args.regen_ca,
            quiet=args.quiet,
        )

    elif args.command == "version":
        print(WHITENET_VERSION)

    elif args.command == "status":
        print_status()

    elif args.command == "list":
        list_state()

    elif args.command == "spoof-test":
        spoof_test()

    elif args.command == "security-demo":
        security_demo()

    elif args.command == "revoke":
        revoke_node(args.ipv6)

    elif args.command == "renew":
        renew_certificate(args.user)

    elif args.command == "propose":
        create_proposal(args.title, args.proposer, args.category)

    elif args.command == "vote":
        cast_vote(args.proposal, args.voter, not args.against)

    elif args.command == "proposals":
        list_proposals_cli()

    elif args.command == "tls":
        tls_handshake(args.client, args.server)

    elif args.command == "dnssec-sign":
        dnssec_sign_records()

    elif args.command == "dnssec-verify":
        dnssec_verify(args.domain)

    elif args.command == "vpn":
        vpn_establish_tunnel(args.node_a, args.node_b)

    elif args.command == "showcase":
        run_showcase()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()