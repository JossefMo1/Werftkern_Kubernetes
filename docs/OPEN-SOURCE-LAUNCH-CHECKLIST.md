# Werftkern Open-Source Launch Gate

Target repository: `JossefMo1/Werftkern_Kubernetes`
Target first release: `v0.1.0-alpha.1` (**experimental source-only pre-release**).

**Default decision: HOLD.** Do not change visibility, create a tag, publish
release artifacts, or call a version production-ready just because these
instructions exist.

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
- [ ] **Repository identity**: decide the permanent import path and migrate
  the `github.com/ClusterPilot-System/werftkern` Go module/import references
  to the actual hosted path (or document a deliberate canonical redirect).
  Re-run all build, test and packaging checks.
- [ ] **CI results**: verify green checks for the exact commit on the proposed
  tag, including `publication-audit`, Go/race/vet, Python suites, Kubernetes
  backend contracts and package builds. A workflow file is not a passed run.
- [ ] **Version truth**: ensure the source, package and CLI identify their
  actual component versions. `v0.1.0-alpha.1` is the umbrella source tag;
  do not silently rename native `0.2.0-dev.4` or Kubernetes `0.1.0-dev.3`.
- [ ] **Security settings**: enable Dependabot alerts and least-privilege
  Actions permissions now. Protect `main` with PR reviews and status checks
  if the current GitHub plan permits private-repository rules; verify its
  protections immediately upon PUBLIC conversion otherwise. Enable available
  GitHub secret scanning and push protection on the public repository; use
  an independent history scanner *before* publication because the GitHub
  repository's private-plan features may be limited. Private vulnerability
  reporting can be enabled only on PUBLIC repositories, so prepare a
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

## First source-only alpha release (only AFTER the checklist passes)

From a clean local checkout of the reviewed `main` commit:

```bash
git fetch --all --tags
git switch main
git pull --ff-only
python3 scripts/check-public-source.py
python3 scripts/audit-git-history.py --require-noreply
git tag -a v0.1.0-alpha.1 -m "Werftkern experimental source alpha 1"
git push origin v0.1.0-alpha.1
gh release create v0.1.0-alpha.1 --verify-tag --prerelease \
  --title "Werftkern v0.1.0-alpha.1 (experimental source)" \
  --notes-file releases/v0.1.0-alpha.1.md
```

Make GitHub repository visibility PUBLIC only after the same checks.
Do not attach unsigned packages as verified binaries. Create a future
production release only after the separate qualification gates pass.

## Evidence and rollback

Record reviewer/date/commit ID, CI URLs, secret-scan results, copyright
approval and branch-protection settings in a private release decision
record (never commit confidential raw evidence). If a blocker appears,
stop; do not tag or publish. Revoking a published release or deleting a
GitHub ref does **not** reliably retract previously downloaded sources.
