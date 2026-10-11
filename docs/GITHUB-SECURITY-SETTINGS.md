# Repository hardening (without mandatory signed commits)

Project: `JossefMo1/Werftkern_Kubernetes`
Default branch: `main`
Visibility: PRIVATE until copyright / secret / security sign-off.
**Commit GPG/SSH signatures must remain OPTIONAL.** Do not turn on
`Require signed commits` or `Commits must have verified signatures`.

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
  BLOCKED**, not converted into fictional test success.
- First alpha release notes are drafted but do not imply a published
  tag, security attestation or official Kubernetes certification.

## GitHub settings that require administrator UI access

I. **Before the public launch**, use Settings -> Security / Code security
to enable available Dependabot alerts and automatic security updates.
Enable secret scanning/push protection if the current plan permits it.
Configure Actions' workflow permissions as read-only by default, and
allow GitHub Actions to create/approve PRs only if demonstrably needed.
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

III. **After publication as PUBLIC** (only after launch checks):
  - Enable GitHub private vulnerability reporting via Settings ->
    Security -> Private vulnerability reporting.
  - Enable GitHub secret scanning and push protection where available.
  - Re-check that rulesets/branch protections *apply* to the now-public
    repository, and test a sample PR without a verified commit signature.
  - Enable security advisory reviews and maintain a confidential
    vulnerability-report channel, without posting exploit details.

## Important plan/permission limitation

The current GitHub integration cannot modify repository admin
settings or branch rules. At the time these instructions were written,
GitHub reported `main.protected=false`; rulesets returned HTTP 403
(Upgrade to Pro or make public), and the branch protection endpoint was
not accessible by the integration. This means source files alone do
**not** mean server-side protection is enabled.

## Release blockers

- Correct the canonical Go module and imports.
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
