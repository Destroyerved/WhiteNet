import { useCallback, useEffect, useState, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";

/* ──────── helpers ──────── */
const api = (path, opts = {}) =>
  fetch(path, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });

const TABS = ["Dashboard", "Topology", "Actions", "Governance", "Audit"];

/* ──────── reusable ──────── */
function StatCard({ label, value, sub, icon, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, type: "spring", stiffness: 120 }}
      className="glass-panel p-5 relative overflow-hidden group"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-violet-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      <p className="text-xs uppercase tracking-widest text-slate-500 font-medium flex items-center gap-1.5">
        {icon && <span>{icon}</span>}
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold font-display text-white tabular-nums">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500 font-mono truncate">{sub}</p>}
    </motion.div>
  );
}

function Btn({ children, onClick, variant = "primary", disabled, small }) {
  const base = `${small ? "px-3 py-1.5 text-xs" : "px-4 py-2.5 text-sm"} rounded-xl font-medium transition-all duration-300 font-display`;
  const styles =
    variant === "primary"
      ? "bg-gradient-to-r from-cyan-500 to-sky-600 text-white shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98]"
      : variant === "danger"
        ? "bg-gradient-to-r from-rose-600 to-orange-600 text-white hover:opacity-90"
        : variant === "success"
          ? "bg-gradient-to-r from-emerald-600 to-teal-600 text-white hover:opacity-90"
          : "border border-white/10 bg-white/5 hover:bg-white/10 text-slate-200";
  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      className={`${base} ${styles} disabled:opacity-40 disabled:cursor-not-allowed`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </motion.button>
  );
}

function Input({ value, onChange, placeholder, ...rest }) {
  return (
    <input
      className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50 placeholder:text-slate-600"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      {...rest}
    />
  );
}

function Toast({ msg, onDone }) {
  useEffect(() => { const t = setTimeout(onDone, 3000); return () => clearTimeout(t); }, [onDone]);
  return (
    <motion.div
      initial={{ opacity: 0, y: -30, x: "-50%" }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -30 }}
      className="fixed top-4 left-1/2 z-50 glass-panel px-5 py-3 text-sm font-mono text-cyan-300 border-cyan-500/30 shadow-lg shadow-cyan-500/20"
    >
      {msg}
    </motion.div>
  );
}

/* ──────── main ──────── */
export default function App() {
  const [tab, setTab] = useState("Dashboard");
  const [meta, setMeta] = useState(null);
  const [report, setReport] = useState(null);
  const [topology, setTopology] = useState({ nodes: [], edges: [] });
  const [proposals, setProposals] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [log, setLog] = useState("");
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState([]);

  /* form state */
  const [userId, setUserId] = useState("alice");
  const [ipv6, setIpv6] = useState("");
  const [domain, setDomain] = useState("");
  const [sendFrom, setSendFrom] = useState("");
  const [sendTo, setSendTo] = useState("");
  const [propTitle, setPropTitle] = useState("");
  const [propProposer, setPropProposer] = useState("");
  const [voteId, setVoteId] = useState("");
  const [voter, setVoter] = useState("");

  const prevAuditCount = useRef(0);

  const toast = (msg) => setToasts((p) => [...p, { id: Date.now(), msg }]);
  const removeToast = (id) => setToasts((p) => p.filter((t) => t.id !== id));

  const appendLog = (title, data) => {
    const line = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    setLog((prev) => prev + `\n── ${title} ──\n${line}\n`);
  };

  const refresh = useCallback(async () => {
    try {
      const [m, r, t, p, a] = await Promise.all([
        api("/api/meta").then((res) => res.json()),
        api("/api/report?audit_tail=40").then((res) => res.json()),
        api("/api/topology").then((res) => res.json()).catch(() => ({ nodes: [], edges: [] })),
        api("/api/governance/proposals").then((res) => res.json()).catch(() => []),
        api("/api/audit?limit=50").then((res) => res.json()),
      ]);
      setMeta(m);
      setReport(r);
      setTopology(t || { nodes: [], edges: [] });
      setProposals(Array.isArray(p) ? p : []);
      setAuditEvents(a.events || []);
      // Auto-fill IPv6 fields from nodes so buttons work immediately
      const nds = r?.nodes ?? [];
      if (nds.length >= 1) {
        setSendFrom((prev) => prev || nds[0].ipv6);
        setIpv6((prev) => prev || nds[0].ipv6);
        setDomain((prev) => prev || `${nds[0].user_id}.whitenet.local`);
      }
      if (nds.length >= 2) {
        setSendTo((prev) => prev || nds[1].ipv6);
      }
      if (prevAuditCount.current > 0 && m.audit_events > prevAuditCount.current) {
        toast(`+${m.audit_events - prevAuditCount.current} new audit events`);
      }
      prevAuditCount.current = m.audit_events;
    } catch (e) {
      appendLog("Error", String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { const iv = setInterval(refresh, 5000); return () => clearInterval(iv); }, [refresh]);

  const postJson = async (url, body) => {
    setBusy(true);
    try {
      const res = await api(url, { method: "POST", body: JSON.stringify(body) });
      const data = await res.json();
      appendLog(url, data);
      toast(`${url.split("/").pop()} ✔`);
      await refresh();
    } catch (e) {
      appendLog(url, String(e));
    } finally {
      setBusy(false);
    }
  };

  const nodes = report?.nodes ?? [];

  return (
    <div className="min-h-screen scanlines relative overflow-x-hidden">
      {/* ambient blurs */}
      <div className="fixed inset-0 bg-glow-radial pointer-events-none" />
      <div className="fixed inset-0 bg-grid-pattern bg-[length:48px_48px] pointer-events-none opacity-40" aria-hidden />
      <motion.div className="fixed -top-32 -right-32 w-96 h-96 rounded-full bg-cyan-500/20 blur-[100px] pointer-events-none"
        animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }} />
      <motion.div className="fixed -bottom-24 -left-24 w-80 h-80 rounded-full bg-violet-600/20 blur-[90px] pointer-events-none"
        animate={{ scale: [1, 1.1, 1], opacity: [0.25, 0.45, 0.25] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 1 }} />

      {/* toasts */}
      <AnimatePresence>
        {toasts.map((t) => <Toast key={t.id} msg={t.msg} onDone={() => removeToast(t.id)} />)}
      </AnimatePresence>

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-10 md:py-14">
        {/* header */}
        <motion.header initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-8">
          <div>
            <motion.div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-xs font-mono mb-4"
              animate={{ boxShadow: ["0 0 0 0 rgba(34,211,238,0)", "0 0 20px 2px rgba(34,211,238,0.15)", "0 0 0 0 rgba(34,211,238,0)"] }}
              transition={{ duration: 3, repeat: Infinity }}>
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              LIVE TRUST CONSOLE v{meta?.version ?? "…"}
            </motion.div>
            <h1 className="text-4xl md:text-5xl font-bold font-display tracking-tight">
              <span className="text-gradient">WhiteNet</span>
              <span className="text-slate-300 font-light"> Identity</span>
            </h1>
            <p className="mt-3 text-slate-400 max-w-xl text-sm leading-relaxed">
              Zero Trust · IPv6 · PKI · TLS 1.3 · DNSSEC · VPN · Governance — all in your browser.
            </p>
          </div>
          <Btn onClick={refresh} disabled={busy || loading}>{loading ? "Syncing…" : "⟳ Refresh"}</Btn>
        </motion.header>

        {/* tabs */}
        <div className="flex gap-1 mb-8 overflow-x-auto pb-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-xl text-sm font-display font-medium transition-all whitespace-nowrap
                ${tab === t
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-lg shadow-cyan-500/10"
                  : "text-slate-400 hover:text-white hover:bg-white/5 border border-transparent"}`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* ═══ DASHBOARD ═══ */}
        {tab === "Dashboard" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
              <StatCard label="Version" value={meta?.version ?? "—"} icon="📦" delay={0.05} />
              <StatCard label="Registry nodes" value={meta?.registry_nodes ?? "—"} icon="🌐" delay={0.1} />
              <StatCard label="Audit events" value={meta?.audit_events ?? "—"} icon="📋"
                sub={meta?.audit_chain_ok === false ? "⚠ Chain broken" : "✔ Chain OK"} delay={0.15} />
              <StatCard label="CA fingerprint" value={meta?.ca_public_key_sha256 ? `${meta.ca_public_key_sha256.slice(0, 10)}…` : "—"}
                sub={meta?.ca_public_key_sha256} icon="🔑" delay={0.2} />
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
              <StatCard label="Revoked" value={meta?.revoked_count ?? 0} icon="🚫" delay={0.25} />
              <StatCard label="Proposals" value={meta?.proposals_count ?? 0} icon="🗳️" delay={0.3} />
              <StatCard label="TLS Sessions" value={meta?.tls_sessions ?? 0} icon="🔒" delay={0.35} />
              <StatCard label="VPN Tunnels" value={meta?.vpn_tunnels ?? 0} icon="🛡️" delay={0.4} />
            </div>

            {/* node cards */}
            <h2 className="text-lg font-semibold font-display text-slate-200 flex items-center gap-2 mb-4">
              <span className="w-1 h-6 rounded-full bg-gradient-to-b from-cyan-400 to-violet-500" />
              Network nodes & posture
            </h2>
            <div className="space-y-3 mb-10">
              <AnimatePresence mode="popLayout">
                {nodes.length === 0 && !loading && (
                  <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-slate-500 text-sm py-8 text-center glass-panel">
                    No bound nodes — use Actions tab to issue & bind identities.
                  </motion.p>
                )}
                {nodes.map((n, i) => (
                  <motion.div key={n.ipv6} layout initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="glass-panel p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 group hover:border-cyan-500/20 transition-colors">
                    <div className="min-w-0">
                      <p className="font-mono text-xs text-cyan-400/90 truncate">{n.ipv6}</p>
                      <p className="font-display font-medium text-white mt-1">{n.user_id}</p>
                      <p className="text-xs text-slate-500 font-mono mt-0.5 truncate">{n.cert_id}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className={`text-xs font-bold px-3 py-1 rounded-full font-mono
                        ${n.assess?.verdict === "TRUSTED" ? "bg-emerald-500/20 text-emerald-300"
                          : n.assess?.verdict === "WARNING" ? "bg-amber-500/20 text-amber-300"
                            : "bg-rose-500/20 text-rose-300"}`}>
                        {n.assess?.verdict ?? "?"} · {n.assess?.score ?? 0}
                      </span>
                      <Btn small variant="danger" disabled={busy} onClick={() => postJson("/api/revoke", { ipv6: n.ipv6 })}>Revoke</Btn>
                      <Btn small variant="ghost" disabled={busy} onClick={() => postJson("/api/renew", { user_id: n.user_id })}>Renew</Btn>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {/* recent audit */}
            <h3 className="text-sm font-semibold text-slate-400 mb-2 font-display">Recent audit (tail)</h3>
            <div className="glass-panel p-4 max-h-64 overflow-auto font-mono text-[11px] leading-relaxed text-slate-400">
              {(report?.audit_tail ?? []).slice(-12).map((ev, i) => (
                <div key={ev.event_id || i} className="border-b border-white/5 py-1.5 last:border-0">
                  <span className="text-slate-600">{ev.timestamp_utc?.slice(11, 19)}</span>{" "}
                  <span className="text-cyan-500/80">{ev.action}</span>{" "}
                  <span className="text-slate-500">{ev.status}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* ═══ TOPOLOGY ═══ */}
        {tab === "Topology" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h2 className="text-lg font-semibold font-display text-slate-200 mb-4 flex items-center gap-2">
              <span className="w-1 h-6 rounded-full bg-gradient-to-b from-cyan-400 to-violet-500" />
              Network Topology
            </h2>
            <div className="glass-panel p-6 relative" style={{ minHeight: 420 }}>
              <TopologyGraph nodes={topology.nodes} edges={topology.edges} />
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="glass-panel p-3 text-center">
                <p className="text-xs text-slate-500">Nodes</p>
                <p className="text-xl font-display font-semibold text-white">{topology.nodes.length}</p>
              </div>
              <div className="glass-panel p-3 text-center">
                <p className="text-xs text-slate-500">VPN Tunnels</p>
                <p className="text-xl font-display font-semibold text-emerald-400">{topology.edges.filter(e => e.type === "vpn").length}</p>
              </div>
              <div className="glass-panel p-3 text-center">
                <p className="text-xs text-slate-500">TLS Sessions</p>
                <p className="text-xl font-display font-semibold text-sky-400">{topology.edges.filter(e => e.type === "tls").length}</p>
              </div>
            </div>
          </motion.div>
        )}

        {/* ═══ ACTIONS ═══ */}
        {tab === "Actions" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid lg:grid-cols-2 gap-6">
            {/* Identity */}
            <div className="glass-panel p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-300 font-display">🆔 Identity (Issue, Bind, Quick Onboard)</h2>
              <Input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="user id (e.g. alice)" />
              <div className="flex flex-wrap gap-2">
                <Btn onClick={() => postJson("/api/issue", { user_id: userId })} disabled={busy}>Issue cert</Btn>
                <Btn variant="ghost" onClick={() => postJson("/api/bind", { cert_path: "cert.json" })} disabled={busy}>Bind</Btn>
                <Btn variant="success" onClick={() => postJson("/api/quick-onboard", { user_id: userId })} disabled={busy}>⚡ Quick Onboard</Btn>
              </div>
            </div>

            {/* Verify & Send */}
            <div className="glass-panel p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-300 font-display">🔐 Verify, Handshake & Send</h2>
              <Input value={ipv6} onChange={(e) => setIpv6(e.target.value)} placeholder="IPv6 address" />
              {nodes.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {nodes.map((n) => (
                    <button key={n.ipv6} onClick={() => { setIpv6(n.ipv6); setSendFrom(n.ipv6); }}
                      className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-cyan-400 hover:bg-cyan-500/20 font-mono transition-colors">
                      {n.user_id}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <Btn variant="ghost" onClick={() => postJson("/api/verify", { ipv6 })} disabled={busy}>Verify</Btn>
                <Btn variant="ghost" onClick={() => postJson("/api/handshake", { ipv6 })} disabled={busy}>Handshake</Btn>
              </div>
              <Input value={sendFrom} onChange={(e) => setSendFrom(e.target.value)} placeholder="source IPv6 (auto-filled from nodes)" />
              <Input value={sendTo} onChange={(e) => setSendTo(e.target.value)} placeholder="destination IPv6 (auto-filled from nodes)" />
              <Btn onClick={() => postJson("/api/send", { source: sendFrom, destination: sendTo })} disabled={busy}>Secure send</Btn>
            </div>

            {/* DNS / Assess */}
            <div className="glass-panel p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-300 font-display">🌐 DNS Resolve & Assess</h2>
              <Input value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="domain (e.g. alice.whitenet.local)" />
              <div className="flex flex-wrap gap-2">
                <Btn variant="ghost" onClick={() => postJson("/api/resolve", { domain })} disabled={busy}>Resolve</Btn>
                <Btn variant="ghost" onClick={() => postJson("/api/assess", { ipv6: ipv6 || undefined, domain: domain || undefined })}
                  disabled={busy}>Assess</Btn>
              </div>
            </div>

            {/* TLS / DNSSEC / VPN */}
            <div className="glass-panel p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-300 font-display">🔒 TLS 1.3 / DNSSEC / VPN</h2>
              <div className="flex flex-wrap gap-2">
                <Btn variant="ghost" onClick={() => postJson("/api/tls-handshake", { client: sendFrom, server: sendTo })}
                  disabled={busy}>TLS 1.3 Handshake</Btn>
                <Btn variant="ghost" onClick={() => postJson("/api/vpn-tunnel", { node_a: sendFrom, node_b: sendTo })}
                  disabled={busy}>VPN Tunnel</Btn>
              </div>
              <div className="flex flex-wrap gap-2">
                <Btn variant="ghost" onClick={() => postJson("/api/dnssec-sign", {})} disabled={busy}>DNSSEC Sign All</Btn>
                <Btn variant="ghost" onClick={() => postJson("/api/dnssec-verify", { domain: domain || "alice.whitenet.local" })}
                  disabled={busy}>DNSSEC Verify</Btn>
              </div>
              <p className="text-xs text-slate-500">Use source/destination IPv6 fields above for TLS & VPN peers.</p>
            </div>

            {/* Demos */}
            <div className="glass-panel p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-300 font-display">🧪 Demos</h2>
              <div className="flex flex-col gap-2">
                <Btn onClick={() => postJson("/api/demo", { fresh: false, quiet: true })} disabled={busy}>Full demo (keep data)</Btn>
                <Btn variant="danger" onClick={() => {
                  if (window.confirm("Fresh demo deletes all JSON data. Continue?"))
                    postJson("/api/demo", { fresh: true, regen_ca: false, quiet: true });
                }} disabled={busy}>🔄 Fresh full demo</Btn>
                <div className="flex gap-2">
                  <Btn variant="ghost" onClick={() => postJson("/api/security-demo", {})} disabled={busy}>Security demo</Btn>
                  <Btn variant="ghost" onClick={() => postJson("/api/spoof-test", {})} disabled={busy}>Spoof test</Btn>
                </div>
              </div>
            </div>

            {/* Activity log */}
            <div className="glass-panel p-5">
              <h2 className="text-sm font-semibold text-slate-300 font-display mb-2">📜 Activity log</h2>
              <pre className="text-[10px] font-mono text-slate-500 whitespace-pre-wrap max-h-52 overflow-auto">
                {log || "API responses appear here."}
              </pre>
            </div>
          </motion.div>
        )}

        {/* ═══ GOVERNANCE ═══ */}
        {tab === "Governance" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h2 className="text-lg font-semibold font-display text-slate-200 mb-4 flex items-center gap-2">
              <span className="w-1 h-6 rounded-full bg-gradient-to-b from-cyan-400 to-violet-500" />
              Decentralised Governance
            </h2>
            <div className="grid lg:grid-cols-2 gap-6 mb-6">
              <div className="glass-panel p-5 space-y-4">
                <h3 className="text-sm font-semibold text-slate-300 font-display">New proposal</h3>
                <Input value={propTitle} onChange={(e) => setPropTitle(e.target.value)} placeholder="Proposal title" />
                <Input value={propProposer} onChange={(e) => setPropProposer(e.target.value)} placeholder="Proposer name" />
                <Btn onClick={() => postJson("/api/governance/propose", { title: propTitle, proposer: propProposer })}
                  disabled={busy || !propTitle || !propProposer}>Submit proposal</Btn>
              </div>
              <div className="glass-panel p-5 space-y-4">
                <h3 className="text-sm font-semibold text-slate-300 font-display">Cast vote</h3>
                <Input value={voteId} onChange={(e) => setVoteId(e.target.value)} placeholder="Proposal ID" />
                <Input value={voter} onChange={(e) => setVoter(e.target.value)} placeholder="Voter name" />
                <div className="flex gap-2">
                  <Btn variant="success" onClick={() => postJson("/api/governance/vote", { proposal_id: voteId, voter, against: false })}
                    disabled={busy || !voteId || !voter}>Vote FOR</Btn>
                  <Btn variant="danger" onClick={() => postJson("/api/governance/vote", { proposal_id: voteId, voter, against: true })}
                    disabled={busy || !voteId || !voter}>Vote AGAINST</Btn>
                </div>
              </div>
            </div>
            <h3 className="text-sm font-semibold text-slate-400 mb-3 font-display">Active proposals</h3>
            <div className="space-y-3">
              {proposals.length === 0 && (
                <p className="text-slate-500 text-sm py-6 text-center glass-panel">No proposals yet — create one above.</p>
              )}
              {proposals.map((p) => (
                <motion.div key={p.proposal_id} layout className="glass-panel p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div>
                    <p className="font-display font-medium text-white">{p.title}</p>
                    <p className="text-xs text-slate-500 font-mono">ID: {p.proposal_id} · by {p.proposer} · {p.category}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-emerald-400 font-mono">▲ {p.votes_for}</span>
                    <span className="text-xs text-rose-400 font-mono">▼ {p.votes_against}</span>
                    <span className={`text-xs font-bold px-3 py-1 rounded-full font-mono
                      ${p.status === "approved" ? "bg-emerald-500/20 text-emerald-300"
                        : p.status === "rejected" ? "bg-rose-500/20 text-rose-300"
                          : "bg-cyan-500/20 text-cyan-300"}`}>
                      {p.status.toUpperCase()}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* ═══ AUDIT ═══ */}
        {tab === "Audit" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h2 className="text-lg font-semibold font-display text-slate-200 mb-4 flex items-center gap-2">
              <span className="w-1 h-6 rounded-full bg-gradient-to-b from-cyan-400 to-violet-500" />
              Full Audit Log ({auditEvents.length} events)
            </h2>
            <div className="glass-panel p-4 max-h-[600px] overflow-auto font-mono text-xs leading-relaxed text-slate-400">
              {auditEvents.length === 0 && <p className="text-slate-500 py-4 text-center">No audit events yet.</p>}
              {auditEvents.map((ev, i) => (
                <motion.div key={ev.event_id || i} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="border-b border-white/5 py-2 last:border-0 flex flex-wrap items-center gap-2">
                  <span className="text-slate-600 w-16 flex-shrink-0">{ev.timestamp_utc?.slice(11, 19)}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold
                    ${ev.status === "success" || ev.status === "allowed" ? "bg-emerald-500/20 text-emerald-300"
                      : ev.status === "blocked" ? "bg-rose-500/20 text-rose-300"
                        : "bg-amber-500/20 text-amber-300"}`}>{ev.status}</span>
                  <span className="text-cyan-500/80">{ev.action}</span>
                  <span className="text-slate-600 text-[10px] truncate flex-1">{ev.event_hash?.slice(0, 12)}…</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        <footer className="mt-16 text-center text-xs text-slate-600 font-mono">
          WhiteNet {meta?.version ?? ""} · Flask + React + TLS 1.3 + DNSSEC + VPN · <code className="text-slate-500">python web/server.py</code>
        </footer>
      </div>
    </div>
  );
}


/* ═══ Topology SVG ═══ */
function TopologyGraph({ nodes, edges }) {
  const svgRef = useRef(null);
  const [positions, setPositions] = useState([]);

  useEffect(() => {
    if (!nodes.length) { setPositions([]); return; }
    const W = 700, H = 380;
    const cx = W / 2, cy = H / 2;
    const r = Math.min(W, H) * 0.35;
    const pos = nodes.map((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
      return { ...n, x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });
    setPositions(pos);
  }, [nodes]);

  if (!nodes.length) {
    return <p className="text-slate-500 text-sm text-center py-16">No nodes to display. Run a demo or onboard nodes first.</p>;
  }

  const nodeMap = {};
  positions.forEach((p) => { nodeMap[p.ipv6] = p; });

  const verdictColor = (v) =>
    v === "TRUSTED" ? "#34d399" : v === "WARNING" ? "#fbbf24" : "#f87171";

  return (
    <svg ref={svgRef} viewBox="0 0 700 380" className="w-full h-auto">
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur" />
          <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      {/* edges */}
      {edges.map((e, i) => {
        const a = nodeMap[e.a], b = nodeMap[e.b];
        if (!a || !b) return null;
        return (
          <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
            stroke={e.type === "vpn" ? "#34d399" : "#38bdf8"}
            strokeWidth={2} strokeDasharray={e.type === "tls" ? "6 3" : "none"}
            opacity={0.5} />
        );
      })}
      {/* nodes */}
      {positions.map((p, i) => {
        const color = verdictColor(p.assess?.verdict);
        return (
          <g key={p.ipv6}>
            <circle cx={p.x} cy={p.y} r={22} fill={color + "22"} stroke={color} strokeWidth={2} filter="url(#glow)" />
            {p.revoked && <line x1={p.x - 14} y1={p.y - 14} x2={p.x + 14} y2={p.y + 14} stroke="#f87171" strokeWidth={2.5} />}
            <text x={p.x} y={p.y + 4} textAnchor="middle" fill="white" fontSize={11} fontFamily="Outfit" fontWeight={600}>
              {p.user_id?.slice(0, 6)}
            </text>
            <text x={p.x} y={p.y + 38} textAnchor="middle" fill="#64748b" fontSize={8} fontFamily="JetBrains Mono">
              {p.assess?.score ?? "?"}/100
            </text>
          </g>
        );
      })}
      {/* legend */}
      <g transform="translate(10, 350)">
        <line x1={0} y1={0} x2={20} y2={0} stroke="#34d399" strokeWidth={2} /><text x={24} y={4} fill="#94a3b8" fontSize={9}>VPN</text>
        <line x1={65} y1={0} x2={85} y2={0} stroke="#38bdf8" strokeWidth={2} strokeDasharray="6 3" /><text x={89} y={4} fill="#94a3b8" fontSize={9}>TLS</text>
      </g>
    </svg>
  );
}
