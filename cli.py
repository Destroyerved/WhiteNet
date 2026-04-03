import argparse
import json
import uuid
import ipaddress
import os
import time
import base64
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding


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


def bind_identity(cert_file):
    print(Colors.CYAN + "\n[ Identity Binding ]" + Colors.RESET)
    loading("Assigning IPv6")

    reg = load_registry()

    with open(cert_file) as f:
        cert = json.load(f)

    ipv6 = generate_ipv6()
    reg[ipv6] = cert

    save_registry(reg)

    print(Colors.GREEN + f"✔ IPv6 Assigned → {ipv6}" + Colors.RESET)


# =========================
# VERIFY
# =========================

def verify_node(ipv6):
    print(Colors.CYAN + "\n[ Verification Engine ]" + Colors.RESET)
    loading("Verifying node")

    reg = load_registry()

    if ipv6 not in reg:
        print(Colors.RED + "✖ Node not found" + Colors.RESET)
        return

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
    except:
        print(Colors.RED + "🚨 Tampered or Fake Node Detected" + Colors.RESET)


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

def handshake(ipv6):
    print(Colors.CYAN + "\n[ TLS Handshake Simulation ]" + Colors.RESET)
    loading("Initiating handshake")

    reg = load_registry()

    if ipv6 not in reg:
        print(Colors.RED + "✖ Node not found" + Colors.RESET)
        return

    cert = reg[ipv6]

    # Step 1: Verify Certificate
    print(Colors.YELLOW + "[1] Verifying Certificate..." + Colors.RESET)
    cert_copy = cert.copy()
    signature = bytes.fromhex(cert_copy.pop("signature"))

    public_ca = load_ca_public()

    try:
        public_ca.verify(
            signature,
            json.dumps(cert_copy).encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print(Colors.GREEN + "✔ Certificate Valid" + Colors.RESET)
    except:
        print(Colors.RED + "✖ Certificate Invalid" + Colors.RESET)
        return

    # Step 2: Challenge-Response
    print(Colors.YELLOW + "[2] Performing Challenge-Response..." + Colors.RESET)

    challenge = os.urandom(32)

    # ⚠️ Simulation: we don’t store user private key
    # So we simulate correct behavior

    print(Colors.GREEN + "✔ Challenge Verified (Simulated Ownership)" + Colors.RESET)

    print(Colors.CYAN + "🔐 Secure Channel Established\n" + Colors.RESET)

def verify_internal(ipv6):
    reg = load_registry()

    if ipv6 not in reg:
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
        return True
    except:
        return False
def secure_send(sender, receiver):
    print(Colors.CYAN + "\n[ Secure Communication ]" + Colors.RESET)

    reg = load_registry()

    if sender not in reg:
        print(Colors.RED + f"✖ Sender {sender} not found" + Colors.RESET)
        return

    if receiver not in reg:
        print(Colors.RED + f"✖ Receiver {receiver} not found" + Colors.RESET)
        return

    print(Colors.YELLOW + "[*] Verifying sender..." + Colors.RESET)
    valid_sender = verify_internal(sender)

    print(Colors.YELLOW + "[*] Verifying receiver..." + Colors.RESET)
    valid_receiver = verify_internal(receiver)

    if valid_sender and valid_receiver:
        print(Colors.GREEN + "✔ Secure Packet Sent Successfully" + Colors.RESET)
        print(Colors.CYAN + f"📡 {sender} → {receiver}" + Colors.RESET)
    else:
        print(Colors.RED + "🚫 Communication Blocked (Zero Trust Enforcement)" + Colors.RESET)
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

    sub.add_parser("spoof-test")
    handshake_cmd = sub.add_parser("handshake")
    handshake_cmd.add_argument("--ipv6", required=True)

    send_cmd = sub.add_parser("send")
    send_cmd.add_argument("--from", dest="sender", required=True)
    send_cmd.add_argument("--to", dest="receiver", required=True)

    args = parser.parse_args()

    generate_ca_keys()

    if args.command == "issue":
        issue_certificate(args.user)

    elif args.command == "bind":
        bind_identity(args.cert)

    elif args.command == "verify":
        verify_node(args.ipv6)

    elif args.command == "spoof-test":
        spoof_test()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

    