"""
WhiteNet desktop GUI — same engine as cli.py (tkinter, stdlib-only beyond cryptography).
Run from project directory:  python gui.py
"""

from __future__ import annotations

import io
import os
import re
import sys
import threading
from contextlib import redirect_stdout

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import cli

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def run_in_gui(root: tk.Tk, log: scrolledtext.ScrolledText, fn, *args, **kwargs) -> None:
    """Run a cli function in a background thread; append captured stdout to the log."""

    def worker() -> None:
        buf = io.StringIO()
        prev_quiet = os.environ.get("WHITENET_QUIET")
        os.environ["WHITENET_QUIET"] = "1"
        try:
            with redirect_stdout(buf):
                fn(*args, **kwargs)
            out = strip_ansi(buf.getvalue())
            if not out.endswith("\n"):
                out += "\n"
        except Exception as e:
            out = f"Error: {e}\n"
        finally:
            if prev_quiet is None:
                os.environ.pop("WHITENET_QUIET", None)
            else:
                os.environ["WHITENET_QUIET"] = prev_quiet

        def append() -> None:
            log.insert(tk.END, out)
            log.see(tk.END)

        root.after(0, append)

    threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    cli.generate_ca_keys()

    root = tk.Tk()
    root.title(f"WhiteNet — {cli.WHITENET_VERSION}")
    root.minsize(780, 560)
    root.geometry("900x680")

    main_fr = ttk.Frame(root, padding=8)
    main_fr.pack(fill=tk.BOTH, expand=True)

    header = ttk.Label(
        main_fr,
        text="WhiteNet Identity — Zero Trust • IPv6 • Cryptographic Identity (GUI)",
        font=("Segoe UI", 11, "bold"),
    )
    header.pack(anchor=tk.W)

    nb = ttk.Notebook(main_fr)
    nb.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    # --- Shared output log ---
    log_fr = ttk.LabelFrame(main_fr, text="Output", padding=6)
    log_fr.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
    log = scrolledtext.ScrolledText(log_fr, height=14, wrap=tk.WORD, font=("Consolas", 10))
    log.pack(fill=tk.BOTH, expand=True)

    def clear_log() -> None:
        log.delete("1.0", tk.END)

    ttk.Button(log_fr, text="Clear output", command=clear_log).pack(anchor=tk.E, pady=(4, 0))

    def tab_identity() -> ttk.Frame:
        fr = ttk.Frame(nb, padding=10)
        ttk.Label(fr, text="User ID (for issue)").grid(row=0, column=0, sticky=tk.W)
        user_var = tk.StringVar(value="alice")
        ttk.Entry(fr, textvariable=user_var, width=48).grid(row=0, column=1, sticky=tk.W, padx=6)

        cert_var = tk.StringVar(value=cli.CERT_FILE)
        ttk.Label(fr, text="Certificate file (bind)").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ce = ttk.Entry(fr, textvariable=cert_var, width=40)
        ce.grid(row=1, column=1, sticky=tk.W, padx=6, pady=(8, 0))

        def browse_cert() -> None:
            p = filedialog.askopenfilename(
                title="Select certificate JSON",
                filetypes=[("JSON", "*.json"), ("All", "*.*")],
            )
            if p:
                cert_var.set(p)

        ttk.Button(fr, text="Browse…", command=browse_cert).grid(row=1, column=2, padx=4, pady=(8, 0))

        def do_issue() -> None:
            u = user_var.get().strip()
            if not u:
                messagebox.showwarning("WhiteNet", "Enter a user ID.")
                return
            run_in_gui(root, log, cli.issue_certificate, u)

        def do_bind() -> None:
            p = cert_var.get().strip()
            if not p:
                messagebox.showwarning("WhiteNet", "Select a certificate file.")
                return
            run_in_gui(root, log, cli.bind_identity, p)

        ttk.Button(fr, text="Issue certificate", command=do_issue).grid(row=2, column=1, sticky=tk.W, pady=12)
        ttk.Button(fr, text="Bind identity", command=do_bind).grid(row=2, column=2, sticky=tk.W, pady=12)
        return fr

    def tab_verify() -> ttk.Frame:
        fr = ttk.Frame(nb, padding=10)
        ttk.Label(fr, text="IPv6 address").grid(row=0, column=0, sticky=tk.W)
        ip_var = tk.StringVar()
        ttk.Entry(fr, textvariable=ip_var, width=56).grid(row=0, column=1, sticky=tk.W, padx=6)

        def do_verify() -> None:
            s = ip_var.get().strip()
            if not s:
                messagebox.showwarning("WhiteNet", "Enter an IPv6 address.")
                return
            run_in_gui(root, log, cli.verify_node, s)

        def do_handshake() -> None:
            s = ip_var.get().strip()
            if not s:
                messagebox.showwarning("WhiteNet", "Enter an IPv6 address.")
                return
            run_in_gui(root, log, cli.handshake_node, s)

        ttk.Button(fr, text="Verify node", command=do_verify).grid(row=1, column=1, sticky=tk.W, pady=10)
        ttk.Button(fr, text="Handshake", command=do_handshake).grid(row=1, column=2, sticky=tk.W, pady=10)
        return fr

    def tab_transport() -> ttk.Frame:
        fr = ttk.Frame(nb, padding=10)
        ttk.Label(fr, text="Source IPv6").grid(row=0, column=0, sticky=tk.W)
        src_var = tk.StringVar()
        ttk.Entry(fr, textvariable=src_var, width=56).grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Label(fr, text="Destination IPv6").grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        dst_var = tk.StringVar()
        ttk.Entry(fr, textvariable=dst_var, width=56).grid(row=1, column=1, sticky=tk.W, padx=6, pady=(6, 0))
        ttk.Label(fr, text="Domain (resolve)").grid(row=2, column=0, sticky=tk.W, pady=(6, 0))
        dom_var = tk.StringVar()
        ttk.Entry(fr, textvariable=dom_var, width=56).grid(row=2, column=1, sticky=tk.W, padx=6, pady=(6, 0))

        def do_send() -> None:
            a, b = src_var.get().strip(), dst_var.get().strip()
            if not a or not b:
                messagebox.showwarning("WhiteNet", "Enter source and destination IPv6.")
                return
            run_in_gui(root, log, cli.send_secure, a, b)

        def do_resolve() -> None:
            d = dom_var.get().strip()
            if not d:
                messagebox.showwarning("WhiteNet", "Enter a domain.")
                return
            run_in_gui(root, log, cli.resolve_domain, d)

        ttk.Button(fr, text="Send (secure)", command=do_send).grid(row=3, column=1, sticky=tk.W, pady=12)
        ttk.Button(fr, text="Resolve domain", command=do_resolve).grid(row=3, column=2, sticky=tk.W, pady=12)
        return fr

    def tab_trust() -> ttk.Frame:
        fr = ttk.Frame(nb, padding=10)
        ttk.Label(fr, text="IPv6 (optional if domain set)").grid(row=0, column=0, sticky=tk.W)
        ip_var = tk.StringVar()
        ttk.Entry(fr, textvariable=ip_var, width=52).grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Label(fr, text="Domain (optional)").grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        dom_var = tk.StringVar()
        ttk.Entry(fr, textvariable=dom_var, width=52).grid(row=1, column=1, sticky=tk.W, padx=6, pady=(6, 0))

        def do_assess() -> None:
            ipv6 = ip_var.get().strip() or None
            domain = dom_var.get().strip() or None
            if not ipv6 and not domain:
                messagebox.showwarning("WhiteNet", "Enter IPv6 and/or domain for assess.")
                return
            run_in_gui(root, log, cli.assess_posture, ipv6, domain, False)

        ttk.Label(fr, text="Audit: last N events").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        lim_var = tk.StringVar(value="20")
        ttk.Entry(fr, textvariable=lim_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=6, pady=(10, 0))
        verify_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(fr, text="Verify full audit chain", variable=verify_var).grid(row=2, column=2, sticky=tk.W, pady=(10, 0))

        def do_audit() -> None:
            try:
                n = int(lim_var.get().strip() or "20")
            except ValueError:
                messagebox.showwarning("WhiteNet", "Enter a valid number for audit limit.")
                return
            run_in_gui(root, log, cli.show_audit, n, verify_var.get())

        ttk.Button(fr, text="Run assess", command=do_assess).grid(row=3, column=1, sticky=tk.W, pady=12)
        ttk.Button(fr, text="Show audit log", command=do_audit).grid(row=3, column=2, sticky=tk.W, pady=12)
        return fr

    def tab_network() -> ttk.Frame:
        fr = ttk.Frame(nb, padding=10)
        ttk.Label(fr, text="Export trust report JSON to:").grid(row=0, column=0, sticky=tk.W)
        rep_var = tk.StringVar(value="trust_report.json")
        ttk.Entry(fr, textvariable=rep_var, width=44).grid(row=0, column=1, sticky=tk.W, padx=6)

        def browse_rep() -> None:
            p = filedialog.asksaveasfilename(
                title="Save trust report",
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("All", "*.*")],
            )
            if p:
                rep_var.set(p)

        ttk.Button(fr, text="Browse…", command=browse_rep).grid(row=0, column=2, padx=4)

        tail_var = tk.StringVar(value="50")

        def do_list() -> None:
            run_in_gui(root, log, cli.list_state)

        def do_status() -> None:
            run_in_gui(root, log, cli.print_status)

        def do_report() -> None:
            p = rep_var.get().strip()
            if not p:
                messagebox.showwarning("WhiteNet", "Choose a report path.")
                return
            try:
                tail = int(tail_var.get().strip() or "50")
            except ValueError:
                messagebox.showwarning("WhiteNet", "Audit tail must be a number.")
                return
            run_in_gui(root, log, cli.export_trust_report, p, tail)

        ttk.Label(fr, text="Audit tail (report)").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(fr, textvariable=tail_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=6, pady=(8, 0))

        ttk.Button(fr, text="List network state", command=do_list).grid(row=2, column=1, sticky=tk.W, pady=12)
        ttk.Button(fr, text="Status snapshot", command=do_status).grid(row=2, column=2, sticky=tk.W, pady=12)
        ttk.Button(fr, text="Write trust report", command=do_report).grid(row=3, column=1, sticky=tk.W)
        return fr

    def tab_demos() -> ttk.Frame:
        fr = ttk.Frame(nb, padding=10)
        ttk.Label(
            fr,
            text="Automated demo resets data if “Fresh state” is checked. Confirm before running in a folder with important JSON.",
            wraplength=720,
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W)

        fresh_var = tk.BooleanVar(value=False)
        regen_var = tk.BooleanVar(value=False)
        quiet_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fr, text="Fresh state (delete registry/DNS/cert/audit)", variable=fresh_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=6)
        ttk.Checkbutton(fr, text="Regenerate CA (only with fresh)", variable=regen_var).grid(row=2, column=0, columnspan=2, sticky=tk.W)
        ttk.Checkbutton(fr, text="Quiet (no loading delays)", variable=quiet_var).grid(row=3, column=0, columnspan=2, sticky=tk.W)

        def do_demo() -> None:
            if fresh_var.get() and not messagebox.askyesno(
                "WhiteNet",
                "Fresh state will delete registry.json, dns_records.json, cert.json, and audit_log.json in the current folder. Continue?",
            ):
                return
            run_in_gui(
                root,
                log,
                cli.run_automated_demo,
                fresh_var.get(),
                regen_var.get(),
                quiet_var.get(),
            )

        def do_sec() -> None:
            run_in_gui(root, log, cli.security_demo)

        def do_spoof() -> None:
            run_in_gui(root, log, cli.spoof_test)

        ttk.Button(fr, text="Run full demo (alice/bob)", command=do_demo).grid(row=4, column=1, sticky=tk.W, pady=14)
        ttk.Button(fr, text="Security demo (tamper)", command=do_sec).grid(row=5, column=1, sticky=tk.W)
        ttk.Button(fr, text="Spoof test", command=do_spoof).grid(row=6, column=1, sticky=tk.W, pady=(6, 0))
        return fr

    nb.add(tab_identity(), text="Identity")
    nb.add(tab_verify(), text="Verify")
    nb.add(tab_transport(), text="Send / DNS")
    nb.add(tab_trust(), text="Trust + Audit")
    nb.add(tab_network(), text="Network + Report")
    nb.add(tab_demos(), text="Demos")

    log.insert(tk.END, f"WhiteNet GUI {cli.WHITENET_VERSION} — working directory: {os.getcwd()}\n")
    log.insert(tk.END, "Use CLI anytime: python cli.py …\n\n")

    root.mainloop()


if __name__ == "__main__":
    main()
