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


def _capture(fn, *args, **kwargs):
    buf = io.StringIO()
    prev = os.environ.get("WHITENET_QUIET")
    os.environ["WHITENET_QUIET"] = "1"
    try:
        with redirect_stdout(buf):
            fn(*args, **kwargs)
        return {"ok": True, "log": buf.getvalue()}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if prev is None:
            os.environ.pop("WHITENET_QUIET", None)
        else:
            os.environ["WHITENET_QUIET"] = prev


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


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    if path.startswith("api"):
        return jsonify({"error": "not found"}), 404
    if app.static_folder and os.path.exists(app.static_folder):
        target = os.path.join(app.static_folder, path)
        if path and os.path.isfile(target):
            return send_from_directory(app.static_folder, path)
        index = os.path.join(app.static_folder, "index.html")
        if os.path.isfile(index):
            return send_from_directory(app.static_folder, "index.html")
    return (
        "<html><body style='font-family:system-ui;padding:2rem;background:#0a0a0f;color:#e2e8f0'>"
        "<h1>WhiteNet Web</h1><p>Build the React app first:</p>"
        "<pre style='background:#111;padding:1rem;border-radius:8px'>cd web/client && npm install && npm run build</pre>"
        "<p>Then run: <code>python web/server.py</code></p>"
        "<p>API is live — try <a href='/api/meta' style='color:#38bdf8'>/api/meta</a></p>"
        "</body></html>",
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )


if __name__ == "__main__":
    cli.generate_ca_keys()
    print(f"WhiteNet web — http://127.0.0.1:5050  (project root: {PROJECT_ROOT})")
    app.run(host="127.0.0.1", port=5050, debug=False)
