# Security

## Credentials and local data

Store the real NVIDIA NIM key only in the root `.env`. Every `.env` file is ignored, including the generated sample environment file. Public example files contain placeholders or deliberately fake fixture values.

Generated reports, SDK databases, session snapshots, and local dependencies are ignored. They can contain repository paths, findings, and model output; review them before sharing them separately.

MinionAudit sends redacted finding records to NVIDIA NIM for model-backed review. Its only supported repository edit requires terminal approval and appends `.env` to `.gitignore`. Ignoring a file does not untrack it, remove Git history, or rotate an exposed credential.

## Reporting a vulnerability

For a suspected credential leak, permission bypass, unsafe filesystem write, or report injection issue, contact the maintainer privately through GitHub. If the repository offers **Security → Report a vulnerability**, use that private channel. Do not put live credentials, private source code, or an unredacted exploit target in a public issue.

For ordinary rule false positives, use a minimal synthetic example in an issue. Include the MinionAudit version, Python version, rule ID, and expected behavior.
