# Release status — 0.2.0-dev.4

**NOT_PRODUCTION_READY. Full masterplan incomplete. State schema 2.**

The authoring-environment observations below are historical, including the
compiler version and whether CI had run at that time. For subsequently verified
GitHub CI and public-source preparation, see
[the dated publication review](validation/PUBLICATION-REVIEW-2026-10-12.md).
That review does not qualify the production features listed here.

## Implemented in this increment

Owned sequential worker rollout, separately authorized node maintenance reads and drain,
signed remote staging, conservative uncertain-install recovery, local Docker-smoke command,
restarted observation windows, identity-bound final unlock and a narrowly supported
dev.3-agent/dev.4-controller compatibility edge. Stale probe observations no longer
count as ready in scheduling or discovery. Paused applications require zero live executions.

Both previous and new agent executables were actually built and started using a real
persistent local journal, real TLS and OS processes. The Docker endpoint and etcd store
were fixtures. This is stronger than changing a version string, but NOT real container,
Ubuntu, SSH, hardware, quorum or production upgrade evidence.

All controllers must already be dev.4 before a dev.3 worker wave starts. General mixed
versions, old controllers accepting new agents, automated controller waves and the
historical dev.2→dev.3 edge are not supported by this compatibility test. Active pinned
or local-volume workloads require separately planned offline maintenance, not forced drain.

## Inherited integrations and boundaries

Native three-host PostgreSQL17/Patroni4 with mandatory watchdog and independent etcd DCS;
pgBackRest/POSIX encrypted backup and PITR adapter; offline CA leaf renewal and combined-PEM
live reload; physical encrypted local-volume archives; own Go TLS ingress; HA/mesh/DNS/
Hetzner tooling. These are not independently qualified multi-host production services.
Database HA runs on dedicated native hosts, not in the ordinary Docker scheduler.
File restore, actual WAL replay and business validation remain separate gates.

## Still missing or unqualified

Replicated generic storage/CSI; qualified physical fencing; complete site-wide DR;
integrated database service lifecycle; production NetworkPolicy and HA ingress endpoint;
full CA rotation/online issuer; automated controller upgrade orchestration; direct
containerd; IONOS/ClusterPilot connector and broader roadmap features. No model size
limit is a measured scalability claim. No SLA/RPO/RTO commitment.

Real Ubuntu/systemd/Docker/SSH/cloud/WireGuard/CoreDNS/PostgreSQL/Patroni/watchdog tests,
three-host failures, actual signed package upgrades, soak/load and independent security
assessment have not passed here. Opt-in etcd/PITR attempts fail explicitly if dependencies
are absent. All production qualification gates remain BLOCKED.

Local compiler: Go1.23.2 on Debian13. Prepared CI: Go1.27.1, not executed here. A separately
supplied `.deb` is unsigned, unqualified and for fresh disposable lab VMs only. Actual
counts and evidence scopes: `validation/TEST-REPORT.md`.
