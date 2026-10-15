# Repository hardening (without mandatory signed commits)

Project: `JossefMo1/Werftkern_Kubernetes`
Default branch: `main`
Visibility: PUBLIC since 2026-10-15, changed by the repository owner after
source/history checks and launch review. Production qualification remains
blocked; public source availability is not production approval.
**Commit GPG/SSH signatures must remain OPTIONAL.** Do not turn on
`Require signed commits` or `Commits must have verified signatures`.

## Verified public-repository settings (2026-10-15)

- `main` is covered by the active `Protect main` ruleset.
- Direct deletion and non-fast-forward updates are blocked.
- Pull requests, one approval, CODEOWNERS review, stale-review dismissal,
  last-push approval and conversation resolution are required.
- `publication-audit`, `contracts`, `test` and `real-etcd` are required checks
  for the default branch.
- Actions default permissions are read-only and Actions cannot approve reviews.
- Dependabot security updates, secret scanning, push protection and private
  vulnerability reporting are enabled.
- An independent reviewer still needs access before issue #7 can be closed.

## Controls already stored in the source repository

- `.github/CODEOWNERS` routes high-risk changes to `@JossefMo1`.
  It does **not** technically require approvals without a GitHub ruleset.
- Workflows use `permissions: contents: read` and
  `persist-credentials: false` for checkout; private keys must never be
  made accessible to fork PRs.
- CI checks source and Git history for selected secret patterns; the
  production-readiness gate remains deliberately BLOCKED.
- Dependabot is scheduled weekly for GitHub Actions and Go modules.
- The missing dev.3 historical commit is recorded as **compatibility
  BLOCKED in ordinary CI**, not converted into fictional test success.
  A separately supplied verified bundle can support an explicitly opted-in
  local test; see `validation/LOCAL-DEV3-DEV4-COMPAT.md`.
- Public source prereleases alpha.1, alpha.2 and alpha.3 exist. They do not
  imply signed binaries, production readiness or Kubernetes certification.

## Remaining administrator and reviewer actions

I. Reconfirm the settings above after any repository-plan or ownership change.
Keep Actions' workflow permissions read-only by default, and allow GitHub
Actions to create/approve PRs only if demonstrably needed.
Restrict/review who can register self-hosted runners; keep permanent
production machines completely out of untrusted code paths.

II. **Branch protection / rulesets**, when available for the plan:
  - Target `main` and stable release/tag refs.
  - Require pull requests instead of direct pushes (including owner where
    supported), required passing status checks for the selected stable
    CI job names (publication-audit, contracts, test, real-etcd), and
    require conversation resolution.
  - Require code-owner reviews; at least one *independent* reviewer
    must have access. GitHub does not count self-approval. If working
    alone, invite a trusted reviewer before enforcing this policy.
  - Dismiss stale approvals on changed code; block force pushes,
    branch deletion and bypass access for non-maintainers.
  - **Do not enable Require signed commits**. Both signed and unsigned
    commits should be allowed if all other gates pass.
  - Confirm by opening the `main` branch details: `protected:true`
    and the expected required checks should actually appear.

III. Keep security-advisory reviews and a confidential vulnerability-report
channel operational; do not post exploit details in public issues.

## Important plan/permission limitation

The 2026-10-12 private-repository snapshot recorded unavailable rulesets and
private vulnerability reporting. After the owner changed visibility to PUBLIC
on 2026-10-15, the ruleset and public security controls became configurable and
were verified as listed above. Source files alone do **not** enable branch
protection; re-check the live settings after administrator changes.

## Release blockers

- The canonical Go module migration (issue #6) is merged. Revalidate it on
  the chosen launch commit. The initial private alpha.1 tag contains the original
  module path; never change an existing release tag to hide that history.
- Obtain authorization for code derived from the existing project and
  check third-party license notices.
- Perform independent source/history secret and security checks;
  rotate any exposed credentials before publication.
- Confirm all expected CI checks for the exact target SHA.
- Qualify real Kubernetes, HA, storage, recovery and cloud operations
  before any production claim. Alpha-only documentation can explicitly
  state that these are not qualified.

See [the launch checklist](OPEN-SOURCE-LAUNCH-CHECKLIST.md) and
[draft release notes](../releases/v0.1.0-alpha.1.md).
