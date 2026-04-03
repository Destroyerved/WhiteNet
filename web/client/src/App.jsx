import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

const api = (path, opts = {}) =>
  fetch(path, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });

function StatCard({ label, value, sub, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, type: "spring", stiffness: 120 }}
      className="glass-panel p-5 relative overflow-hidden group"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-violet-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      <p className="text-xs uppercase tracking-widest text-slate-500 font-medium">{label}</p>
      <p className="mt-2 text-2xl font-semibold font-display text-white tabular-nums">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500 font-mono truncate">{sub}</p>}
    </motion.div>
  );
}

function ActionButton({ children, onClick, variant = "primary", disabled }) {
  const base =
    "px-4 py-2.5 rounded-xl font-medium text-sm transition-all duration-300 font-display";
  const styles =
    variant === "primary"
      ? "bg-gradient-to-r from-cyan-500 to-sky-600 text-white shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98]"
      : variant === "danger"
        ? "bg-gradient-to-r from-rose-600 to-orange-600 text-white hover:opacity-90"
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

export default function App() {
  const [meta, setMeta] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [log, setLog] = useState("");
  const [userId, setUserId] = useState("alice");
  const [certPath, setCertPath] = useState("cert.json");
  const [ipv6, setIpv6] = useState("");
  const [domain, setDomain] = useState("");
  const [sendFrom, setSendFrom] = useState("");
  const [sendTo, setSendTo] = useState("");
  const [auditLimit, setAuditLimit] = useState(20);
  const [busy, setBusy] = useState(false);

  const appendLog = (title, data) => {
    const line =
      typeof data === "string"
        ? data
        : JSON.stringify(data, null, 2);
    setLog((prev) => prev + `\n── ${title} ──\n${line}\n`);
  };

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [m, r] = await Promise.all([
        api("/api/meta").then((res) => res.json()),
        api("/api/report?audit_tail=40").then((res) => res.json()),
      ]);
      setMeta(m);
      setReport(r);
    } catch (e) {
      appendLog("Error", String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const postJson = async (url, body) => {
    setBusy(true);
    try {
      const res = await api(url, {
        method: "POST",
        body: JSON.stringify(body),
      });
      const data = await res.json();
      appendLog(url, data);
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
      {/* ambient */}
      <div className="fixed inset-0 bg-glow-radial pointer-events-none" />
      <div
        className="fixed inset-0 bg-grid-pattern bg-[length:48px_48px] pointer-events-none opacity-40"
        aria-hidden
      />
      <motion.div
        className="fixed -top-32 -right-32 w-96 h-96 rounded-full bg-cyan-500/20 blur-[100px] pointer-events-none"
        animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="fixed -bottom-24 -left-24 w-80 h-80 rounded-full bg-violet-600/20 blur-[90px] pointer-events-none"
        animate={{ scale: [1, 1.1, 1], opacity: [0.25, 0.45, 0.25] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 1 }}
      />

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-10 md:py-14">
        {/* header */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-12"
        >
          <div>
            <motion.div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-xs font-mono mb-4"
              animate={{ boxShadow: ["0 0 0 0 rgba(34,211,238,0)", "0 0 20px 2px rgba(34,211,238,0.15)", "0 0 0 0 rgba(34,211,238,0)"] }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              LIVE TRUST CONSOLE
            </motion.div>
            <h1 className="text-4xl md:text-5xl font-bold font-display tracking-tight">
              <span className="text-gradient">WhiteNet</span>
              <span className="text-slate-300 font-light"> Identity</span>
            </h1>
            <p className="mt-3 text-slate-400 max-w-xl text-sm md:text-base leading-relaxed">
              Zero Trust · IPv6-bound identities · Signed audit chain. Same engine as{" "}
              <code className="text-cyan-400/90 font-mono text-xs">cli.py</code> — now in your browser.
            </p>
          </div>
          <motion.div
            className="flex gap-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <ActionButton onClick={refresh} disabled={busy || loading}>
              {loading ? "Syncing…" : "Refresh data"}
            </ActionButton>
          </motion.div>
        </motion.header>

        {/* stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          <StatCard
            label="Version"
            value={meta?.version ?? "—"}
            delay={0.05}
          />
          <StatCard
            label="Registry nodes"
            value={meta?.registry_nodes ?? "—"}
            delay={0.1}
          />
          <StatCard
            label="Audit events"
            value={meta?.audit_events ?? "—"}
            sub={meta?.audit_chain_ok === false ? "Chain broken" : "Chain OK"}
            delay={0.15}
          />
          <StatCard
            label="CA fingerprint"
            value={meta?.ca_public_key_sha256 ? `${meta.ca_public_key_sha256.slice(0, 10)}…` : "—"}
            sub={meta?.ca_public_key_sha256}
            delay={0.2}
          />
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* nodes */}
          <motion.section
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.25 }}
            className="lg:col-span-2 space-y-4"
          >
            <h2 className="text-lg font-semibold font-display text-slate-200 flex items-center gap-2">
              <span className="w-1 h-6 rounded-full bg-gradient-to-b from-cyan-400 to-violet-500" />
              Network & posture
            </h2>
            <div className="space-y-3">
              <AnimatePresence mode="popLayout">
                {nodes.length === 0 && !loading && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-slate-500 text-sm py-8 text-center glass-panel"
                  >
                    No bound nodes yet — issue & bind from the actions panel.
                  </motion.p>
                )}
                {nodes.map((n, i) => (
                  <motion.div
                    key={n.ipv6}
                    layout
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="glass-panel p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 group hover:border-cyan-500/20 transition-colors"
                  >
                    <div>
                      <p className="font-mono text-xs text-cyan-400/90">{n.ipv6}</p>
                      <p className="font-display font-medium text-white mt-1">{n.user_id}</p>
                      <p className="text-xs text-slate-500 font-mono mt-0.5">{n.cert_id}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <motion.span
                        className={`text-xs font-bold px-3 py-1 rounded-full font-mono ${
                          n.assess?.verdict === "TRUSTED"
                            ? "bg-emerald-500/20 text-emerald-300"
                            : n.assess?.verdict === "WARNING"
                              ? "bg-amber-500/20 text-amber-300"
                              : "bg-rose-500/20 text-rose-300"
                        }`}
                        whileHover={{ scale: 1.05 }}
                      >
                        {n.assess?.verdict ?? "?"} · {n.assess?.score ?? 0}
                      </motion.span>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {/* audit tail */}
            <h3 className="text-sm font-semibold text-slate-400 mt-8 mb-2 font-display">Recent audit (tail)</h3>
            <div className="glass-panel p-4 max-h-64 overflow-auto font-mono text-[11px] leading-relaxed text-slate-400">
              {(report?.audit_tail ?? []).slice(-12).map((ev, i) => (
                <motion.div
                  key={ev.event_id || i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.02 }}
                  className="border-b border-white/5 py-1.5 last:border-0"
                >
                  <span className="text-slate-600">{ev.timestamp_utc?.slice(11, 19)}</span>{" "}
                  <span className="text-cyan-500/80">{ev.action}</span>{" "}
                  <span className="text-slate-500">{ev.status}</span>
                </motion.div>
              ))}
            </div>
          </motion.section>

          {/* actions */}
          <motion.aside
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-6"
          >
            <div className="glass-panel p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-300 font-display">Identity</h2>
              <input
                className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="user id"
              />
              <input
                className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                value={certPath}
                onChange={(e) => setCertPath(e.target.value)}
                placeholder="cert.json path"
              />
              <div className="flex flex-wrap gap-2">
                <ActionButton onClick={() => postJson("/api/issue", { user_id: userId })} disabled={busy}>
                  Issue cert
                </ActionButton>
                <ActionButton variant="ghost" onClick={() => postJson("/api/bind", { cert_path: certPath })} disabled={busy}>
                  Bind
                </ActionButton>
              </div>
            </div>

            <div className="glass-panel p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-300 font-display">Verify & send</h2>
              <input
                className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono"
                value={ipv6}
                onChange={(e) => setIpv6(e.target.value)}
                placeholder="IPv6"
              />
              <div className="flex flex-wrap gap-2">
                <ActionButton variant="ghost" onClick={() => postJson("/api/verify", { ipv6 })} disabled={busy}>
                  Verify
                </ActionButton>
                <ActionButton variant="ghost" onClick={() => postJson("/api/handshake", { ipv6 })} disabled={busy}>
                  Handshake
                </ActionButton>
              </div>
              <input
                className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono"
                value={sendFrom}
                onChange={(e) => setSendFrom(e.target.value)}
                placeholder="source IPv6"
              />
              <input
                className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono"
                value={sendTo}
                onChange={(e) => setSendTo(e.target.value)}
                placeholder="destination IPv6"
              />
              <ActionButton onClick={() => postJson("/api/send", { source: sendFrom, destination: sendTo })} disabled={busy}>
                Secure send
              </ActionButton>
              <input
                className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="domain (e.g. alice.whitenet.local)"
              />
              <div className="flex flex-wrap gap-2">
                <ActionButton variant="ghost" onClick={() => postJson("/api/resolve", { domain })} disabled={busy}>
                  Resolve
                </ActionButton>
                <ActionButton
                  variant="ghost"
                  onClick={async () => {
                    setBusy(true);
                    try {
                      const res = await api("/api/assess", {
                        method: "POST",
                        body: JSON.stringify({
                          ipv6: ipv6 || undefined,
                          domain: domain || undefined,
                        }),
                      });
                      const data = await res.json();
                      appendLog("assess", data);
                      await refresh();
                    } catch (e) {
                      appendLog("assess", String(e));
                    } finally {
                      setBusy(false);
                    }
                  }}
                  disabled={busy || (!ipv6 && !domain)}
                >
                  Assess
                </ActionButton>
              </div>
            </div>

            <div className="glass-panel p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-300 font-display">Demos</h2>
              <div className="flex flex-col gap-2">
                <ActionButton
                  onClick={() => postJson("/api/demo", { fresh: false, quiet: true })}
                  disabled={busy}
                >
                  Full demo (no reset)
                </ActionButton>
                <ActionButton
                  variant="danger"
                  onClick={() => {
                    if (window.confirm("Fresh demo deletes registry, DNS, cert, and audit JSON. Continue?")) {
                      postJson("/api/demo", { fresh: true, regen_ca: false, quiet: true });
                    }
                  }}
                  disabled={busy}
                >
                  Fresh full demo
                </ActionButton>
                <div className="flex gap-2">
                  <ActionButton variant="ghost" onClick={() => postJson("/api/security-demo", {})} disabled={busy}>
                    Security demo
                  </ActionButton>
                  <ActionButton variant="ghost" onClick={() => postJson("/api/spoof-test", {})} disabled={busy}>
                    Spoof test
                  </ActionButton>
                </div>
              </div>
            </div>

            <div className="glass-panel p-5">
              <h2 className="text-sm font-semibold text-slate-300 font-display mb-2">Activity log</h2>
              <pre className="text-[10px] font-mono text-slate-500 whitespace-pre-wrap max-h-40 overflow-auto">
                {log || "API responses appear here."}
              </pre>
            </div>
          </motion.aside>
        </div>

        <footer className="mt-16 text-center text-xs text-slate-600 font-mono">
          WhiteNet {meta?.version ?? ""} · Flask + React · Run{" "}
          <code className="text-slate-500">python web/server.py</code>
        </footer>
      </div>
    </div>
  );
}
