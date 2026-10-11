# Local historical native agent compatibility verification

**Evidence date:** 2026-10-11. **Scope:** local executable/protocol test, not
GitHub CI, live Docker/etcd, Ubuntu, multi-host upgrade or production approval.

## Source provenance

The privately supplied earlier development artifacts were compared with their
original delivery manifests before use:

- dev.3 Git bundle SHA-256:
  `ae14dd172a8286876b0f6d8f1b2806d4d1da5012ca633b48cf1eecad5a9b7fd8`.
- dev.3 source commit:
  `67f5617188a8536d0ce915267a27ed552e55687e`.
- dev.4 Git bundle SHA-256:
  `3f739684b6064847f0184e7bcb865c8a8835ada519e68640e1d7a8ae9f0684db`.
- dev.4 source commit:
  `8803d9d641af0e01dbbb034fc5732cb31da30852`.

Both bundle hashes matched. The historical dev.3 commit exists within the
dev.4 bundle, even though it is not present in the independently initialized
GitHub repository. The source lint on the dev.4 working tree reported
216 files scanned, zero known-pattern findings; that is NOT a full
secret, copyright or security audit.

## Executed test

From the verified historical dev.4 source checkout with Go 1.23.2 on an
isolated Linux container, both dev.3/dev.4 executable binaries were built.
The actual prior-agent compatibility test was executed with
`WERFT_PREVIOUS_BINARY`, `WERFT_CURRENT_BINARY` and the
`compat_agent` build tag. Output:

```text
=== RUN   TestPreviousAgentBinaryUpgradeRetainsJournalAndAllocation
--- PASS: TestPreviousAgentBinaryUpgradeRetainsJournalAndAllocation (14.09s)
PASS
ok github.com/ClusterPilot-System/werftkern/tests/integration 14.103s
```

The test uses actual agent child processes, local mTLS and an actual
persistent journal. Its Docker and etcd services are **explicit test adapters**.
It does not execute a real container engine, distributed etcd or a host
installation, and cannot establish upgrade safety on real clusters.

An earlier `go test -race` attempt timed out in the local environment;
the successful test above was executed **without the race detector**.
Do not reclassify that interrupted attempt as a pass.

## How to reproduce with current development checkout

The script `scripts/test-agent-compat.sh` now accepts an optional
`WERFT_PREVIOUS_BUNDLE` path to the exact checksum-pinned historical
dev.3 bundle. The bundle is NEVER copied to the repository:

```bash
WERFT_PREVIOUS_BUNDLE=/private/path/Werftkern_0.2.0_dev3.bundle \
  bash scripts/test-agent-compat.sh
```

It rejects missing/wrong checksums with a BLOCKED exit and extracts
historical source into a disposable directory. Without an independently
verified bundle or a reachable historic commit the test is not performed.
The built binaries and test log remain under `evidence/agent-compat`,
which must not be published without a separate source/secret review.

**Still open:** there is not yet a successful GitHub CI run of this
bundle-backed test against the exact current main commit and no actual
Ubuntu/SSH/package-upgrade/rollback evidence. Issue #8 remains open.
