# Werftkern Open-Source Launch Gate

Target repository: `JossefMo1/Werftkern_Kubernetes`
Existing private source prereleases: `v0.1.0-alpha.1` and `v0.1.0-alpha.2`.
Current alpha selector: `release/alpha-version.txt` (`v0.1.0-alpha.2`).

**Default decision: HOLD for PUBLIC publication and production.**
A separate GitHub Actions workflow may create a **PRIVATE, source-only,
experimental** pre-release selected by `release/alpha-version.txt` once all three defined CI workflows
succeed for the exact current main commit. No binaries or external distribution
are authorized. The private alpha does not replace the requirements below
for a future PUBLIC release. Never label it production-ready.

## Required checks (must be recorded by a maintainer)

- [ ] **Ownership and IP**: verify permission to redistribute each reused
  ClusterPilot-derived file and design under Apache-2.0, including employment,
  contributor and third-party rights. Review `NOTICE.md`,
  `THIRD_PARTY_NOTICES.md`, dependency licenses and the Git history.
- [ ] **Source + history secrets**: in a fresh full-history clone run
  `python3 scripts/check-public-source.py` and
  `python3 scripts/audit-git-history.py --require-noreply`.
  These are heuristics. Independently scan full history with a maintained
  secret scanner and manually check configurations, cloud IDs, incident
  reports, personal data, SSH keys, backups and credentials.
- [ ] **On any exposure**: rotate/revoke exposed credentials BEFORE any
  public visibility change; rewrite or replace contaminated history with
  documented authorization. `.gitignore` and deleting a current file do
  not remove a secret from old commits. Re-scan all reachable refs.
- [x] **Repository identity at reviewed baseline `45c8306`**: canonical module,
  imports and linker flags use `github.com/JossefMo1/Werftkern_Kubernetes`.
  The migration was merged as `8b20f60` (issue #6). Preserve the old alpha.1
  tag; verify focused identity tests and exact-SHA CI again on the launch commit.
- [ ] **CI results**: verify green checks for the exact commit on the proposed
  launch commit, including `publication-audit`, Go/race/vet, Python suites, Kubernetes
  backend contracts and package builds. A workflow file is not a passed run.
- [ ] **Version truth**: ensure the source, package and CLI identify their
  actual component versions. Alpha tags identify the umbrella source release;
  do not silently rename native `0.2.0-dev.4` or Kubernetes `0.1.0-dev.3`.
  Review BOTH existing releases and every public branch/tag. A visibility change
  does not update their notes or move their immutable source commits.
- [ ] **Security settings**: enable Dependabot alerts and least-privilege
  Actions permissions now. Protect `main` with PR reviews and status checks
  if the current GitHub plan permits private-repository rules; verify its
  protections immediately upon PUBLIC conversion otherwise. Enable available
  GitHub secret scanning and push protection on the public repository; use
  an independent history scanner *before* publication because the GitHub
  repository's private-plan features may be limited. Private vulnerability
  reporting was unavailable on the reviewed PRIVATE repository, so prepare a
  confidential interim channel and enable GitHub reporting immediately
  after the repository becomes public.
- [ ] **Threat model + scope**: review root/SSH, cloud deletion, fencing,
  credentials, SSL termination, snapshot restore and upgrade contracts. No
  production claims without independent assessment.
- [ ] **Human release review**: verify the notes match the exact commit and
  the project is clearly labeled experimental/non-CNCF-certified.
  Publication requires repository-owner approval.

## Checks that must remain BLOCKED for production

`python3 scripts/check-release.py --commit "$(git rev-parse HEAD)"`
is expected to report `BLOCKED` because the production evidence gates
are incomplete. **Do not edit JSON flags to make it pass**. Production
qualification requires separate real-world evidence and independent review.

## Public visibility change (only AFTER all checks pass)

The internal alpha is produced automatically by `.github/workflows/auto-alpha-release.yml`
while the repository stays private. This section applies solely when approving
PUBLIC distribution later. From a clean checkout of the reviewed `main` commit:

```bash
git fetch origin --tags
git switch main
git pull --ff-only
python3 scripts/check-public-source.py
python3 scripts/audit-git-history.py --require-noreply
gh release view v0.1.0-alpha.1
gh release view v0.1.0-alpha.2
```

Do not recreate or move either existing tag. Record the reviewed main SHA,
all refs/releases in scope, exact-SHA CI and remaining human approvals.
The private-alpha automation deliberately refuses to publish when PUBLIC;
future public releases need a separately reviewed release workflow.

Make GitHub repository visibility PUBLIC only after independent ownership,
secrets/history and security review plus the effective branch protections.
A PRIVATE source alpha is not that approval.
Do not attach unsigned packages as verified binaries. Create a future
production release only after the separate qualification gates pass.

## Evidence and rollback

Record reviewer/date/commit ID, CI URLs, secret-scan results, copyright
approval and branch-protection settings in a private release decision
record (never commit confidential raw evidence). If a blocker appears,
stop; do not tag or publish. Revoking a published release or deleting a
GitHub ref does **not** reliably retract previously downloaded sources.

## Latest inspection

See [the dated publication review](validation/PUBLICATION-REVIEW-2026-10-12.md).
It records executed checks and actual GitHub settings. Green heuristic checks
do not clear ownership, comprehensive secrets review or production gates.
