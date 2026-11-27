# MinionAudit

**Local repository security review for Solidity, Python, and AI agent code.**

MinionAudit combines deterministic security checks with a real OpenMinion agent workflow: scan the repository, delegate remediation review, request permission for a bounded fix, and compare the next run with durable memory.

Built for **Cortensor Hackathon #5**.

**Python 3.11+** · **OpenMinion 0.1.22** · **NVIDIA NIM** · **Local HTML reports**

[Quick start](#quick-start) · [Verified demo](docs/DEMO.md) · [Architecture](docs/ARCHITECTURE.md) · [SDK feedback](NOTES.md)

## What you get

| Stage | Result |
| --- | --- |
| **Scan** | Rule IDs, severity, exact `file:line`, redacted snippets, and suggested fixes. |
| **Review** | A bounded OpenMinion subagent prioritizes remediation using the bundled review skill. |
| **Approve** | A terminal prompt gates the only repository edit: adding `.env` to `.gitignore`. |
| **Compare** | SDK memory tracks new and resolved findings for the same repository. |
| **Inspect** | A self-contained HTML report includes filters, model advice, and SDK diagnostics. |

## Quick start

You need Python 3.11+ and a NVIDIA NIM API key. Run these commands from the cloned repository. Keep an existing configured `.env` when repeating setup.

### Windows · PowerShell

```powershell
git clone https://github.com/IAMONCRYPTO/MinionAudit.git
cd MinionAudit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item fixtures/sample.env.example sample_target/.env
```

### macOS / Linux

```bash
git clone https://github.com/IAMONCRYPTO/MinionAudit.git
cd MinionAudit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
cp fixtures/sample.env.example sample_target/.env
```

Edit the root `.env` and set your key:

```dotenv
NVIDIA_API_KEY=your_nvidia_nim_key
```

Then run the real-model demo:

```bash
python -m minion_audit scan ./sample_target
```

When the permission prompt appears, enter `yes` or `no`. Open **`reports/audit_report.html`** after completion. The report works directly from disk with no build step or external assets.

<details>
<summary>Serve the report on localhost</summary>

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory reports
```

Open [localhost:8000/audit_report.html](http://localhost:8000/audit_report.html). This serves only the report directory. Start scans through the CLI and refresh the browser after each completed run.

</details>

## Verified demo output

Two real NIM runs completed with the supplied sample. The recorded results include both permission decisions and persistent memory recall. See the [verification record](docs/DEMO.md) for run IDs, timings, and test scope.

```text
Scan tool: 3 files / 12 candidates
Delegating remediation review...

Critical: 2  |  High: 9  |  Medium: 1
Previous run: 12 issues -> Current run: 12 issues (0 resolved, 0 new)
Status: complete
```

Adding an ignore rule leaves the finding count at 12: the environment file and its credentials still need review. A finding becomes resolved when its scanner candidate is removed on a subsequent complete scan.

## Audit your repository

```bash
# Scan a local code directory
python -m minion_audit scan /path/to/repository

# Scan and review without offering the repository edit
python -m minion_audit scan /path/to/repository --no-fix

# Read a saved run without calling the model
python -m minion_audit inspect audit-SESSION_ID

# Reuse SDK session history and re-scan current files
python -m minion_audit scan /path/to/repository --session audit-SESSION_ID
```

Use a quoted Windows path such as `"C:\Projects\my-repo"` when needed. Session continuation restarts the bounded workflow with SDK history; it does not restore an arbitrary interrupted Python instruction.

| Output | Location |
| --- | --- |
| Browser report | `reports/audit_report.html` |
| Structured report | `reports/audit_report.json` |
| Inspectable run snapshots | `.minion_audit/runs/` |
| SDK sessions, memory, skills, telemetry | `.minion_audit/` |

Completed scans exit **0**, including scans with findings. Failed or partial scans exit **2**. The most recent scan replaces the report files; per-session snapshots remain available locally.

## Checks and limits

| Rules | Review candidates |
| --- | --- |
| `SEC001–002` | Secret-like assignments, common key formats, private keys, seed/mnemonic assignments, and `.env` presence. |
| `SOL001–004` | `tx.origin`, low-level calls, pre-0.8 pragmas, and sensitive public functions needing authorization review. |
| `PY001–003` | AST-detected `eval` / `exec`, common subprocess `shell=True` usage, and unsafe YAML loading. |
| `DEP001` | Unpinned entries in `requirements.txt`. |

The scanner reads supported text files and skips dependency directories, generated state, links, and files larger than 1 MB. Coverage gaps appear as warnings and prevent the baseline from being replaced.

Findings are **heuristic review candidates**. Solidity checks are line-based and cannot establish exploitability, inherited access control, or complete call-result handling. Python alias resolution is limited. The tool does not execute target code, inspect dependency advisories, or guarantee that every secret is detected.

Only redacted finding records are supplied to NIM for remediation review. The model reviews the first 100 candidates; the report and regression baseline retain every scanner finding. Model guidance requires human review. Provider failures remain visible, with no simulated model fallback.

## Configuration and reproducibility

`agents.json` configures the OpenAI-compatible NIM endpoint, native tool calling, and SDK approval policy.

| Setting | Pinned value |
| --- | --- |
| SDK | `openminion==0.1.22` |
| Provider URL | `https://integrate.api.nvidia.com/v1` |
| Model | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| Credential | `NVIDIA_API_KEY` from the local `.env` |

Both originally requested models returned HTTP 410 during testing. The verified runs used Nemotron, selected as their replacement. Exact SDK quirks and improvement suggestions are documented in [NOTES.md](NOTES.md).

`requirements-lock.txt` records the dependency versions from the verified Windows / Python 3.14 environment. Use `python -m pip install -r requirements-lock.txt` to reproduce that set. The SDK source was inspected at [v0.1.22](https://github.com/OpenMinion/openminion/tree/v0.1.22), commit `bf7cc18d15abd059ec130f50aa80ecb2ec5c5305`.

## Repository map

```text
minion_audit/       CLI, SDK orchestration, scanner tools, HTML reporting
sample_target/      Intentionally vulnerable Solidity and Python fixtures
fixtures/           Fake environment fixture copied during demo setup
skills/             Bundled remediation review procedure
tests/              Scanner, regression, file-safety, and escaping checks
docs/               Demo evidence and implementation guide
agents.json         Provider and permission configuration
NOTES.md            OpenMinion building-block feedback
```

## Development

```bash
python -m unittest discover -s tests -v
```

The six local tests require no API key or model calls. They cover planted detections, redaction, AST handling, stable fingerprints, regression counts, safe writes, hard-link refusal, and report escaping. The hard-link fixture needs a filesystem that permits temporary hard links; a restricted execution sandbox may block its creation.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and [SECURITY.md](SECURITY.md) for credential handling and vulnerability reports.
