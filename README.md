# MinionAudit

A local-first Solidity and Python security review CLI for Cortensor Hackathon #5. OpenMinion 0.1.22 runs the real NVIDIA NIM model, executes the scanner tool, delegates remediation review, gates a repository write, and persists sessions and regression memory.

## Setup

Python 3.11+ and a NVIDIA NIM API key are required. Tested locally with Python 3.14 on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set NVIDIA_API_KEY in .env using your editor.
Copy-Item fixtures/sample.env.example sample_target/.env
python -m minion_audit scan ./sample_target
```

On macOS/Linux, activate with `source .venv/bin/activate` and copy with `cp .env.example .env` and `cp fixtures/sample.env.example sample_target/.env`. Run from the project root. If `.env` is already configured, do not overwrite it.

`requirements-lock.txt` captures the exact installed versions from the verified Windows environment. Use `python -m pip install -r requirements-lock.txt` to reproduce that dependency set.

The demo includes fake credentials and unsafe code; never execute or deploy the sample. The real application key belongs only in the root `.env`. Every `.env` file is ignored, including the local sample fixture. Only placeholder/example files are published; setup copies the deliberately fake fixture into the sample target.

## Workflow

1. The SDK scanner agent calls a typed, read-only `scan_repository` tool. It skips dependency folders, generated state, links, and files over 1 MB; coverage gaps are reported.
2. A bounded OpenMinion subagent with no tools reviews redacted findings. The app ingests and retrieves its bundled review skill through the SDK skill store, then explicitly passes its procedure to this reviewer.
3. If a `.env` file is present, the SDK requests permission to append `.env` to the target's `.gitignore`. Type `yes` to approve exactly that write, or `no` to deny. EOF denies. Every other confirmation is denied. This edit does not untrack secrets or rotate credentials.
4. A complete scan stores finding fingerprints in OpenMinion memory under a scope derived from the canonical target path. The next scan reports new and resolved findings. Partial scans never replace the baseline.
5. Open `reports/audit_report.html`. It is a single file with inline CSS and JavaScript, filtering, remediation advice, and actual SDK statistics and telemetry. A JSON companion supports inspection.

```powershell
python -m minion_audit scan ./sample_target --no-fix
python -m minion_audit inspect audit-SESSION_ID
python -m minion_audit scan ./sample_target --session audit-SESSION_ID
python -m unittest discover -s tests -v
```

Session continuation reuses the SDK history and re-scans current files. It restarts the bounded workflow rather than resuming an arbitrary Python instruction. Interrupted run snapshots live in `.minion_audit/runs/`; SDK sessions, memory, skill versions, and telemetry are under `.minion_audit/`. These are ignored, as are generated reports.

## What is checked

| Rules | Candidates |
| --- | --- |
| SEC001–002 | Secret-like assignments, common key patterns, private keys, mnemonic/seed assignments, `.env` presence |
| SOL001–004 | `tx.origin`, low-level calls requiring success/reentrancy review, pre-0.8 pragmas, sensitive public entry points |
| PY001–003 | AST-detected `eval`/`exec`, common subprocess shell usage, unsafe YAML loading |
| DEP001 | Unpinned entries in `requirements.txt` |

This is a bounded heuristic auditor. Solidity matching is line-based; it cannot prove missing access control, unchecked calls, or exploitability. Python alias resolution is limited. It does not execute the target, analyze dependency advisories, or guarantee complete secret detection. Rule IDs and line locations are deterministic; remediation text comes from the real model and requires review.

Only redacted finding records reach NIM. The model reviews at most the first 100 candidates per scan; the report and regression baseline retain every scanner finding. Repository paths and findings remain in local reports and SDK storage. Scanning is local; model-backed remediation requires network access. There is no simulated model fallback. Provider errors produce a failed report and exit code 2; completed scans exit 0 even when findings exist.

## Reproducibility

`agents.json` pins the OpenAI-compatible endpoint `https://integrate.api.nvidia.com/v1`, model `nvidia/nemotron-3.5-lightning-30b-a3b`, native tool calling, zero temperature, and permission policy. Both originally requested models returned HTTP 410; Nemotron is the user-selected replacement. SDK source inspected: official [v0.1.22](https://github.com/OpenMinion/openminion/tree/v0.1.22), commit `bf7cc18d15abd059ec130f50aa80ecb2ec5c5305`. Optional source checkout for inspection:

```powershell
git clone --depth 1 --branch v0.1.22 https://github.com/OpenMinion/openminion.git vendor/openminion
```

See [NOTES.md](NOTES.md) for verified behavior and SDK friction. Run twice to demonstrate memory. Adding an ignore rule does not remove the `.env` finding: it still requires review. To demonstrate resolved findings, fix one unsafe expression in a copy of the sample, then scan that same copy again.
