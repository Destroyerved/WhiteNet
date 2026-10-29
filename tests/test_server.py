"""Integration tests for WhiteNet Flask REST API and static/HTML routes (web/server.py)."""

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WHITENET_QUIET", "1")
    import cli
    from web.server import app

    cli.generate_ca_keys()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health_meta_and_page_routes(client):
    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.get_json()["status"] == "ok"

    r_meta = client.get("/api/meta")
    assert r_meta.status_code == 200
    meta = r_meta.get_json()
    assert meta["audit_chain_ok"] is True
    assert meta["ca_public_key_sha256"]

    assert client.get("/").status_code == 200
    assert client.get("/about").status_code == 200
    assert client.get("/use-cases").status_code == 200
    assert client.get("/attack-matrix").status_code == 200
    assert client.get("/api/does-not-exist").status_code == 404


def test_full_api_workflow_and_routing(client):
    for user in ("alice", "bob", "charlie"):
        r = client.post("/api/quick-onboard", json={"user_id": user})
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    rep = client.get("/api/report").get_json()
    assert len(rep["nodes"]) == 3
    ips = {n["user_id"]: n["ipv6"] for n in rep["nodes"]}

    assert client.post("/api/verify", json={"ipv6": ips["alice"]}).status_code == 200
    assert client.post("/api/handshake", json={"ipv6": ips["bob"]}).status_code == 200
    assert client.post("/api/send", json={"source": ips["alice"], "destination": ips["bob"]}).status_code == 200
    assert client.post("/api/resolve", json={"domain": "alice.whitenet.local"}).status_code == 200

    assess = client.post("/api/assess", json={"domain": "alice.whitenet.local"}).get_json()
    assert assess["verdict"] == "TRUSTED"

    assert client.post("/api/tls-handshake", json={"client": ips["alice"], "server": ips["bob"]}).status_code == 200
    assert client.post("/api/vpn-tunnel", json={"node_a": ips["alice"], "node_b": ips["bob"]}).status_code == 200
    assert client.post("/api/dnssec-sign", json={}).status_code == 200
    assert client.post("/api/dnssec-verify", json={"domain": "alice.whitenet.local"}).status_code == 200

    route_res = client.post(
        "/api/route",
        json={"source": ips["alice"], "destination": ips["bob"], "hops": [ips["charlie"]]},
    ).get_json()
    assert route_res["ok"] is True
    assert route_res["route"]["status"] == "DELIVERED"
    assert route_res["route"]["hop_count"] == 3

    topo = client.get("/api/topology").get_json()
    assert len(topo["nodes"]) == 3
    assert len(topo["edges"]) >= 2


def test_governance_and_revocation_endpoints(client):
    client.post("/api/quick-onboard", json={"user_id": "alice"})
    rep = client.get("/api/report").get_json()
    alice_ip = rep["nodes"][0]["ipv6"]

    assert client.post("/api/revoke", json={"ipv6": alice_ip}).status_code == 200
    assert client.post("/api/assess", json={"ipv6": alice_ip}).get_json()["verdict"] == "BLOCKED"
    assert client.post("/api/renew", json={"user_id": "alice"}).status_code == 200
    assert client.post("/api/assess", json={"domain": "alice.whitenet.local"}).get_json()["verdict"] == "TRUSTED"

    assert client.post("/api/governance/propose", json={"title": "Upgrade policy", "proposer": "alice"}).status_code == 200
    props = client.get("/api/governance/proposals").get_json()
    assert len(props) == 1
    pid = props[0]["proposal_id"]

    for voter in ("bob", "charlie", "dave"):
        assert client.post("/api/governance/vote", json={"proposal_id": pid, "voter": voter}).status_code == 200
    props_after = client.get("/api/governance/proposals").get_json()
    assert props_after[0]["status"] == "approved"


def test_attack_simulations_and_sector_demos(client):
    atk = client.post("/api/attack-sim", json={"type": "all"})
    assert atk.status_code == 200
    atk_data = atk.get_json()
    assert atk_data["ok"] is True
    assert len(atk_data["simulations"]) == 4

    for endpoint in (
        "/api/banking-demo",
        "/api/scammer-demo",
        "/api/agent-verify-demo",
        "/api/egov-demo",
        "/api/health-demo",
        "/api/corporate-demo",
    ):
        res = client.post(endpoint, json={})
        assert res.status_code == 200
        assert res.get_json()["ok"] is True

    audit = client.get("/api/audit?limit=30&verify_chain=true").get_json()
    assert audit["chain_verified"] is True
