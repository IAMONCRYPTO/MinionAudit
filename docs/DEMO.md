# Demo and verification

This record describes observed local execution. Model availability, timing, and wording can vary on later runs.

## Reproduce the demo

1. Follow the platform setup in the [README](../README.md), including copying the fake environment fixture.
2. Run `python -m minion_audit scan ./sample_target`.
3. Enter `no` at the write prompt and open `reports/audit_report.html`.
4. Run the same command again. Enter `yes` to test the allowed write.
5. Check the regression line and the SDK diagnostics drawer.

The sample is deliberately unsafe. Read it as fixture data; do not run its Python code or deploy its contract.

## Observed real-model runs

| | First completed run | Second completed run |
| --- | --- | --- |
| Session | `audit-a6d73f9bee724345` | `audit-91ebc5f4c1a14d10` |
| Duration, including operator wait | 85.252 s | 126.312 s |
| Files scanned | 3 | 3 |
| Findings | 2 Critical / 9 High / 1 Medium | 2 Critical / 9 High / 1 Medium |
| Permission decision | `DENY` | `ALLOW` |
| Repository write | No `.gitignore` created | Literal `.env` rule added |
| Regression memory | Baseline stored | Prior baseline recalled; 0 new / 0 resolved |

Both runs used OpenMinion 0.1.22 and the real NVIDIA NIM model `nvidia/nemotron-3.5-lightning-30b-a3b`. The runtime executed the scanner tool and a bounded remediation subagent. Reports contain SDK result statistics, metadata, and session telemetry alongside application-recorded tool and permission events.

In the second run, the SDK reported 7 LLM calls / 1 tool call for scanning, 3 LLM calls for the child review, and 5 LLM calls / 1 tool call for the approved-fix turn. This overhead is documented in the [SDK feedback](../NOTES.md).

## Demonstrate a resolved finding

Work in a copy of the sample. Scan that copy once, replace `eval(user_input)` with a safe implementation, then scan the **same path** again. Its removed scanner candidate should count as resolved. Fixing an ignore rule alone does not resolve credential candidates.

## Validation scope

- Six local unit tests passed without model calls.
- A separate runtime check wrote structured SDK memory, closed the runtime, reopened it, and recalled the record.
- The saved successful session passed the actual `inspect` CLI check.
- HTML structural validation found 12 finding articles, 4 filters, 1 diagnostics drawer, and zero external asset references.
- Secret-bearing sample lines were withheld from finding snippets. Before publication, staged Git blobs were checked against the real local credential.
- Browser visual QA was unavailable because the browser tool blocked local `file://` previews. The structural checks are not a screenshot-based layout certification.

## Submission walkthrough

Show the scan command, the exact terminal permission request, and its decision. Open the report, filter by severity, then expand the diagnostics drawer. Finish with the second-run memory comparison and the concrete friction recorded under **Building Blocks Tested** and **What We Learned** in [NOTES.md](../NOTES.md).
