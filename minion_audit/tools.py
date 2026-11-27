"""Read-only heuristics. Findings are review candidates, not proof of exploitability."""
from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import re

SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", "vendor", "reports", ".minion_audit", ".openminion"}
SECRET = re.compile(r'''(?ix)(?:api[_-]?key|secret|private[_-]?key|password|mnemonic|seed_phrase)\s*[=:]\s*["']?([^\s"'\#;,]{8,}|(?:[a-z]+\s+){11,23}[a-z]+)''')
TOKEN = re.compile(r"(?:nvapi-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9_-]{16,}|AKIA[A-Z0-9]{16}|0x[a-fA-F0-9]{64})")


def redact(text: str) -> str:
    text = TOKEN.sub("[REDACTED]", text)
    return SECRET.sub(lambda m: m.group(0)[:m.start(1)-m.start()] + "[REDACTED]", text)


def fingerprint(rule: str, file: str, snippet: str, occurrence: int) -> str:
    return hashlib.sha256(f"{rule}|{file}|{snippet.strip()}|{occurrence}".encode()).hexdigest()[:20]


def scan_tree(root: Path) -> dict:
    findings, warnings, scanned = [], [], 0
    occurrences = {}

    def add(rule, severity, path, line, snippet, title, fix):
        relative = path.relative_to(root).as_posix()
        snippet = redact(snippet.strip())[:240]
        key = (rule, relative, snippet)
        occurrences[key] = occurrences.get(key, 0) + 1
        findings.append(dict(id=fingerprint(rule, relative, snippet, occurrences[key]), rule=rule,
            severity=severity, file=relative, line=line, snippet=snippet, title=title, fix=fix))

    def walk_error(error):
        warnings.append(f"Unreadable directory: {redact(str(error))}")

    for base, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(base)/d).is_symlink()
                         and not getattr(Path(base)/d, "is_junction", lambda: False)())
        for name in sorted(names):
            path = Path(base)/name
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                warnings.append(f"Skipped link: {path.relative_to(root)}")
                continue
            if path.suffix.lower() not in {".sol", ".py", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"} and not name.startswith(".env"):
                continue
            try:
                if path.stat().st_size > 1_000_000:
                    warnings.append(f"Skipped oversized file: {path.relative_to(root)}")
                    continue
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                warnings.append(f"Skipped unreadable file: {path.relative_to(root)} ({type(exc).__name__})")
                continue
            scanned += 1
            lines = source.splitlines()
            if name == ".env":
                add("SEC002", "High", path, 1, "[environment file contents withheld]", "Environment file present", "Confirm this file is untracked; ignore .env and rotate any exposed credentials.")
            for number, line in enumerate(lines, 1):
                if line.lstrip().startswith(("#", "//")):
                    continue
                if SECRET.search(line) or TOKEN.search(line) or "BEGIN PRIVATE KEY" in line:
                    add("SEC001", "Critical", path, number, "[secret-bearing line withheld]", "Possible hardcoded credential", "Rotate the credential, remove it from source and history, and load it from the environment.")
                if path.suffix == ".sol":
                    checks = [
                        ("SOL001", "High", r"\btx\s*\.\s*origin\b", "tx.origin authentication candidate", "Use msg.sender with an explicit authorization policy."),
                        ("SOL002", "High", r"\.call(?:\s*\{|\s*\(|\.value)", "Low-level external call requires review", "Check the success result; apply checks-effects-interactions and assess reentrancy."),
                        ("SOL003", "Medium", r"pragma\s+solidity\s+[^;]*0\.[0-7]\.", "Outdated Solidity compiler range", "Migrate to a supported 0.8.x compiler and test arithmetic and contract behavior."),
                        ("SOL004", "High", r"function\s+(?:setOwner|mint|withdraw|upgrade\w*)\b.*\b(?:public|external)\b", "Sensitive public function requires access review", "Verify access control across the full function body and inherited modifiers; this heuristic cannot prove it is missing.")]
                    for rule, severity, pattern, title, fix in checks:
                        if re.search(pattern, line):
                            add(rule, severity, path, number, line, title, fix)
            if path.suffix == ".py":
                try:
                    tree = ast.parse(source)
                except SyntaxError:
                    warnings.append(f"Python parse failed: {path.relative_to(root)}")
                    continue
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    fn = ast.unparse(node.func)
                    rule = title = fix = None
                    if fn in {"eval", "exec", "builtins.eval", "builtins.exec"}:
                        rule, title, fix = "PY001", "Dynamic Python execution", "Remove dynamic execution; parse a restricted data format or use an explicit dispatch table."
                    elif any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords) and fn.startswith(("subprocess.", "sp.")):
                        rule, title, fix = "PY002", "Subprocess shell execution", "Pass an argument list with shell=False and validate untrusted arguments."
                    elif fn in {"yaml.load", "yaml.unsafe_load"} and not any(k.arg == "Loader" and ast.unparse(k.value) in {"yaml.SafeLoader", "SafeLoader"} for k in node.keywords):
                        rule, title, fix = "PY003", "Potentially unsafe YAML deserialization", "Use yaml.safe_load for untrusted data."
                    if rule:
                        add(rule, "High", path, node.lineno, lines[node.lineno-1], title, fix)
            if name == "requirements.txt":
                for number, line in enumerate(lines, 1):
                    if line.strip() and not line.startswith("#") and "==" not in line:
                        add("DEP001", "Medium", path, number, line, "Dependency is not exactly pinned", "Pin reviewed versions in a lock file and verify hashes.")
    return {"findings": findings, "files_scanned": scanned, "warnings": warnings, "complete": not warnings}


def protect_environment(root: Path) -> dict:
    """The only repository edit: append a literal .env ignore rule."""
    path = root / ".gitignore"
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError("Refusing .gitignore outside the target")
    if path.exists() and path.stat().st_nlink > 1:
        raise ValueError("Refusing to edit a hard-linked .gitignore")
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    if ".env" in previous.splitlines():
        return {"changed": False, "path": ".gitignore"}
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(("\n" if previous and not previous.endswith("\n") else "") + ".env\n")
    return {"changed": True, "path": ".gitignore"}
