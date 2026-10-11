# Contributing

This is an experimental independent Go runtime. Read `docs/STATUS.md` before proposing a feature.
Keep changes small and reviewable; add unit tests, failure/replay tests, API/docs updates and an
explicit account of which integration tests actually ran. Do not change unsupported capabilities
to "ready" by adding a flag or successful fixture response.

Run `go test -race -count=1 ./...`, `go vet ./...`, JavaScript syntax checks,
`python3 -m unittest discover -s tests/release -v`, and the public-source lint.
Docker/etcd fixtures are not a substitute for actual runtime tests.

Contributions are under Apache-2.0. Use a Signed-off-by line (`git commit -s`) to attest you have
the rights to submit the contribution. No separate CLA is introduced by this file. Retain relevant
copyright/NOTICE attribution; do not import proprietary code or deploy credentials.

Do not run privileged VM scripts on shared or production hosts. Fork PRs must never receive
production secrets or privileged self-hosted runners. No pull_request_target checkout of untrusted code.
Provide sanitized evidence only; never upload PKI, join bundles, backups or secret files.

Issue IDs in ROADMAP are plan references, not live GitHub issues. Never close a task because
only interfaces, documentation or test doubles exist. Critical control-plane/host/security paths
require a reviewer other than the implementer before production qualification.
