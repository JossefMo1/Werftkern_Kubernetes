# Dev.2 implementation record

Baseline: cbc01de44284274947f81c244b091af7c626363c (dev.1). The delivered Git commit records
all changes; it does not publish them remotely.

## Reproduced defects and fixes

1. Revoking a node excluded its unknown allocation from the scheduler's effective replica
   count. That could create another execution without proving the old process was stopped.
   A regression test failed with the baseline scheduler and passes with this change.
2. Heartbeats were not ordered durably at the protocol boundary. Sequence/content checks now
   prevent delayed reports from refreshing liveness or reviving stopped allocations.
3. Strict inventory validation now applies on authoritative reads and CAS writes, rather
   than merely validating the root state object. Invalid test inventories were corrected.

Default replacement retains unknown execution. `replacementPolicy: duplicate-safe` is an
explicit stateless-only choice allowing simultaneous old/new processes during a partition.
It does not implement exactly-once processing. Lost allocations keep reservations until
confirmation; long-lived partitions can deliberately consume capacity and require repair.

## Additional implemented paths

`internal/volumearchive`: authenticated chunk framing and bounded directory export/extract.
`internal/cli/volume_archive.go`: owned maintenance, Docker mount inspection, IO lock,
new-volume pending reservation, byte copy, durable receipt and idempotent completion.
`internal/ingress`: TLS edge with pinned route/host and endpoint freshness contracts.
`internal/control/gateway.go`: service-scoped mTLS discovery identities.
`internal/store/migration.go`: explicit backed-up schema 1→2 migration, one CAS, no retry
against changed source bytes. `tests/integration/quorum_etcd_test.go`: real process suite.

These modules are not claims that database HA, CSI, network policy or all 52 tasks are done.
Read STATUS and the actual test report for missing implementation and missing evidence.
