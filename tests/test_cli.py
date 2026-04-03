"""Isolation tests: each test uses a temp cwd so registry/CA files do not touch the repo."""

import pytest


@pytest.fixture
def iso(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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


def test_trust_report_contains_meta(iso):
    import cli

    cli.generate_ca_keys()
    cli.issue_certificate("alice")
    cli.bind_identity(cli.CERT_FILE)
    r = cli.build_trust_report(audit_tail_limit=5)
    assert r["meta"]["whitenet_version"]
    assert r["meta"]["ca_public_key_sha256"]
    assert len(r["nodes"]) == 1
    assert r["nodes"][0]["assess"]["verdict"] in ("TRUSTED", "WARNING", "BLOCKED")
