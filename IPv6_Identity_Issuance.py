import uuid
import hashlib
import secrets

# =========================
# CRYPTO UTILITIES
# =========================

def generate_keys():
    private_key = secrets.token_hex(32)
    public_key = hashlib.sha256(private_key.encode()).hexdigest()
    return public_key, private_key


def sign_data(data, private_key):
    return hashlib.sha256((data + private_key).encode()).hexdigest()


def verify_signature(data, signature, private_key):
    return sign_data(data, private_key) == signature


# =========================
# CERTIFICATE AUTHORITY
# =========================

class CertificateAuthority:
    def __init__(self):
        self.issued_certs = {}

    def issue_certificate(self, user_id, public_key):
        cert_id = str(uuid.uuid4())

        cert_data = f"{user_id}:{public_key}:{cert_id}"
        signature = hashlib.sha256(cert_data.encode()).hexdigest()

        certificate = {
            "cert_id": cert_id,
            "user_id": user_id,
            "public_key": public_key,
            "signature": signature
        }

        self.issued_certs[cert_id] = certificate
        return certificate


# =========================
# IPv6 ALLOCATOR
# =========================

def generate_ipv6():
    return "2001:" + ":".join(
        format(secrets.randbits(16), '04x') for _ in range(7)
    )


# =========================
# IDENTITY BINDING
# =========================

class WhiteNetRegistry:
    def __init__(self):
        self.registry = {}

    def bind_identity(self, certificate, ipv6):
        self.registry[ipv6] = certificate

    def get_certificate(self, ipv6):
        return self.registry.get(ipv6, None)


# =========================
# VERIFICATION ENGINE
# =========================

def verify_node(ipv6, registry):
    cert = registry.get_certificate(ipv6)

    if not cert:
        return False, "❌ No identity bound"

    # recompute hash
    data = f"{cert['user_id']}:{cert['public_key']}:{cert['cert_id']}"
    expected_signature = hashlib.sha256(data.encode()).hexdigest()

    if cert['signature'] != expected_signature:
        return False, "🚨 Tampered certificate"

    return True, "✅ Verified Trusted Node"


# =========================
# ATTACK SIMULATION
# =========================

def spoof_attempt(ipv6, fake_cert, registry):
    print("\n[ATTACK] Trying to spoof identity...")

    registry.registry[ipv6] = fake_cert  # attacker tries override

    valid, msg = verify_node(ipv6, registry)
    print(msg)


# =========================
# MAIN DEMO
# =========================

if __name__ == "__main__":
    print("🚀 WhiteNet Identity Simulation\n")

    ca = CertificateAuthority()
    registry = WhiteNetRegistry()

    # Step 1: Generate keys
    public_key, private_key = generate_keys()

    # Step 2: Issue certificate
    cert = ca.issue_certificate("user_123", public_key)

    # Step 3: Assign IPv6
    ipv6 = generate_ipv6()

    # Step 4: Bind identity
    registry.bind_identity(cert, ipv6)

    print(f"Assigned IPv6: {ipv6}")
    print(f"Certificate ID: {cert['cert_id']}")

    # Step 5: Verify node
    valid, msg = verify_node(ipv6, registry)
    print("\nVerification:", msg)

    # Step 6: Simulate spoof attack
    fake_cert = cert.copy()
    fake_cert["user_id"] = "attacker_999"

    spoof_attempt(ipv6, fake_cert, registry)