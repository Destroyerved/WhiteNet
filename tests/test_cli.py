"""Isolation tests for WhiteNet core engine (cli.py): each test runs in a temp cwd."""

from datetime import datetime, timedelta, timezone
import json
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


@pytest.fixture
def iso(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WHITENET_QUIET", "1")
    return tmp_path


def test_compute_assess_trusted_after_bind(iso):
    import cli

    cli.generate_ca_keys()
    cli.issue_certificate("alice")
    cli.bind_identity(cli.CERT_FILE)
    out = cli.compute_assess_posture(domain="alice.whitenet.local")
    assert out["verdict"] == "TRUSTED"
    assert out["score"] == 100


def test_verify_certificate_fails_after_tamper(iso):
    import cli

    cli.generate_ca_keys()
    cli.issue_certificate("alice")
    cli.bind_identity(cli.CERT_FILE)
    reg = cli.load_registry()
    ipv6 = next(iter(reg))
    reg[ipv6]["user_id"] = "attacker"
    cli.save_registry(reg)
    assert cli.verify_certificate_payload(reg[ipv6]) is False
    assert cli.verify_node(ipv6) is False


def test_trust_report_contains_meta(iso):
    import cli

    cli.generate_ca_keys()
    cli.issue_certificate("alice")
    cli.bind_identity(cli.CERT_FILE)
    r = cli.build_trust_report(audit_tail_limit=5)
    assert r["meta"]["whitenet_version"] == cli.WHITENET_VERSION
    assert r["meta"]["ca_public_key_sha256"]
    assert len(r["nodes"]) == 1
    assert r["nodes"][0]["assess"]["verdict"] in ("TRUSTED", "WARNING", "BLOCKED")


def test_revoke_and_renew_lifecycle(iso):
    import cli

    cli.generate_ca_keys()
    cli.issue_certificate("alice")
    cli.bind_identity(cli.CERT_FILE)
    dns = cli.load_dns_records()
    alice_ip = dns["alice.whitenet.local"]

    assert cli.verify_node(alice_ip) is True
    cli.revoke_node(alice_ip)
    assert cli.is_revoked(alice_ip) is True
    assert cli.verify_node(alice_ip) is False
    assert cli.handshake_node(alice_ip) is False
    posture = cli.compute_assess_posture(ipv6=alice_ip)
    assert posture["verdict"] == "BLOCKED"
    assert posture["checks"]["revocation"]["ok"] is False

    cli.renew_certificate("alice")
    assert cli.is_revoked(alice_ip) is False
    assert cli.verify_node(alice_ip) is True
    posture_after = cli.compute_assess_posture(domain="alice.whitenet.local")
    assert posture_after["verdict"] == "TRUSTED"


def test_certificate_expiry_blocks_verify_and_flags_assess(iso):
    import cli

    cli.generate_ca_keys()
    cli.issue_certificate("alice")
    cli.bind_identity(cli.CERT_FILE)
    reg = cli.load_registry()
    ipv6 = next(iter(reg))

    # Re-sign certificate with an expired valid_until timestamp
    cert = reg[ipv6].copy()
    cert.pop("signature", None)
    cert["valid_until"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    sig = cli.load_ca_private().sign(
        json.dumps(cert).encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    cert["signature"] = sig.hex()
    reg[ipv6] = cert
    cli.save_registry(reg)

    assert cli.is_cert_expired(cert) is True
    assert cli.verify_node(ipv6) is False
    posture = cli.compute_assess_posture(ipv6=ipv6)
    assert posture["checks"]["expiry"]["ok"] is False
    assert posture["verdict"] in ("WARNING", "BLOCKED")


def test_tls_handshake_and_vpn_tunnel_enforcement(iso):
    import cli

    cli.generate_ca_keys()
    for u in ("alice", "bob"):
        cli.issue_certificate(u)
        cli.bind_identity(cli.CERT_FILE)
    dns = cli.load_dns_records()
    alice_ip = dns["alice.whitenet.local"]
    bob_ip = dns["bob.whitenet.local"]

    tls_sess = cli.tls_handshake(alice_ip, bob_ip)
    assert tls_sess is not None
    assert tls_sess["cipher_suite"] == "TLS_AES_256_GCM_SHA384"

    vpn_tun = cli.vpn_establish_tunnel(alice_ip, bob_ip)
    assert vpn_tun is not None
    assert vpn_tun["encryption"] == "AES-256-GCM"

    # Revoke bob -> TLS and VPN must be rejected
    cli.revoke_node(bob_ip)
    assert cli.tls_handshake(alice_ip, bob_ip) is None
    assert cli.vpn_establish_tunnel(alice_ip, bob_ip) is None


def test_dnssec_sign_verify_and_poison_detection(iso):
    import cli

    cli.generate_ca_keys()
    cli.issue_certificate("alice")
    cli.bind_identity(cli.CERT_FILE)

    signed = cli.dnssec_sign_records()
    assert "alice.whitenet.local" in signed
    assert cli.dnssec_verify("alice.whitenet.local") is True

    # Poison live dns_records.json
    dns = cli.load_dns_records()
    dns["alice.whitenet.local"] = "2001:db8::dead:beef"
    cli.save_dns_records(dns)
    assert cli.dnssec_verify("alice.whitenet.local") is False


def test_trust_based_multi_hop_routing(iso):
    import cli

    cli.generate_ca_keys()
    for u in ("alice", "bob", "charlie"):
        cli.issue_certificate(u)
        cli.bind_identity(cli.CERT_FILE)
    dns = cli.load_dns_records()
    alice_ip = dns["alice.whitenet.local"]
    bob_ip = dns["bob.whitenet.local"]
    charlie_ip = dns["charlie.whitenet.local"]

    res = cli.route_packet(alice_ip, bob_ip, hops=[charlie_ip])
    assert res["ok"] is True
    assert res["status"] == "DELIVERED"
    assert res["hop_count"] == 3
    assert len(res["hops"]) == 3

    # Revoke relay hop charlie -> route must be blocked at hop #2
    cli.revoke_node(charlie_ip)
    blocked_res = cli.route_packet(alice_ip, bob_ip, hops=[charlie_ip])
    assert blocked_res["ok"] is False
    assert blocked_res["status"] == "BLOCKED"
    assert blocked_res["failed_hop"] == charlie_ip
    assert blocked_res["reason"] == "revoked"


def test_governance_proposal_and_voting_resolution(iso):
    import cli

    cli.generate_ca_keys()
    prop = cli.create_proposal("Rotate CA keys quarterly", "alice", "security")
    pid = prop["proposal_id"]

    cli.cast_vote(pid, "bob", vote_for=True)
    # Duplicate vote by bob should be ignored
    cli.cast_vote(pid, "bob", vote_for=True)
    props = cli.load_proposals()
    assert props[0]["votes_for"] == 1
    assert props[0]["status"] == "open"

    cli.cast_vote(pid, "charlie", vote_for=True)
    cli.cast_vote(pid, "dave", vote_for=False)
    props = cli.load_proposals()
    assert props[0]["votes_for"] == 2
    assert props[0]["votes_against"] == 1
    assert props[0]["status"] == "approved"


def test_four_vector_attack_simulation_and_audit_chain(iso):
    import cli

    cli.generate_ca_keys()
    res = cli.attack_simulation("all")
    assert res["ok"] is True
    assert len(res["simulations"]) == 4
    for sim in res["simulations"]:
        assert sim["detected"] is True
        assert sim["verdict"] == "BLOCKED"

    chain_ok, count = cli.verify_audit_chain()
    assert chain_ok is True
    assert count > 0

    # Tamper with an audit event and verify detection
    events = cli.load_audit_log()
    events[0]["action"] = "tampered_action"
    cli.save_audit_log(events)
    chain_ok_after, failed_idx = cli.verify_audit_chain()
    assert chain_ok_after is False
    assert failed_idx == 1
