# Contributing

Thanks for your interest in contributing! This document explains the workflow and the
checks your change must pass. The default branch is protected — all changes land via
**pull request**.

## Quick start

1. **Fork** the repo (external contributors) or create a branch (collaborators).
2. Create a topic branch: `feat/<short-name>`, `fix/<short-name>`, or `chore/<short-name>`.
3. Make your change with clear, focused commits.
4. Open a **pull request** against the default branch and fill out the template.

## Branch protection — what your PR must satisfy

The default branch enforces a ruleset ("Protect default branch"):

- **No direct pushes, no force-pushes, no branch deletion.**
- **1 approving review** is required, including review from a **code owner** (see `CODEOWNERS`).
- **Conversations must be resolved** before merge.
- **Re-approval after new pushes** (stale approvals are dismissed).
- **Status checks must pass** — the **Harden Gate** workflow runs:
  `lint`, `test`, `build`, `sast` (Semgrep), `secret-scan` (gitleaks), `dependency-scan` (Trivy).
- **Commits must be signed** (`required_signatures`). See below.

## Signed commits

All commits on the default branch must be verified/signed. The easiest setup is SSH signing:

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
```

Then add the key as a **Signing Key** in GitHub → Settings → SSH and GPG keys.
Commits made through the GitHub web UI/API are signed automatically.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`
(`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, …).

## Code of Conduct

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Reporting security issues

See [SECURITY.md](SECURITY.md) — do **not** open public issues for vulnerabilities.
