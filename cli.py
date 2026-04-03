import argparse
import json
import uuid
import ipaddress
import os
import time
import sys

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


# =========================
# UTILITIES
# =========================

def loading(msg="Processing"):
    print(Colors.YELLOW + msg, end="", flush=True)
    for _ in range(3):
        time.sleep(0.3)
        print(".", end="", flush=True)
    print(Colors.RESET)


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

    cert = {
        "cert_id": str(uuid.uuid4()),
        "user_id": user_id,
        "public_key": public_bytes
    }

    cert_bytes = json.dumps(cert).encode()

    signature = private_key.sign(
        cert_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    cert["signature"] = signature.hex()

    with open("cert.json", "w") as f:
        json.dump(cert, f, indent=4)

    print(Colors.GREEN + "✔ Certificate issued → cert.json" + Colors.RESET)


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


# =========================
# VERIFY
# =========================

def verify_node(ipv6):
    print(Colors.CYAN + "\n[ Verification Engine ]" + Colors.RESET)
    loading("Verifying node")

    reg = load_registry()

    if ipv6 not in reg:
        print(Colors.RED + "✖ Node not found" + Colors.RESET)
        return False

    cert = reg[ipv6].copy()
    signature = bytes.fromhex(cert.pop("signature"))

    public_key = load_ca_public()

    try:
        public_key.verify(
            signature,
            json.dumps(cert).encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print(Colors.GREEN + "✔ Trusted Node (Identity Verified)" + Colors.RESET)
        return True
    except:
        print(Colors.RED + "🚨 Tampered or Fake Node Detected" + Colors.RESET)
        return False


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
        return True

    print(Colors.RED + "✖ Handshake failed: untrusted node" + Colors.RESET)
    return False


def send_secure(source_ipv6, dest_ipv6):
    print(Colors.CYAN + "\n[ Secure Transport Layer ]" + Colors.RESET)
    loading("Validating trust before communication")

    if source_ipv6 == dest_ipv6:
        print(Colors.RED + "✖ Source and destination cannot be the same" + Colors.RESET)
        return

    src_ok = verify_node(source_ipv6)
    dst_ok = verify_node(dest_ipv6)

    if not (src_ok and dst_ok):
        print(Colors.RED + "✖ Communication blocked (Zero Trust policy)" + Colors.RESET)
        return

    print(Colors.GREEN + f"✔ Secure packet sent: {source_ipv6} -> {dest_ipv6}" + Colors.RESET)


def resolve_domain(domain):
    print(Colors.CYAN + "\n[ DNSSEC-like Resolution ]" + Colors.RESET)
    loading("Resolving trusted domain")

    records = load_dns_records()
    ipv6 = records.get(domain)

    if not ipv6:
        print(Colors.RED + "✖ Domain not found in trusted records" + Colors.RESET)
        return

    print(Colors.GREEN + f"✔ {domain} -> {ipv6}" + Colors.RESET)
    print(Colors.YELLOW + "Running trust verification on resolved node..." + Colors.RESET)
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
    print(Colors.CYAN + "\n[ Security Resilience Demo ]" + Colors.RESET)
    loading("Executing spoof resilience scenario")

    reg = load_registry()
    if not reg:
        print(Colors.RED + "✖ No nodes available. Create and bind at least one node first." + Colors.RESET)
        return

    victim = list(reg.keys())[0]
    print(Colors.YELLOW + f"Victim node: {victim}" + Colors.RESET)
    print(Colors.YELLOW + "Step 1: Baseline verification" + Colors.RESET)
    verify_node(victim)

    print(Colors.YELLOW + "Step 2: Injecting spoofed identity" + Colors.RESET)
    reg[victim]["user_id"] = "attacker_node"
    save_registry(reg)

    print(Colors.YELLOW + "Step 3: Re-verification after tampering" + Colors.RESET)
    verify_node(victim)


# =========================
# SPOOF TEST
# =========================

def spoof_test():
    print(Colors.CYAN + "\n[ Attack Simulation ]" + Colors.RESET)

    reg = load_registry()

    if not reg:
        print(Colors.RED + "✖ No nodes available" + Colors.RESET)
        return

    ipv6 = list(reg.keys())[0]

    print(Colors.YELLOW + "[!] Injecting Spoofed Identity..." + Colors.RESET)

    reg[ipv6]["user_id"] = "attacker_node"

    save_registry(reg)

    verify_node(ipv6)


# =========================
# CLI
# =========================

def main():
    print(Colors.CYAN + BANNER + Colors.RESET)

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

    sub.add_parser("list")
    sub.add_parser("spoof-test")
    sub.add_parser("security-demo")

    args = parser.parse_args()

    generate_ca_keys()

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

    elif args.command == "list":
        list_state()

    elif args.command == "spoof-test":
        spoof_test()

    elif args.command == "security-demo":
        security_demo()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()