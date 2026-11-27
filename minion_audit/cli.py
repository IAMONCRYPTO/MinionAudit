from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

from dotenv import load_dotenv

from .report import write_report

PROJECT = Path(__file__).resolve().parent.parent


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="minion_audit", description="Local Solidity and Python security review, powered by OpenMinion.")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="Scan a repository with real NVIDIA NIM execution")
    scan.add_argument("target", type=Path)
    scan.add_argument("--no-fix", action="store_true", help="Skip the permission-gated .gitignore action")
    scan.add_argument("--session", help="Continue a previous SDK session; re-scan current files")
    scan.add_argument("--config", type=Path, default=PROJECT / "agents.json")
    scan.add_argument("--report", type=Path, default=Path("reports/audit_report.html"))
    inspect = commands.add_parser("inspect", help="Inspect a saved run without calling the model")
    inspect.add_argument("session")
    args = parser.parse_args()
    state = PROJECT / ".minion_audit"
    if args.command == "inspect":
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.session):
            parser.error("Invalid session identifier")
        path = state / "runs" / f"{args.session}.json"
        if not path.is_file():
            parser.error("Session not found")
        print(path.read_text(encoding="utf-8"))
        return 0
    root = args.target.resolve()
    if not root.is_dir():
        parser.error("Target must be an existing directory")
    if args.session and not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.session):
        parser.error("Invalid session identifier")
    load_dotenv(PROJECT / ".env")
    os.environ.setdefault("OPENMINION_LOG_LEVEL", "ERROR")
    if not os.environ.get("NVIDIA_API_KEY"):
        parser.error("Set NVIDIA_API_KEY in the local .env file")
    from .agent import audit
    print(f"MinionAudit / {root.name}\nOpenMinion 0.1.22 / real NVIDIA NIM execution", flush=True)
    result = audit(root, args.config.resolve(), state, not args.no_fix, args.session)
    write_report(result, args.report)
    counts = {s: sum(f["severity"] == s for f in result["findings"]) for s in ("Critical", "High", "Medium")}
    print("\n" + "  |  ".join(f"{s}: {n}" for s, n in counts.items()))
    for finding in result["findings"]:
        print(f"  {finding['severity']:8} {finding['rule']}  {finding['file']}:{finding['line']}  {finding['title']}")
    delta = result.get("delta", {})
    if delta.get("previous") is not None:
        print(f"Previous run: {delta['previous']} issues -> Current run: {delta['current']} issues ({delta['resolved']} resolved, {delta['new']} new)")
    else:
        print("Baseline: first completed scan" if result["status"] == "complete" else "Baseline not updated")
    print(f"Status: {result['status']} / {result['elapsed_seconds']}s / session: {result['session']}")
    if result.get("error"):
        print(result["error"])
    for warning in result.get("warnings", []):
        print(f"Warning: {warning}")
    print(f"Report: {args.report.resolve()}")
    print(f"Inspect: python -m minion_audit inspect {result['session']}")
    return 0 if result["status"] == "complete" else 2
