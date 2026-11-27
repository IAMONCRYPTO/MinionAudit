# Contributing

Start with the setup in [README.md](README.md). Scanner and report tests run without API credentials:

```bash
python -m unittest discover -s tests -v
```

Keep changes focused. A scanner rule should identify a concrete review candidate, provide an actionable fix, and avoid presenting a heuristic as a confirmed exploit. Preserve stable rule IDs and finding fingerprints where practical.

Use temporary fixtures for tests. Add regression coverage when changing redaction, traversal boundaries, repository writes, or comparison behavior. Never execute the intentionally vulnerable sample.

When changing the SDK integration, inspect the pinned release source before modifying imports, config, or runtime calls. Record observed SDK friction in [NOTES.md](NOTES.md). Distinguish credential-free tests from real provider verification; do not label a mock or echo run as a real-model run.

Before publishing, inspect `git diff --cached`, run the tests, and confirm that `.env`, reports, credentials, and local SDK state are absent from the staged files. Report security issues using [SECURITY.md](SECURITY.md).
