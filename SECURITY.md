# Security policy

## Support status

Current sources contain experimental Werftkern Kubernetes 0.1.0-dev.3 and the separate Native Runtime 0.2.0-dev.4. **No version is production-supported.**
Do not deploy customer data, production credentials, payment workers or untrusted tenants.
No response-time SLA or 24/7 security team is claimed.

See [the public-launch safety gate](docs/OPEN-SOURCE-LAUNCH-CHECKLIST.md) before changing repository visibility or tagging a release.

## Private reporting

The repository owner should enable GitHub private vulnerability reporting before public launch.
Use **Security → Report a vulnerability** when that option exists. If it is unavailable, request
an appropriate private reporting channel without posting exploit details, keys or customer data
in a public issue. This policy does not invent an email address or an already operating security team.

## Trust model

One trusted administrator/cluster. Nodes receive their own client certificates and may read only
assigned allocations and referenced secret versions. mTLS authentication is not multi-tenant RBAC.
Host root / Docker-socket access can compromise that host and its workloads. Container isolation
shares the host kernel; hostile multi-tenancy is unsupported.

Read-only rootfs, non-root workload UID, dropped capabilities, bounded resources and no-new-privileges
are configured in the Docker adapter. Actual enforcement must be qualified on the target daemon/kernel.
Workload secrets use versioned AES-256-GCM ciphertext bound to cluster/name/version. Their key is a
random 32-byte protected local file. Agent materialization requires a tmpfs root, private host
parent and read-only bind. Revocation cannot erase a value already delivered to an isolated host.
Applications can deliberately log values; there is no universal redaction guarantee.

## Disclosure and release process

Reproduce on disposable infrastructure; keep evidence access-controlled; add regression tests;
review the affected trust boundary; independently retest; publish a security advisory only after
responsible coordination. A unit test, scanner or mutable JSON checklist is not security approval.

Before production: current compiler/dependency review, real container/etcd/Ubuntu tests,
certificate lifecycle, API/node isolation, backup/restore, network policy, failure/soak testing,
independent assessment, protected CI approvals and signed release provenance.
See `release/qualification.json` and `docs/STATUS.md` for missing evidence.

## Werftkern additions (0.2.0-dev.2)

New root-affecting operations are experimental: HA kit import, WireGuard/routes, node-bound volumes, PostgreSQL restore, SSH bootstrap and signed controller updates. Peer-network, cloud, database and installer behavior has not been independently assessed. Never run operations from untrusted forks or archives. Restore only trusted database dumps. Local volume ownership is not physical fencing. Review `docs/STATUS.md`, `docs/NETWORK.md` and `docs/RECOVERY.md` before enabling these paths. Keep private kits, cloud tokens, PG passfiles, vault material and backup keys out of the public source tree. An installed unsupported lab compiler binary is not a production-supported release.

## Dev.2 trust boundaries

Gateway identities are service-scoped, not administrators. Edge TLS terminates before
private HTTP upstreams; private IP alone is not encryption. Revocation takes effect
on refresh/freshness expiry, not instantly on an isolated node. Volume archives use
new authenticated framing and must receive independent cryptographic/file traversal
review. Backup requires a quiescent trusted host and does not fence other writers.
Schema2 requires exact agent versions and an explicit offline migration. Never erase
pending-restore or ordering fields to bypass recovery. Default unknown-node replacement
retains reservations; node revocation is not physical fencing.
