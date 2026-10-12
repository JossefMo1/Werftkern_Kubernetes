# Contributing

This is an experimental Go runtime with a separate Python/k0s Kubernetes manager.
Read [the README](README.md), [native status](docs/STATUS.md),
[Kubernetes guide](docs/kubernetes/README-DE.md) and
[code of conduct](CODE_OF_CONDUCT.md) before proposing a feature.
Keep changes small and reviewable; add unit tests, failure/replay tests, API/docs updates and an
explicit account of which integration tests actually ran. Do not change unsupported capabilities
to "ready" by adding a flag or successful fixture response.

Develop and validate on Linux (Ubuntu 24.04 LTS is the installation target).
Choose checks for the changed code and its consumers; the CI workflows own the
complete source/package checks. For the relevant suites:

```sh
go test -race -count=1 ./...
go vet ./...
python3 -m unittest discover -s tests/ops -v
PYTHONPATH=ops python3 -m unittest discover -s tests/kubernetes -v
python3 -m unittest discover -s tests/release -v
python3 scripts/check-public-source.py
python3 scripts/audit-git-history.py
node --check internal/dashboard/assets/app.js
```

Go builds require a supported compiler; package builds also enforce the
toolchain policy in `scripts/build-deb.sh`. Windows may lack symlink privileges
or Linux process/file semantics; use Linux/WSL rather than weakening tests.
Docker/etcd fixtures are not a substitute for actual runtime tests.

Contributions are under Apache-2.0. Use a Signed-off-by line (`git commit -s`) to attest you have
the rights to submit the contribution. No separate CLA is introduced by this file. Retain relevant
copyright/NOTICE attribution; do not import proprietary code or deploy credentials.

Signed-off-by is a contribution rights attestation, not a GPG/SSH signature.
Cryptographic commit signatures remain optional. Use a feature branch and PR,
explain compatibility and rollback, and link the exact validation results.

Do not run privileged VM scripts on shared or production hosts. Fork PRs must never receive
production secrets or privileged self-hosted runners. No pull_request_target checkout of untrusted code.
Provide sanitized evidence only; never upload PKI, join bundles, backups or secret files.

Issue IDs in ROADMAP are plan references, not live GitHub issues. Never close a task because
only interfaces, documentation or test doubles exist. Critical control-plane/host/security paths
require a reviewer other than the implementer before production qualification.
