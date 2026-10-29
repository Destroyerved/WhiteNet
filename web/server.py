"""
WhiteNet web dashboard — Flask API + static React build.
Run from repo root:  python web/server.py
Dev (two terminals):  python web/server.py   &&   cd web/client && npm run dev
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

WEB_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(WEB_DIR)
DIST_DIR = os.path.join(WEB_DIR, "client", "dist")

os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import cli  # noqa: E402

app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")
CORS(app)

# Ensure CA keys exist when loaded by gunicorn (not just __main__)
cli.generate_ca_keys()


def _capture(fn, *args, **kwargs):
    buf = io.StringIO()
    prev = os.environ.get("WHITENET_QUIET")
    os.environ["WHITENET_QUIET"] = "1"
    try:
        with redirect_stdout(buf):
            res = fn(*args, **kwargs)
        out = {"ok": True, "log": buf.getvalue()}
        if res is not None:
            out["result"] = res
        return out
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if prev is None:
            os.environ.pop("WHITENET_QUIET", None)
        else:
            os.environ["WHITENET_QUIET"] = prev


@app.route("/about")
def about_page():
    return send_from_directory(PROJECT_ROOT, "about.html")


@app.route("/use-cases")
def use_cases_page():
    return send_from_directory(PROJECT_ROOT, "use_cases.html")


@app.route("/attack-matrix")
@app.route("/WhiteNet_Attack_Defense_Matrix.html")
def attack_matrix_page():
    return send_from_directory(PROJECT_ROOT, "WhiteNet_Attack_Defense_Matrix.html")


@app.route("/api/banking-demo", methods=["POST"])
def banking_demo():
    """Full banking KYC scenario: reset → issue/bind customer → assess trust."""
    cli.demo_reset_data_files(regen_ca=True)
    cli.generate_ca_keys()
    results = {"steps": []}
    # Issue + bind customer
    _capture(cli.issue_certificate, "customer_ankit")
    _capture(cli.bind_identity, cli.CERT_FILE)
    dns = cli.load_dns_records()
    cust_ip = dns.get("customer_ankit.whitenet.local")
    results["steps"].append({"action": "onboard_customer", "user": "customer_ankit", "ipv6": cust_ip, "ok": bool(cust_ip)})
    # Issue + bind bank server
    _capture(cli.issue_certificate, "securebank_server")
    _capture(cli.bind_identity, cli.CERT_FILE)
    bank_ip = dns.get("securebank_server.whitenet.local") or cli.load_dns_records().get("securebank_server.whitenet.local")
    results["steps"].append({"action": "onboard_bank", "user": "securebank_server", "ipv6": bank_ip, "ok": bool(bank_ip)})
    # Assess customer trust
    posture = cli.compute_assess_posture(domain="customer_ankit.whitenet.local")
    results["steps"].append({"action": "assess_customer", "posture": posture})
    # TLS handshake
    if cust_ip and bank_ip:
        _capture(cli.tls_handshake, cust_ip, bank_ip)
        results["steps"].append({"action": "tls_session", "ok": True})
    results["ok"] = True
    return jsonify(results)


@app.route("/api/scammer-demo", methods=["POST"])
def scammer_demo():
    """Simulate a scammer: tamper registry → re-verify → show BLOCKED."""
    reg = cli.load_registry()
    if not reg:
        return jsonify({"ok": False, "error": "No nodes. Run banking-demo first."}), 400
    victim_ip = list(reg.keys())[0]
    victim_user = reg[victim_ip].get("user_id", "unknown")
    # Verify before tamper
    before = cli.compute_assess_posture(ipv6=victim_ip)
    # Tamper
    reg[victim_ip]["user_id"] = "scammer_fake_id"
    cli.save_registry(reg)
    # Verify after tamper
    after = cli.compute_assess_posture(ipv6=victim_ip)
    # Restore
    reg = cli.load_registry()
    reg[victim_ip]["user_id"] = victim_user
    cli.save_registry(reg)
    return jsonify({"ok": True, "victim": victim_user, "ipv6": victim_ip,
                     "before": before, "after": after})


@app.route("/api/agent-verify-demo", methods=["POST"])
def agent_verify_demo():
    """Register two bank agents, verify both, then simulate impersonator on one."""
    cli.demo_reset_data_files(regen_ca=True)
    cli.generate_ca_keys()
    agents = ["agent_raj", "agent_priya"]
    results = {"agents": [], "impersonator": {}}
    for a in agents:
        _capture(cli.issue_certificate, a)
        _capture(cli.bind_identity, cli.CERT_FILE)
    dns = cli.load_dns_records()
    for a in agents:
        ip = dns.get(f"{a}.whitenet.local")
        posture = cli.compute_assess_posture(domain=f"{a}.whitenet.local")
        results["agents"].append({"user": a, "ipv6": ip, "posture": posture})
    # Impersonator attack on agent_raj
    raj_ip = dns.get("agent_raj.whitenet.local")
    if raj_ip:
        reg = cli.load_registry()
        reg[raj_ip]["user_id"] = "impersonator_xyz"
        cli.save_registry(reg)
        blocked = cli.compute_assess_posture(ipv6=raj_ip)
        results["impersonator"] = {"target": "agent_raj", "ipv6": raj_ip, "posture": blocked}
        # Restore
        reg = cli.load_registry()
        reg[raj_ip]["user_id"] = "agent_raj"
        cli.save_registry(reg)
    results["ok"] = True
    return jsonify(results)


@app.route("/api/egov-demo", methods=["POST"])
def egov_demo():
    """E-Governance scenario: citizen + portal onboarding, DNSSEC signing & verification, posture, TLS 1.3."""
    cli.demo_reset_data_files(regen_ca=True)
    cli.generate_ca_keys()
    _capture(cli.issue_certificate, "citizen_priya")
    _capture(cli.bind_identity, cli.CERT_FILE)
    _capture(cli.issue_certificate, "egov_portal_server")
    _capture(cli.bind_identity, cli.CERT_FILE)
    dns = cli.load_dns_records()
    cit_ip = dns.get("citizen_priya.whitenet.local")
    portal_ip = dns.get("egov_portal_server.whitenet.local")
    _capture(cli.dnssec_sign_records)
    dnssec_r = _capture(cli.dnssec_verify, "citizen_priya.whitenet.local")
    posture = cli.compute_assess_posture(domain="citizen_priya.whitenet.local")
    if cit_ip and portal_ip:
        _capture(cli.tls_handshake, cit_ip, portal_ip)
    return jsonify({
        "ok": True,
        "citizen": "citizen_priya",
        "citizen_ipv6": cit_ip,
        "portal_ipv6": portal_ip,
        "dnssec_verified": bool(dnssec_r.get("result", True)),
        "posture": posture,
        "steps": [
            {"action": "onboard_citizen", "user": "citizen_priya", "ipv6": cit_ip, "ok": bool(cit_ip)},
            {"action": "onboard_portal", "user": "egov_portal_server", "ipv6": portal_ip, "ok": bool(portal_ip)},
            {"action": "dnssec_sign_verify", "domain": "citizen_priya.whitenet.local", "ok": bool(dnssec_r.get("result", True))},
            {"action": "assess_citizen", "posture": posture},
            {"action": "tls_session", "ok": bool(cit_ip and portal_ip)},
        ],
    })


@app.route("/api/health-demo", methods=["POST"])
def health_demo():
    """Healthcare scenario: verified cardiologist TLS access + blocked revoked nurse."""
    cli.demo_reset_data_files(regen_ca=True)
    cli.generate_ca_keys()
    for u in ("dr_sharma", "hospital_records_server", "nurse_unverified"):
        _capture(cli.issue_certificate, u)
        _capture(cli.bind_identity, cli.CERT_FILE)
    dns = cli.load_dns_records()
    doc_ip = dns.get("dr_sharma.whitenet.local")
    hosp_ip = dns.get("hospital_records_server.whitenet.local")
    nurse_ip = dns.get("nurse_unverified.whitenet.local")
    doc_posture = cli.compute_assess_posture(domain="dr_sharma.whitenet.local")
    if doc_ip and hosp_ip:
        _capture(cli.tls_handshake, doc_ip, hosp_ip)
    if nurse_ip:
        _capture(cli.revoke_node, nurse_ip)
    nurse_posture = cli.compute_assess_posture(ipv6=nurse_ip) if nurse_ip else {"verdict": "BLOCKED", "score": 0}
    return jsonify({
        "ok": True,
        "doctor": {"user": "dr_sharma", "ipv6": doc_ip, "posture": doc_posture},
        "hospital_ipv6": hosp_ip,
        "unauthorized": {"user": "nurse_unverified", "ipv6": nurse_ip, "posture": nurse_posture},
        "steps": [
            {"action": "onboard_doctor", "user": "dr_sharma", "ipv6": doc_ip, "posture": doc_posture},
            {"action": "onboard_hospital", "user": "hospital_records_server", "ipv6": hosp_ip},
            {"action": "tls_session", "ok": bool(doc_ip and hosp_ip)},
            {"action": "block_unauthorized", "user": "nurse_unverified", "ipv6": nurse_ip, "posture": nurse_posture},
        ],
    })


@app.route("/api/corporate-demo", methods=["POST"])
def corporate_demo():
    """Corporate Zero Trust scenario: employee VPN tunnel + revocation block upon termination."""
    cli.demo_reset_data_files(regen_ca=True)
    cli.generate_ca_keys()
    for u in ("employee_vikram", "corporate_server"):
        _capture(cli.issue_certificate, u)
        _capture(cli.bind_identity, cli.CERT_FILE)
    dns = cli.load_dns_records()
    emp_ip = dns.get("employee_vikram.whitenet.local")
    srv_ip = dns.get("corporate_server.whitenet.local")
    before = cli.compute_assess_posture(domain="employee_vikram.whitenet.local")
    tunnel_res = _capture(cli.vpn_establish_tunnel, emp_ip, srv_ip) if (emp_ip and srv_ip) else {}
    if emp_ip:
        _capture(cli.revoke_node, emp_ip)
    after = cli.compute_assess_posture(ipv6=emp_ip) if emp_ip else {"verdict": "BLOCKED", "score": 0}
    return jsonify({
        "ok": True,
        "employee": "employee_vikram",
        "employee_ipv6": emp_ip,
        "server_ipv6": srv_ip,
        "before": before,
        "after": after,
        "tunnel": tunnel_res.get("result"),
        "steps": [
            {"action": "onboard_employee", "user": "employee_vikram", "ipv6": emp_ip, "posture": before},
            {"action": "vpn_tunnel", "ok": bool(tunnel_res.get("result"))},
            {"action": "terminate_revoke", "user": "employee_vikram", "ipv6": emp_ip, "posture": after},
        ],
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "version": cli.WHITENET_VERSION})


@app.route("/api/meta")
def meta():
    ok, marker = cli.verify_audit_chain()
    return jsonify(
        {
            "version": cli.WHITENET_VERSION,
            "ca_public_key_sha256": cli.ca_public_key_fingerprint_sha256(),
            "cwd": os.getcwd(),
            "audit_chain_ok": ok,
            "audit_chain_failed_at": None if ok else marker,
            "registry_nodes": len(cli.load_registry()),
            "dns_entries": len(cli.load_dns_records()),
            "audit_events": len(cli.load_audit_log()),
            "revoked_count": len(cli.load_revoked()),
            "proposals_count": len(cli.load_proposals()),
            "tls_sessions": len(cli.load_tls_sessions()),
            "vpn_tunnels": len(cli.load_vpn_tunnels()),
        }
    )


@app.route("/api/report")
def report():
    try:
        tail = int(request.args.get("audit_tail", 50))
    except ValueError:
        tail = 50
    return jsonify(cli.build_trust_report(audit_tail_limit=tail))


@app.route("/api/assess", methods=["POST"])
def assess():
    data = request.get_json(silent=True) or {}
    out = cli.compute_assess_posture(ipv6=data.get("ipv6"), domain=data.get("domain"))
    return jsonify(out)


@app.route("/api/issue", methods=["POST"])
def issue():
    data = request.get_json(silent=True) or {}
    uid = (data.get("user_id") or data.get("user") or "").strip()
    if not uid:
        return jsonify({"ok": False, "error": "user_id required"}), 400
    r = _capture(cli.issue_certificate, uid)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/bind", methods=["POST"])
def bind():
    data = request.get_json(silent=True) or {}
    path = (data.get("cert_path") or cli.CERT_FILE).strip()
    if not path:
        return jsonify({"ok": False, "error": "cert_path required"}), 400
    r = _capture(cli.bind_identity, path)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/quick-onboard", methods=["POST"])
def quick_onboard():
    data = request.get_json(silent=True) or {}
    uid = (data.get("user_id") or "").strip()
    if not uid:
        return jsonify({"ok": False, "error": "user_id required"}), 400
    r1 = _capture(cli.issue_certificate, uid)
    if not r1.get("ok"):
        return jsonify(r1), 500
    r2 = _capture(cli.bind_identity, cli.CERT_FILE)
    log = (r1.get("log", "") + "\n" + r2.get("log", "")).strip()
    return jsonify({"ok": r2.get("ok", False), "log": log})


@app.route("/api/verify", methods=["POST"])
def verify():
    data = request.get_json(silent=True) or {}
    ipv6 = (data.get("ipv6") or "").strip()
    if not ipv6:
        return jsonify({"ok": False, "error": "ipv6 required"}), 400
    r = _capture(cli.verify_node, ipv6)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/handshake", methods=["POST"])
def handshake():
    data = request.get_json(silent=True) or {}
    ipv6 = (data.get("ipv6") or "").strip()
    if not ipv6:
        return jsonify({"ok": False, "error": "ipv6 required"}), 400
    r = _capture(cli.handshake_node, ipv6)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/send", methods=["POST"])
def send():
    data = request.get_json(silent=True) or {}
    src = (data.get("source") or data.get("from") or "").strip()
    dst = (data.get("destination") or data.get("to") or "").strip()
    if not src or not dst:
        return jsonify({"ok": False, "error": "source and destination required"}), 400
    r = _capture(cli.send_secure, src, dst)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/resolve", methods=["POST"])
def resolve():
    data = request.get_json(silent=True) or {}
    domain = (data.get("domain") or "").strip()
    if not domain:
        return jsonify({"ok": False, "error": "domain required"}), 400
    r = _capture(cli.resolve_domain, domain)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/audit")
def audit():
    try:
        limit = int(request.args.get("limit", 25))
    except ValueError:
        limit = 25
    verify_chain = request.args.get("verify_chain", "false").lower() in ("1", "true", "yes")
    events = cli.load_audit_log()
    recent = events[-limit:] if limit > 0 else events
    ok, marker = cli.verify_audit_chain() if verify_chain else (True, 0)
    return jsonify(
        {
            "total": len(events),
            "showing": len(recent),
            "chain_verified": ok,
            "chain_failed_at": None if ok else marker,
            "events": recent,
        }
    )


@app.route("/api/revoke", methods=["POST"])
def revoke():
    data = request.get_json(silent=True) or {}
    ipv6 = (data.get("ipv6") or "").strip()
    if not ipv6:
        return jsonify({"ok": False, "error": "ipv6 required"}), 400
    r = _capture(cli.revoke_node, ipv6)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/renew", methods=["POST"])
def renew():
    data = request.get_json(silent=True) or {}
    uid = (data.get("user_id") or "").strip()
    if not uid:
        return jsonify({"ok": False, "error": "user_id required"}), 400
    r = _capture(cli.renew_certificate, uid)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/demo", methods=["POST"])
def demo():
    data = request.get_json(silent=True) or {}
    r = _capture(
        cli.run_automated_demo,
        bool(data.get("fresh")),
        bool(data.get("regen_ca")),
        bool(data.get("quiet", True)),
    )
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/security-demo", methods=["POST"])
def security_demo():
    r = _capture(cli.security_demo)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/spoof-test", methods=["POST"])
def spoof_test():
    r = _capture(cli.spoof_test)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/governance/proposals")
def governance_proposals():
    return jsonify(cli.load_proposals())


@app.route("/api/governance/propose", methods=["POST"])
def governance_propose():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    proposer = (data.get("proposer") or "").strip()
    if not title or not proposer:
        return jsonify({"ok": False, "error": "title and proposer required"}), 400
    r = _capture(cli.create_proposal, title, proposer, data.get("category", "policy"))
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/governance/vote", methods=["POST"])
def governance_vote():
    data = request.get_json(silent=True) or {}
    pid = (data.get("proposal_id") or "").strip()
    voter = (data.get("voter") or "").strip()
    if not pid or not voter:
        return jsonify({"ok": False, "error": "proposal_id and voter required"}), 400
    r = _capture(cli.cast_vote, pid, voter, not data.get("against", False))
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/tls-handshake", methods=["POST"])
def tls_handshake_api():
    data = request.get_json(silent=True) or {}
    c = (data.get("client") or "").strip()
    s = (data.get("server") or "").strip()
    if not c or not s:
        return jsonify({"ok": False, "error": "client and server required"}), 400
    r = _capture(cli.tls_handshake, c, s)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/dnssec-sign", methods=["POST"])
def dnssec_sign_api():
    r = _capture(cli.dnssec_sign_records)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/dnssec-verify", methods=["POST"])
def dnssec_verify_api():
    data = request.get_json(silent=True) or {}
    domain = (data.get("domain") or "").strip()
    if not domain:
        return jsonify({"ok": False, "error": "domain required"}), 400
    r = _capture(cli.dnssec_verify, domain)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/vpn-tunnel", methods=["POST"])
def vpn_tunnel_api():
    data = request.get_json(silent=True) or {}
    a = (data.get("node_a") or "").strip()
    b = (data.get("node_b") or "").strip()
    if not a or not b:
        return jsonify({"ok": False, "error": "node_a and node_b required"}), 400
    r = _capture(cli.vpn_establish_tunnel, a, b)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/route", methods=["POST"])
def route_api():
    data = request.get_json(silent=True) or {}
    src = (data.get("source") or data.get("from") or "").strip()
    dst = (data.get("destination") or data.get("to") or "").strip()
    hops = data.get("hops")
    payload = (data.get("payload") or "SECURE_PACKET").strip()
    if not src or not dst:
        return jsonify({"ok": False, "error": "source and destination required"}), 400
    r = _capture(cli.route_packet, src, dst, hops=hops, payload=payload)
    route_res = r.get("result") or {}
    return jsonify({
        "ok": r.get("ok", False) and route_res.get("ok", False),
        "log": r.get("log", ""),
        "route": route_res,
    }), 200 if r.get("ok") else 500


@app.route("/api/attack-sim", methods=["POST"])
def attack_sim_api():
    data = request.get_json(silent=True) or {}
    atype = (data.get("type") or "all").strip().lower()
    r = _capture(cli.attack_simulation, atype)
    res = r.get("result") or {}
    if not r.get("ok") or res.get("ok") is False:
        return jsonify({"ok": False, "error": res.get("error") or r.get("error", "attack simulation failed")}), 400
    return jsonify({
        "ok": True,
        "type": res.get("type", atype),
        "simulations": res.get("simulations", []),
        "log": r.get("log", ""),
    })


@app.route("/api/showcase", methods=["POST"])
def showcase_api():
    r = _capture(cli.run_showcase)
    return jsonify(r), 200 if r.get("ok") else 500


@app.route("/api/topology")
def topology():
    reg = cli.load_registry()
    dns = cli.load_dns_records()
    revoked = cli.load_revoked()
    tunnels = cli.load_vpn_tunnels()
    tls_sess = cli.load_tls_sessions()
    nodes = []
    for ipv6, cert in reg.items():
        nodes.append({
            "ipv6": ipv6,
            "user_id": cert.get("user_id", "unknown"),
            "revoked": ipv6 in revoked,
            "assess": cli.compute_assess_posture(ipv6=ipv6),
        })
    edges = []
    for tid, t in tunnels.items():
        edges.append({"type": "vpn", "id": tid, "a": t["node_a"], "b": t["node_b"]})
    for sid, s in tls_sess.items():
        edges.append({"type": "tls", "id": sid, "a": s["client_ipv6"], "b": s["server_ipv6"]})
    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    # Explicit page routes
    if path == "about" or path == "about.html":
        return send_from_directory(PROJECT_ROOT, "about.html")
    if path == "use-cases" or path == "use_cases.html":
        return send_from_directory(PROJECT_ROOT, "use_cases.html")
    if path == "attack-matrix" or path == "WhiteNet_Attack_Defense_Matrix.html":
        return send_from_directory(PROJECT_ROOT, "WhiteNet_Attack_Defense_Matrix.html")
    if path.startswith("api"):
        return jsonify({"error": "not found"}), 404
    # Serve React dashboard from dist
    if app.static_folder and os.path.exists(app.static_folder):
        target = os.path.join(app.static_folder, path)
        if path and os.path.isfile(target):
            return send_from_directory(app.static_folder, path)
        index = os.path.join(app.static_folder, "index.html")
        if os.path.isfile(index):
            return send_from_directory(app.static_folder, "index.html")
    # Fallback landing — links to all pages
    return (
        "<html><head><title>WhiteNet</title>"
        "<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:#030508;color:#e2e8f0;min-height:100vh;display:flex;align-items:center;justify-content:center}"
        ".wrap{text-align:center;max-width:720px;padding:2rem}"
        "h1{font-size:2.5rem;margin-bottom:.5rem;background:linear-gradient(135deg,#0ff,#00a8ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}"
        "p{color:#7a9ab8;margin-bottom:2rem;font-size:1.1rem}"
        ".cards{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}"
        "a{display:block;padding:24px 16px;background:rgba(0,255,255,.04);border:1px solid rgba(0,255,255,.15);border-radius:12px;color:#0ff;text-decoration:none;transition:all .3s;font-weight:600}"
        "a:hover{background:rgba(0,255,255,.1);border-color:rgba(0,255,255,.4);box-shadow:0 0 20px rgba(0,255,255,.1)}"
        "a span{display:block;font-size:.75rem;color:#5a7a94;margin-top:6px;font-weight:400}"
        "</style></head><body>"
        "<div class='wrap'>"
        "<h1>WhiteNet</h1>"
        f"<p>Identity-First Zero Trust Network — v{cli.WHITENET_VERSION}</p>"
        "<div class='cards'>"
        "<a href='/about'>📄 About<span>Project overview & architecture</span></a>"
        "<a href='/use-cases'>🏦 Use Cases<span>Banking, E-Gov, Healthcare & Corporate</span></a>"
        "<a href='/attack-matrix'>⚔️ Attack Matrix<span>Spoofing, MITM, Sybil & Forgery Defense</span></a>"
        "<a href='/api/meta'>⚡ API<span>Live API status endpoint</span></a>"
        "</div></div></body></html>",
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )


if __name__ == "__main__":
    cli.generate_ca_keys()
    port = int(os.environ.get("PORT", 5050))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"WhiteNet web — http://{host}:{port}  (project root: {PROJECT_ROOT})")
    app.run(host=host, port=port, debug=False)
