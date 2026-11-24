# Latest code handoff (2026-11-24, PR #287)

PR [#287](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/287) merged as [d286279a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d286279a8e9a1728910204293380c6dcf3953f10). Native `werft release verify` now validates all required manifest, signature, public-key and package paths plus positional arguments before reading any file, returning stable `RELEASE_ARGUMENTS_INVALID` for incomplete input. The regression test `TestReleaseCommandRejectsIncompleteInputBeforeReadingFiles` covers the fail-closed path.

PR checks: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308382126) **success** with real-etcd **success** and real-vm/PITR **skipped**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308382080) **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308382109) **success**. Post-merge Main checks also passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308989520), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308989479) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308989539).

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [d286279a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d286279a8e9a1728910204293380c6dcf3953f10) and use the existing ephemeral Ubuntu path with `run_real_vm_e2e=true` when workflow-dispatch access is available; do not start a seven-VM HA or Kubernetes lab for this first release.

# Latest code handoff (2026-11-24, PR #285)

PR [#285](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/285) merged as [e564148b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e564148b89a883190aa116ea5848540ebd48c922). Native certificate dispatch now rejects unknown operations before reading the configured CA certificate. The regression test `TestCertificateUnknownOperationFailsBeforeCARead` proves malformed input returns `UNKNOWN_CERTIFICATE_OPERATION` even when the CA path is unavailable.

PR checks: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45292645090) **success** with real-etcd **success** and real-vm/PITR **skipped**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45292645074) **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45292645094) **success**. Post-merge Main checks also passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45293062402), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45293062401) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45293062474).

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [e564148b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e564148b89a883190aa116ea5848540ebd48c922) and use the existing ephemeral Ubuntu path with `run_real_vm_e2e=true` when workflow-dispatch access is available; do not start a seven-VM HA or Kubernetes lab for this first release.

# Latest code handoff (2026-11-23, PR #282)

PR [#282](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/282) merged as [8800325a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8800325ab64dd701a69d65a39f332e6153c9da0d). Native `volume`, `secret` and `gateway` dispatch now rejects unknown actions before loading admin configuration or attempting controller access. A regression table uses an unavailable configuration path and verifies stable fail-closed errors for all three command families.

PR checks: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45284152469) **success** with real-etcd **success** and real-vm/PITR **skipped**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45284152601) **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45284152514) **success**. The documented second self-review was recorded on the PR; GitHub correctly disallows self-approval.

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [8800325a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8800325ab64dd701a69d65a39f332e6153c9da0d) and use the existing ephemeral Ubuntu path with `run_real_vm_e2e=true` when workflow-dispatch access is available; do not start a seven-VM HA or Kubernetes lab for this first release.

# Latest code handoff (2026-11-23, PR #279)

PR [#279](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/279) merged as [bfc74495](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bfc74495a3248d98df9cfc770eac3a519811e2d0). Native node drain|uncordon|revoke NAME now validates the policy action before loading admin configuration or reading controller state. Malformed two-argument actions therefore fail closed without an unnecessary control-plane request. TestNodePolicyBody covers all supported bodies and the NODE_ACTION_UNKNOWN contract.

PR checks:
- Native runtime/package [45274712039](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45274712039) — **success**; compile, race/static checks, package smoke checks and reachable Go vulnerability check passed; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45274712036](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45274712036) — **success**.
- Source/Privacy audit [45274711955](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45274711955) — **success**.

No Single-Host qualification gate closed. The unchanged [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to 28efa7518e171a618d4dcf9ff3aba58cddaf3296, reports immutable=false and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [bfc74495](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bfc74495a3248d98df9cfc770eac3a519811e2d0) and use the existing ephemeral Ubuntu path with run_real_vm_e2e=true when workflow-dispatch access is available; do not start a seven-VM lab for this first release.
# Latest code handoff (2026-11-23, PR #277)

PR [#277](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/277) merged as [2c4cbd4e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2c4cbd4ec54e63b52e45dde557809dfa13d2b88e). Native gateway enrollment now reads controller state before creating the credential directory or writing mTLS files. A transient controller/API failure therefore leaves no incomplete directory that blocks a safe retry with the same gateway identity. The generated ingress example was extracted into a deterministic helper and regression-tested for stable CIDR de-duplication, scoped routes and gateway/client identity.

PR checks:
- Native runtime/package [45264880235](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45264880235) — **success**; compile, race/static checks, package smoke checks and reachable Go vulnerability check passed; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45264880291](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45264880291) — **success**.
- Source/Privacy audit [45264880241](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45264880241) — **success**.

The first PR attempt exposed a source-transfer error in the remote Go blob; the Native compile check failed, the exact blob was republished, and the corrected head passed all available PR workflows before merge. This is recorded as a corrected publication defect, not as a production qualification result. The connector exposed no post-merge Main workflow runs for [2c4cbd4e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2c4cbd4ec54e63b52e45dde557809dfa13d2b88e) at handoff time.

No Single-Host qualification gate closed. The unchanged [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [2c4cbd4e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2c4cbd4ec54e63b52e45dde557809dfa13d2b88e) and use the existing ephemeral Ubuntu path with `run_real_vm_e2e=true` when workflow-dispatch access is available; do not start a seven-VM lab for this first release.

# Latest code handoff (2026-11-23, PR #274)

PR [#274](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/274) merged as [960ddafc](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/960ddafc6ab99b883ebdb2c180be41e71d3a071f). Native volume archive CLI dispatch now rejects unknown actions before root, state, Docker or filesystem access; a regression test covers the fail-closed boundary. The initial blob transfer was truncated and caught by CI; the complete file was republished before merge.

PR checks:
- Native runtime/package [45253629415](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45253629415) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45253629612](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45253629612) — **success**.
- Source/Privacy audit [45253629987](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45253629987) — **success**.

Post-merge Main checks:
- Native runtime/package [45254149973](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254149973) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45254150050](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254150050) — **success**.
- Source/Privacy audit [45254149998](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254149998) — **success**.
- Alpha publication guard [45254244539](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254244539) — **success**; source-only publication was **skipped** because no new release was created.

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

# Latest code handoff (2026-11-23, PR #272)

PR [#272](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/272) merged as [d92c922f](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d92c922fa8f1d46fc98e9dd5580124dacfdba001). Native `CreateBundle` now validates the join-bundle output destination before loading PKI material or registering the worker through `POST /v1/nodes`. Empty paths, existing destinations, final symlinks and symlinked parents are rejected; regression coverage verifies safe missing paths and each rejection case. This prevents a deterministic remote registration without a materialized local bundle.

PR checks:
- Native runtime/package [45244001391](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244001391) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45244001496](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244001496) — **success**.
- Source/Privacy audit [45244001445](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244001445) — **success**.

Post-merge Main checks:
- Native runtime/package [45244598160](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244598160) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45244598234](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244598234) — **success**.
- Source/Privacy audit [45244598089](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244598089) — **success**.

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

# Latest code handoff (2026-11-23, PR #270)

PR [#270](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/270) merged as [f7ab7e5a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f7ab7e5a0d3f10a6fa182222fb24c61c5dbb6b85). Native worker join-bundle input now uses no-follow safefile.OpenRead and bounded strict-JSON parsing from the opened descriptor. Final and parent symlink redirection, group-readable inputs and oversize bundles are rejected; regression coverage pins those cases and the exact 32 KiB boundary.

PR checks:
- Native runtime/package [45233988541](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45233988541) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45233988578](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45233988578) — **success**.
- Source/Privacy audit [45233988580](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45233988580) — **success**.

Post-merge Main checks:
- Native runtime/package [45234652978](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45234652978) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45234652991](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45234652991) — **success**.
- Source/Privacy audit [45234653067](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45234653067) — **success**.

This defensive change closes no Single-Host qualification gate. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to 28efa7518e171a618d4dcf9ff3aba58cddaf3296, reports immutable=false and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

# Latest code handoff (2026-11-23, PR #268)

PR [#268](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/268) merged as [f73662f4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f73662f4e957cf0489319d34445715d17c626cd4). Native `safefile.DirectoryLock` now validates absolute, clean and non-symlink parent directories before and after creation, opens lock files with no-follow/close-on-exec flags, and rejects non-regular files, non-0600 modes or unexpected owners. Regression coverage verifies a parent-symlink lock directory is rejected.

PR checks:
- Native runtime/package [45220888940](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45220888940) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45220888882](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45220888882) — **success**.
- Source/Privacy audit [45220889258](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45220889258) — **success**.

Post-merge Main checks:
- Native runtime/package [45221411990](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45221411990) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45221412038](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45221412038) — **success**.
- Source/Privacy audit [45221412406](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45221412406) — **success**.

No Single-Host qualification gate closed. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; immutable=false and unsigned assets mean it cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed artifacts/provenance and Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native Single-Host scope.
# Latest code handoff (2026-11-23, PR #266)

PR [#266](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/266) merged as [cdc929e8](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/cdc929e8651bef08ee4744edc234fa4c52f9ff35). Native `werft control` and agent local-lock paths now validate absolute, clean and non-symlink parent directories before and after creation, open lock files with no-follow/close-on-exec flags, and reject non-regular files, non-0600 modes or unexpected owners. Regression coverage verifies final and parent symlink rejection.

PR checks:
- Native runtime/package [45211017062](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45211017062) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45211016964](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45211016964) — **success**.
- Source/Privacy audit [45211016962](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45211016962) — **success**.

Post-merge Main checks:
- Native runtime/package [45212279490](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45212279490) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45212279129](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45212279129) — **success**.
- Source/Privacy audit [45212279244](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45212279244) — **success**.

No Single-Host qualification gate closed. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; immutable=false and unsigned assets mean it cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed artifacts/provenance and Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native Single-Host scope.
# Latest code handoff (2026-11-23, PR #264)

PR [#264](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/264) merged as [1b24e6cd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/1b24e6cd7b0f38c13797f2ab161a609e2641ca48). The `werft doctor` path now reads the configured admin certificate through `safefile.OpenRead` with a regular-file and 64 KiB size bound before parsing. Final and parent symlink redirection is rejected consistently with other credential paths. Regression coverage verifies a valid certificate and both symlink forms.

PR checks:
- Native runtime/package [45198552808](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45198552808) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45198553068](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45198553068) — **success**.
- Source/Privacy audit [45198552768](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45198552768) — **success**.

Post-merge Main checks:
- Native runtime/package [45199052283](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45199052283) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45199052324](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45199052324) — **success**.
- Source/Privacy audit [45199052375](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45199052375) — **success**.

No Single-Host qualification gate closed. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; immutable=false and unsigned assets mean it cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [1b24e6cd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/1b24e6cd7b0f38c13797f2ab161a609e2641ca48) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #262)

PR [#262](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/262) merged as [b99d5b8d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b99d5b8d25b839f94fc1ed1e3c82cc658c74f4fe). The packaged demo archive verification path now opens the archive through `safefile.OpenRead` before hashing, rejecting final and parent symlink redirection and non-regular inputs consistently with Docker image loading. Regression coverage verifies a valid archive and both symlink forms.

PR checks:
- Native runtime/package [45189154392](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189154392) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45189154412](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189154412) — **success**.
- Source/Privacy audit [45189154242](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189154242) — **success**.

Post-merge Main checks:
- Native runtime/package [45189685437](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189685437) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45189685472](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189685472) — **success**.
- Source/Privacy audit [45189685479](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189685479) — **success**.

No Single-Host qualification gate closed. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; immutable=false and unsigned assets mean it cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [b99d5b8d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b99d5b8d25b839f94fc1ed1e3c82cc658c74f4fe) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #260)

PR [#260](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/260) merged as [5cfd4726](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5cfd47267648840f57d947e2bc9f14443e2bf2b2). The read-only `werft assess DATEI.json` path now opens Kubernetes inventory files through `safefile.OpenRead`, rejecting final and parent symlink redirection before bounded assessment. Regression coverage verifies a valid inventory and both symlink forms. Input size limits, strict JSON, read-only behavior and the migration assessment contract are unchanged.

PR checks:
- [Native runtime/package 45179199727](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45179199727) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45179199695](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45179199695) — **success**.
- [Source/Privacy audit 45179199809](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45179199809) — **success**.

Post-merge Main checks:
- [Native runtime/package 45180128482](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45180128482) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45180128580](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45180128580) — **success**.
- [Source/Privacy audit 45180128505](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45180128505) — **success**.

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [5cfd4726](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5cfd47267648840f57d947e2bc9f14443e2bf2b2) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #257)

PR [#257](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/257) merged as [bafbf1e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bafbf1e98d93490282117b36a26a89eb3f51581b). Native secret-directory reuse now opens `.manifest` through `safefile.OpenRead`, rejecting final and parent symlink redirection. Reuse additionally requires a regular 0400 manifest with the exact expected hash length and a bounded read. Regression coverage rejects a symlinked manifest. Allocation APIs, state schema, stdin input, Kubernetes manager behavior and production flags are unchanged.

PR checks:
- [Native runtime/package 45169953738](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45169953738) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45169953783](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45169953783) — **success**.
- [Source/Privacy audit 45169953690](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45169953690) — **success**.

Post-merge Main checks:
- [Native runtime/package 45170406716](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45170406716) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45170406949](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45170406949) — **success**.
- [Source/Privacy audit 45170407002](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45170407002) — **success**.

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [bafbf1e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bafbf1e98d93490282117b36a26a89eb3f51581b) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #255)

PR [#255](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/255) merged as [e1586312](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e15863120152e08e280c65e8d00b00d27c06ea61). The Native `apply DATEI.json` path now opens manifest inputs through `safefile.OpenRead`, rejecting final and parent symlink traversal before a mutating manifest is parsed. Regression coverage verifies a valid file and both symlink forms. Stdin input (`-`), strict JSON, size limits, API contracts and state schema are unchanged.

Post-merge Main checks:
- [Native runtime/package 45160914694](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45160914694) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45160914910](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45160914910) — **success**.
- [Source/Privacy audit 45160914778](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45160914778) — **success**.

No Single-Host qualification gate closed. The existing `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [e1586312](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e15863120152e08e280c65e8d00b00d27c06ea61) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #253)

PR [#253](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/253) merged as [39965f40](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/39965f40c5103e64cfe563da4d4631df9032fb6a). Native volume restore archive inputs now use `safefile.OpenRead`, rejecting final and parent symlink traversal before archive bytes are consumed. A focused regression covers a valid archive and a parent-symlink path. Archive format, restore state and authorization policy are unchanged.

Post-merge Main checks:
- [Native runtime/package 45151283506](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45151283506) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45151283604](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45151283604) — **success**.
- [Source/Privacy audit 45151283665](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45151283665) — **success**.

No Single-Host qualification gate closed. The existing `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [39965f40](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/39965f40c5103e64cfe563da4d4631df9032fb6a) and use the existing ephemeral Ubuntu path when dispatch access is available.

## Latest code handoff (2026-11-23, PR #244)

PR [#244](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/244) merged as [6faf2fbe](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6faf2fbe819ae7a0775d27727986bc02be07228e). Native ingress gateway credentials now use the existing no-follow certificate/private-key readers, and edge TLS PEM loading uses bounded no-follow reads instead of path-based `tls.LoadX509KeyPair`. Regression coverage rejects final and parent symlinks for edge certificates and private keys. No certificate format, routing policy or qualification claim changed.

PR checks:
- [Native PR run 45120310439](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120310439) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes PR run 45120310428](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120310428) — **success**.
- [Source/Privacy PR run 45120310459](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120310459) — **success**.

Post-merge Main checks:
- [Native Main run 45120597182](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120597182) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes Main run 45120597181](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120597181) — **success**.
- [Source/Privacy Main run 45120597194](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120597194) — **success**.

Production remains **not ready**: the immutable/signed release candidate, fresh Ubuntu installation, backup/restore, upgrade/rollback, bounded load/soak and final Go/No-Go evidence are still open. The tagged dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and cannot evidence this newer Main commit. Next handoff: build a new candidate from [6faf2fbe](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6faf2fbe819ae7a0775d27727986bc02be07228e), then run the existing ephemeral Ubuntu path when dispatch access is available.

## Latest code handoff (2026-11-23, PR #242)

PR [#242](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/242) merged as [485fcfd2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/485fcfd2b9f53abc857dfe19d66e8741981aa864). Native `certificate bundle/renew/install` now reads CA and leaf certificate inputs through `safefile.OpenRead`, rejecting final and parent symlinks and enforcing a 1 MiB input bound. Regression coverage rejects both symlink forms. The change does not alter certificate formats or qualification claims.

PR checks:
- [Native PR run 45115171200](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115171200) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes PR run 45115171140](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115171140) — **success**.
- [Source/Privacy PR run 45115171174](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115171174) — **success**.

Post-merge Main checks:
- [Native Main run 45115468629](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115468629) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes Main run 45115468670](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115468670) — **success**.
- [Source/Privacy Main run 45115468624](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115468624) — **success**.

Production remains **not ready**: the immutable/signed release candidate, fresh Ubuntu installation, backup/restore, upgrade/rollback, bounded load/soak and final Go/No-Go evidence are still open. The tagged dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and must not be treated as evidence for this newer Main commit. Next handoff: build a new candidate from [485fcfd2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/485fcfd2b9f53abc857dfe19d66e8741981aa864), then run the existing ephemeral Ubuntu path when dispatch access is available.

## Latest code handoff (2026-11-23, PR #239)

PR [#239](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/239) merged as [43bcfb46](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/43bcfb468680d976b181a5ca8a745d55bd1d63ff). Native `backup inspect/restore --file` now opens privileged backup inputs through `safefile.OpenRead`, rejecting final and parent symlinks and enforcing the existing 3x `MaxPlaintext` limit after opening. Regression tests cover both symlink forms and regular-file reads. The first CI attempt exposed a self-introduced truncated-file error; it was corrected before the merged head.

PR and post-merge required checks:
- [Native PR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108527662) and [Native Main](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108824975) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes Main](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108825010) — **success**.
- [Source/Privacy Main](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108824979) — **success**.

No qualification gate was closed. The tagged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and remains `productionReady=false`/No-Go. The next candidate must be built from `43bcfb468680d976b181a5ca8a745d55bd1d63ff`. Live Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle and restart, backup/restore, upgrade/rollback, bounded load/soak, signed provenance/immutability, user feedback and final Go/No-Go remain open. The connector still cannot dispatch `ci.yml`; this is a blocker, not a passed gate.

# Aktuelle Production-Entscheidung — 23.11.2026

## Latest code handoff (2026-11-23, PR #237)

PR [#237](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/237) merged as [6463c29d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6463c29de2a1bfcb6c9e7dbcfbfeae26585d427d). Native `werft release verify` liest Manifest-, Signatur- und Public-Key-Eingaben jetzt über `safefile.OpenRead`, weist finale und übergeordnete Symlinks ab und erzwingt das Größenlimit auch nach dem Öffnen. Regressionstests decken beide Symlinkformen und das Limit ab.

Exact Main checks for the merge commit:
- [Native runtime/package 45103114622](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103114622) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts/package 45103114692](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103114692) — **success**.
- [Source/Privacy audit 45103114649](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103114649) — **success**.

Private alpha publication jobs [45103144455](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103144455), [45103152906](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103152906) and [45103316680](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103316680) completed successfully but are not stable release or production evidence. No qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains **no-go**.

The next candidate must be package-built from `6463c29de2a1bfcb6c9e7dbcfbfeae26585d427d`. Live Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle and restart, backup/restore, upgrade/rollback, bounded load/soak, signed provenance/immutability, user feedback and final Go/No-Go remain open. The current GitHub connector still cannot dispatch `ci.yml`; this is a blocker, not a passed gate.

## Previous handoff history
## Previous handoff history

## Latest code handoff (2026-11-23, PR #232)

PR [#232](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/232) merged as [29418520](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/29418520bc4198a2e8102fe7518ef8e1e23893fe). Native `Docker.Load` now opens local image archives through `safefile.OpenRead`, refusing final symlinks and symlinked parent paths before Docker ingestion; regression tests cover both paths.

Exact PR checks passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091069067), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091068980) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091069003). Post-merge Main checks passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091414068), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091414150) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091414089). Real-etcd passed; real-vm and real-PITR were skipped.

This is security-boundary hardening only. The tagged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, its release metadata reports `immutable=false` and unsigned assets, `productionReady=false`, and no qualification gate was closed. The next candidate must be built from `29418520bc4198a2e8102fe7518ef8e1e23893fe`; live installation, backup/restore, upgrade/rollback, bounded load/soak, signing/provenance and final Go/No-Go remain open.


Der offizielle erste Production-Scope ist jetzt **Native Single-Host Production**. Die Hauptversion soll produktiv nutzbar sein, aber nur innerhalb dieses ausdrücklich dokumentierten Umfangs. HA/Multi-Host, Kubernetes-Production und Site-Recovery sind zurückgestellt und keine Blocker für den ersten Native-Release.

Der aktuelle Status bleibt **No-Go**, bis der exakte Native-Kandidat die Single-Host-Gates, Signierung, Runbooks und Go/No-Go-Prüfung bestanden hat. Die alten Full-Masterplan-Einträge darunter sind historische Nachweise; sie gelten nicht mehr als Pflichtumfang für den ersten Release.

The scope decision is recorded in [PR #203](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/203), merged at
`f75845424286c1c8bed6c9ef17d2b172066e6309`. The current tagged candidate remains
older and must not be treated as evidence for this changed scope; GitHub release metadata reports immutable=false and its assets are unsigned.

The tracker contract is hardened by [PR #204](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/204), merged at
`83c06425600749418994d34a1f197d4ad64f6d50`; the follow-up documentation synchronization is
tracked in PR #205. The candidate remains an older, unsigned lab artifact and does not
qualify any Native Single-Host gate.

The next live candidate must be built from package-bearing Main code handoff `29418520bc4198a2e8102fe7518ef8e1e23893fe`; documentation-only Main commits may have newer SHAs, so evidence must bind the runner-reported `GITHUB_SHA` and package digest rather than a guessed predecessor. The current connector cannot dispatch `ci.yml`, so this remains a documented blocker rather than a passed gate.


## Previous code handoff (2026-11-23, PR #230)

PR [#230](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/230) merged as [397e0ff](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/397e0ff6de39404f631aab92c12ed9719108c617). Native release verification now opens the candidate package through `safefile.OpenRead`, which validates non-symlink parent components, refuses final symlinks and rejects non-regular files before hashing. Regression coverage protects both final-package and parent-symlink paths.

Exact PR checks passed: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45085446362), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45085446302) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45085446373). Real-etcd passed; real-VM and real-PITR were skipped. The first PR attempt failed only because of a self-introduced Go formatting mistake, which was corrected before these final checks. This is release-artifact path hardening only: `v0.2.0-dev.4-test.17` remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, release metadata reports `immutable=false` and unsigned assets, `productionReady=false`, and no qualification gate was closed. Build the next candidate from `397e0ff6de39404f631aab92c12ed9719108c617` before live evidence can cover this fix.

# Release status — 0.2.0-dev.4

**NOT_PRODUCTION_READY. Full masterplan incomplete. State schema 2.**

The [candidate production scope](PRODUCTION-SCOPE.md) records a proposed,
bounded first support matrix for the Native and Kubernetes paths. It is a
planning and drift-detection contract, not qualification evidence. All listed
live, security, supply-chain and operational gates remain open until evidence
for one unchanged release candidate is verified.

The active [German E2E production plan](PRODUCTION-E2E-PLAN-DE.md) and the
machine-readable [`production-tracker.json`](../release/production-tracker.json)
make the next blocked and independent steps explicit between runs. They are
tracking aids only; their status never closes a qualification gate.

The Kubernetes matrix now selects hcloud-csi 2.24.2 as a candidate RWO storage
path with a digest-bound chart and `Retain` StorageClass. Its six upstream OCI
index digests are pinned after each registry digest header matched the SHA-256 of
the received manifest body, and the checker can repeat that online comparison.
The hash-checked chart was rendered with the conservative values and exact image
multiset; the generated manifest is committed and hash-bound. The chart, Helm and
images have not been signature- or vulnerability-verified, executed or independently
reviewed; real Volume lifecycle, failure, backup and restore evidence remains absent.
The exact render now also has a fail-closed static privilege audit: RBAC contains no
wildcards or Secret access, and the only accepted privileged container/host-path set
is the CSI node driver boundary. The exact render now selects a separately hash-bound
node ServiceAccount with automatic API-token mounts disabled. Both workloads set
`RuntimeDefault` at pod level, covering their non-privileged containers; Kubernetes
privileged-container semantics leave the CSI node driver as an explicit exception.
The linux/amd64 manifest and config blobs behind all six locked image indexes were
also hash-checked. Their image configs select root explicitly (`User: 0`) or implicitly
(empty `User`), while the upstream chart exposes no per-container security-context
values. Pod-level `runAsNonRoot` is therefore explicitly unsafe for this candidate,
not a completed control. An exact-input, fail-closed post-render step now makes every
root identity explicit. The seven non-privileged container instances disable privilege
escalation, drop every Linux capability and bind `RuntimeDefault` at container level;
the privileged node driver retains only its reviewed explicit root/privileged context.
Hardening remains blocked pending qualified non-root identities and disposable-cluster
runtime evidence. Every rendered CSI container has a hash-bound CPU/memory request and
limit; these conservative starting budgets have not been measured under load or soak
and are not production capacity claims.
These audits are not runtime security or live CSI compatibility evidence.

The authoring-environment observations below are historical, including the
compiler version and whether CI had run at that time. For subsequently verified
GitHub CI and public-source preparation, see
[the dated publication review](validation/PUBLICATION-REVIEW-2026-10-12.md).
That review does not qualify the production features listed here.
The later [production qualification review](validation/PRODUCTION-READINESS-2026-10-12.md)
records a successful exact-commit single-host Ubuntu test. Multi-host, Kubernetes,
database recovery and signed production acceptance remain unqualified.

## Current tagged lab candidate

The latest tagged experimental candidate is [`v0.2.0-dev.4-test.17`](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17), built from source commit `28efa7518e171a618d4dcf9ff3aba58cddaf3296`. GitHub release metadata reports immutable=false and its assets are unsigned. Its Native, Kubernetes-package and source-audit workflows passed; the Native real-etcd job passed, while VM/PITR jobs were skipped. The release includes the auto-discovery known-hosts replay guard, is unsigned and remains a lab artifact only: it does not qualify installation, HA, recovery, Kubernetes lifecycle, supply-chain or production readiness. The machine-readable tracker records the exact asset digests and open gates.

Main contains [PR #122](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/122), merged at `c95511a5f1e1c8ca6aa909b3e69bb21558b00634`, [PR #140](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/140), [PR #143](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/143), [PR #148](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/148), [PR #152](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/152), [PR #154](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/154), [PR #156](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/156) and [PR #158](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/158). The code-bearing handoff commit remains `2ab2ebe5433b938925b4aebd57c84a7939d92a43`; the latest tracker-synchronized Main handoff is `9403d55e2deae30f4c99e889a56cfffbafb0390b`, with this status/roadmap/tracker synchronization following PR #158. Native auto-discovery binds both the explicit `--hosts-file` path and its exact bytes in the private resume journal; changed content is rejected with `AUTO_DISCOVERY_HOSTS_FILE_CONTENT_CHANGED`, and legacy journals without the byte binding fail closed. PR #140 adds fail-closed TCP port-range validation for Native control-plane endpoints. PR #143 makes the Native package `postinst` execute `/usr/bin/werft --help` and `/usr/bin/werft-ops --help` before declaring the package configured, with a release regression test protecting both checks. PR #148 adds a release-contract regression test that covers every service stop/disable action and prevents uninstall scripts from deleting persisted state, identities or workloads. PR #152 adds a release-contract regression test for both Kubernetes recovery/repair systemd templates, preserving their explicit root, token/assets and sandbox boundaries. PR #154 adds hermetic Kubernetes-manager wrapper tests for staged package-root execution and exit-78 fail-closed behavior when Python modules are missing. PR #156 requires the Kubernetes wrapper entrypoint to exist before selecting an installed, staged or source-tree module path and regression-tests incomplete package trees. PR #158 requires the Native `werft-ops` wrapper to find both `werftops/__init__.py` and `werftops/__main__.py` before selecting a module path and regression-tests incomplete package trees. Post-merge Native, Kubernetes-package, source-audit and Private-Alpha workflows passed; real-vm/real-pitr remain skipped. Test17 remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; GitHub release metadata reports immutable=false and its assets are unsigned and does not contain PR #140, PR #143, PR #148, PR #152, PR #154, PR #156 or PR #158; a new candidate is required before live testing the updated package. The production decision remains no-go.

## Latest code handoff (2026-11-21)

PR #160 is merged at [a04b0b4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a04b0b4c9db7f4f0aa5e408446b45cb5fe25dd1a). The Kubernetes-manager `werft-kube plan` command now rejects valid non-object JSON before format dispatch and returns the stable `KUBE_PLAN_OBJECT_REQUIRED` block instead of an uncaught traceback; the regression test covers the JSON response and stderr. This is a CLI error-handling guard only. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and does not contain PR #160. Post-merge source, contract, Real-etcd and publication-audit checks passed; `real-vm` and `real-pitr` remain skipped. Production remains no-go.


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

The new `werft-ops native-bootstrap` coordinator now covers the intended
three-controller/worker bootstrap flow in code: it resolves an explicit
inventory against a trusted hosts file, performs fail-closed SSH/Ubuntu/systemd/
cgroup-v2 preflight on every target, generates one bound HA kit set, installs
the unchanged package through the existing SSH bootstrap primitive, and resumes
from a private journal without overwriting foreign or incomplete state. The
coordinator has fixture tests only; no real six-host run was executed in this
authoring environment, so this does not close any live qualification gate.

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



## Latest code handoff (2026-11-21, PR #162)

PR #162 merged at [2ad8daeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2ad8daebed99f8ea2b6735f9f626e500666cd694). The Kubernetes wrapper now requires both `werftops/__init__.py` and `werftops/kube_main.py` before selecting installed, staged or source modules; a missing package marker fails closed with exit 78 and is covered by a regression test. This is a packaging/error-boundary fix for the Kubernetes manager only. Post-merge test, contracts, real-etcd, publication-audit and private-alpha checks passed; real-vm and real-pitr remain skipped because no authorized disposable lab is configured. The immutable test17 candidate is unchanged, and `productionReady=false` remains the honest status.
## Latest code handoff (2026-11-21, PR #164)

PR [#164](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/164) merged at [552a9aeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/552a9aeb46097d703300475ff21c87ecbffa282c). The Kubernetes conformance evidence parser now validates archived `serverversion.json` and `gitVersion` before comparison, returning stable blocked reasons for malformed evidence. Post-merge automated checks passed; real-VM/PITR remain skipped because no authorized disposable lab is configured. Test17 is unchanged and `productionReady=false` remains the honest status.

## Latest code handoff (2026-11-21, PR #166)

[PR #166](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/166) merged as [e88b667](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e88b6679829be356710cc88a35e090093054ec8b). Kubernetes supply-chain evidence verification now validates top-level and nested SBOM, vulnerability-scan and provenance document shapes before access, returning stable blocked reasons for malformed evidence. Regression coverage and post-merge automated checks are green.

This is a code-quality handoff only. No live qualification gate was closed: authorized disposable Ubuntu/k0s execution, installation/upgrade/rollback, backup/restore, HA/partition, load/soak and independent-review evidence remain open. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` remains the honest status.

## Latest code handoff (2026-11-21, PR #168)

[PR #168](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/168) merged as [7b1408a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7b1408a38f830405af52da47143cffa6058068c9). The Kubernetes evidence verifier now validates the trust-policy `keys` inventory before iteration and returns stable `TRUST_KEYS_REQUIRED` for null, empty or non-list inventories. Regression coverage and post-merge automated checks are green.

This is a code-quality handoff only. No live qualification gate was closed: authorized disposable Ubuntu/k0s execution, installation/upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent-review evidence remain open. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` remains the honest status.

## Latest code handoff (2026-11-21, PR #170)

[PR #170](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/170) merged as [289c0f2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/289c0f2c37e4ce011e2c1c4827a2646915c3b340). The Kubernetes evidence verifier now requires every signed environment identity to be a non-empty string and returns stable `EVIDENCE_IDENTITIES_INVALID` for malformed entries. Regression coverage and post-merge automated checks are green.

This is a code-quality handoff only. No live qualification gate was closed: authorized disposable Ubuntu/k0s execution, installation/upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent-review evidence remain open. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` remains the honest status.


## Latest code handoff — PR #172 (2026-11-21)

[PR #172](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/172) merged at [77bdc1d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/77bdc1d1af128f5c98fefec3f6720d74df01b3d7). The Kubernetes evidence verifier now rejects trust-policy key roles and organization metadata unless they are non-empty strings, preserving stable `TRUST_KEY_INVALID` handling. Regression tests cover both malformed trust-key paths. Exact post-merge Kubernetes, Native, Source/Privacy and private-alpha audits passed:
[Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520639),
[Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520655),
[Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520708),
[Private Alpha](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959717872).

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #174 (2026-11-22)

[PR #174](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/174) merged at [0245997](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0245997861b9eb663f261cf0d7bcc5623c4627e1). The Kubernetes supply-chain evidence verifier now rejects CycloneDX SBOM component entries unless each is a JSON object, preserving stable `SBOM_COMPONENT_INVALID` handling. A regression test covers `components: [null]`. Exact post-merge audits passed:
[Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222806),
[Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222823),
[Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222792),
[Private Alpha](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964385448).

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #176 (2026-11-22)

[PR #176](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/176) merged at [33d8780](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/33d87805b952fcfff1b98ff43e18a60cb041db32). The Kubernetes Trivy-v2 evidence verifier now rejects empty or whitespace-only result targets, preserving stable `VULNERABILITY_RESULT_INVALID` handling. Nullable `Vulnerabilities` fields remain supported; a regression test covers the malformed target. Exact post-merge audits passed:
[Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159822),
[Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159864),
[Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159804),
[Private Alpha](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969356902).

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #179 (2026-11-22)

[PR #179](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/179) merged at [6b44496](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6b44496ed69a0feb25e11e2ba0ea358802dc8945). The Kubernetes Trivy-v2 evidence verifier now rejects boolean, numeric and other scalar `Vulnerabilities` inventories while preserving missing/`null` inventories as empty, with stable `VULNERABILITY_RESULT_INVALID` handling and a regression test. Exact PR checks passed: [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221312), [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221342), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221313); real-VM and real-PITR remained skipped.

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.



## Latest code handoff — PR #181 (2026-11-22)

PR [#181](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/181) merged at [f38d33c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f38d33c77394d321ec8229033dda5e48299d16cf). The Kubernetes CycloneDX evidence parser now requires every component object to carry a non-empty string `name`; malformed entries are rejected fail-closed with `SBOM_COMPONENT_INVALID`, and a regression test covers an empty component object.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393959), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393878) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393890). Real-VM and real-PITR remain skipped. This is not SBOM validity, vulnerability clearance or production qualification.

The immutable `v0.2.0-dev.4-test.17` candidate is unchanged at `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #183 (2026-11-22)

PR [#183](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/183) merged at [8c0bc4a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8c0bc4aa21575891eb782ad6943bfe42c24cb4d6). The Kubernetes Trivy-v2 evidence parser now requires each LOW/MEDIUM finding to carry a non-empty string `VulnerabilityID`; malformed findings are rejected fail-closed with `VULNERABILITY_FINDING_INVALID`, and a regression test covers a nameless LOW finding.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729213), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729235) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729267). Real-VM and real-PITR remain skipped. This is not vulnerability clearance or production qualification.

The immutable `v0.2.0-dev.4-test.17` candidate is unchanged at `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #185 (2026-11-22)

PR [#185](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/185) merged at [3cfe2e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/3cfe2e9f25b68cce70a8e9684d8dd4dd957c8fa8). The Kubernetes release-candidate evidence parser now requires `sourceRepository` to be a canonical public GitHub repository URL, with an optional `.git` suffix; malformed identities are rejected fail-closed with `SOURCE_REPOSITORY_INVALID`, and a regression test covers a truncated URL.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036663), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036674) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036662). Real-VM and real-PITR remain skipped. This is not provenance validity or production qualification.

The immutable `v0.2.0-dev.4-test.17` candidate is unchanged at `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #187 (2026-11-22)

PR [#187](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/187) merged at [1954916](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/19549167b5a18c1e741d1603aaa990a67e5bbb11). The Kubernetes SLSA-provenance parser now rejects each `resolvedDependencies` entry unless it has a non-empty URI, a non-empty digest object and non-empty string digest values, returning stable `PROVENANCE_DEPENDENCIES_INVALID` handling. Regression coverage protects the malformed-material case.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447185), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447134) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447123). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is evidence-shape hardening only; it does not close a live qualification gate. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #189 (2026-11-22)

PR [#189](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/189) merged at [93b0cb3](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/93b0cb3672cd6889114e2e6f7b5e358057979fdf). The Kubernetes evidence verifier now rejects whitespace-only `builderId` values with stable `BUILD_IDENTITY_REQUIRED` handling, with regression coverage for the malformed identity.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512976), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512956) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512896). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is evidence-shape hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #191 (2026-11-22)

PR [#191](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/191) merged at [94b5110](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/94b51103edeaf16e1e381e5acac4232bf2ac58cc). The Kubernetes evidence verifier now rejects empty or whitespace-only digest keys in `resolvedDependencies` entries with stable `PROVENANCE_DEPENDENCIES_INVALID` handling, with regression coverage for malformed digest-key data.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517185), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517149) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517249). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is evidence-shape hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #193 (2026-11-22)

PR [#193](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/193) merged at [e660826](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e66082608f67f4f51d996f86afc1ce94652b455d). The Kubernetes evidence verifier now rejects candidate `builderId` values with leading or trailing whitespace using stable `BUILD_IDENTITY_REQUIRED` handling, with regression coverage for a non-canonical identity.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520825), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520832) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520854). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is evidence-identity hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #195 (2026-11-22)

PR [#195](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/195) merged at [c587354](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/c58735426626ee71dc9755fc3a38a6c7edb6c740). The Kubernetes evidence verifier now requires trust-policy `organization` identifiers to be non-empty and canonically free of leading or trailing whitespace; malformed identities fail closed with stable `TRUST_KEY_INVALID` handling, with regression coverage.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532273), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532243) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532236). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is trust-identity hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #197 (2026-11-22)

PR [#197](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/197) merged at [71f1dfd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/71f1dfddc2be51ad6a1c54371cac4339c9910167). The production-tracker validator now requires non-empty string lists for `nextAction.blockers`, `nextAction.successCriteria` and every workstream's `requiredGateFamilies`; the previous empty-list `all([])` acceptance is closed with regression tests.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865245), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865193) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865239). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is release-tracker validation hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #199 (2026-11-22)

PR [#199](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/199) merged at [f532b26](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f532b264a9f8bcc20ce26bfe2da6e4ab4debcc9d). The production-tracker validator now rejects empty or whitespace-only decision evidence lists, rollback contracts, next-action evidence strings and gate-family strings. Blocked workstreams reject scalar, object or blank-entry blocker fields with stable `TRACKER_BLOCKERS_INVALID` handling; regression tests cover malformed shapes.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092826), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092830) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092833). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is release-tracker validation hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #201 (2026-11-22)

PR [#201](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/201) merged at [a768d0e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a768d0e304bc7c28ca8f3da7732a179e504001e6). The production-tracker validator now requires non-empty `nextAction.summary` and `nextAction.nextStep` strings, with regression coverage for missing actionable text. This closes a fail-open shape where a blocked release handoff could omit the operator-facing next step.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736383), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736359) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736350). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is release-tracker validation hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #209 (2026-11-22)

PR [#209](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/209) merged at [fe052af](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/fe052af52ab80509f325b9ebee8338649f49ecdd). The Native API now evaluates mTLS certificate validity through its injected UTC clock, with a regression test for certificates outside that validity window. This is a code-quality/security-boundary handoff only; no qualification gate was closed.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904516), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904485) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904486). Real-VM and real-PITR remain skipped because the authorized disposable runner dispatch is not available through the current connector. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`.


## Latest code handoff — PR #211 (2026-11-22)

PR [#211](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/211) merged as [0a785a8](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0a785a85435c6796a34cadd24d66e7c1256f553c). The ingress Gateway now evaluates edge TLS leaf validity through its injected clock, matching the existing snapshot-freshness boundary; `TestServeUsesInjectedClockForCertificateValidity` covers an out-of-window certificate.

Exact PR checks passed: [Native test and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437255), [contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437247) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437285). Real-VM and real-PITR were skipped; no live qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. The next candidate must be package-built from `0a785a85435c6796a34cadd24d66e7c1256f553c`.


## Latest code handoff — PR #213 (2026-11-22)

PR [#213](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/213) merged as [ea83bb6](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ea83bb618edd82586a269930f388a66e04ade566). The Native agent now restores the allocation ID when an engine returns a zero report on failure; this keeps failure reports valid for the heartbeat contract and preserves node liveness. Regression coverage verifies the failed report identity.

Exact PR checks passed: [Native test and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874344), [contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874104) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874099). Real-VM and real-PITR were skipped; no live qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. The next candidate must be package-built from `ea83bb618edd82586a269930f388a66e04ade566`.

## Latest code handoff — PR #246 (2026-11-23)

PR [#246](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/246) merged as [7154c11](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7154c11c58ec2b77c839b0ec1dd8745c630756e2). The privileged Native `node bundle` path now reads the authority certificate and issuing private key through bounded, no-follow file handling. Private keys require a regular file with mode 0600; final and parent symlinks, oversized inputs and permissive key modes are rejected. Regression coverage is in `internal/setup/setup_test.go`.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45126994589), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45126994424) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45126994355). Post-merge Main checks also passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45127397668), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45127397549) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45127397616). Real-VM and real-PITR remained skipped; no live qualification gate was closed.

The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `productionReady=false`; its release metadata is not immutable and its assets are unsigned. A new candidate must be built from [7154c11c58ec2b77c839b0ec1dd8745c630756e2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7154c11c58ec2b77c839b0ec1dd8745c630756e2) before these Native changes can be covered by live installation, backup/restore, upgrade/rollback or load/soak evidence. The decision remains `no-go`.


## Latest code handoff — PR #248 (2026-11-23)

PR [#248](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/248) merged as [5c564ac](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5c564acb4972041bc3a9e3733404cc356594b4e7). Native vault key creation and logical/schema/volume backup outputs now use `safefile.CreateExclusive`: parent-chain validation, exclusive no-follow creation, regular-file verification and exact permissions prevent final or parent symlink redirection. Regression tests cover valid creation, existing destinations, final symlinks and parent symlinks.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45134771753), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45134771842) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45134771745). Post-merge Main checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45135169259), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45135169243) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45135169232). Real-VM and real-PITR remain skipped; no live qualification gate was closed.

The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `productionReady=false`; its release metadata is not immutable and its assets are unsigned. A new candidate must be built from [5c564acb4972041bc3a9e3733404cc356594b4e7](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5c564acb4972041bc3a9e3733404cc356594b4e7) before this hardening can be covered by live installation, backup/restore, upgrade/rollback or load/soak evidence. The decision remains `no-go`.


## Latest code handoff — PR #251 (2026-11-23)

PR [#251](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/251) merged as [e0bc69a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e0bc69abf0793b7fbae20301f09be97fc706ace6). Existing Native vault key reads now use `safefile.OpenRead`, so final and parent symlink traversal fails closed while the 32-byte/private-mode contract remains enforced. A regression test creates a valid key behind a symlinked parent and verifies rejection.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142398350), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142398485) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142398600). Post-merge Main checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142835351), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142834906) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142834912). Real-VM and real-PITR remain skipped; no live qualification gate was closed.

The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `productionReady=false`; its release metadata is not immutable and its assets are unsigned. A new candidate must be built from [e0bc69a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e0bc69abf0793b7fbae20301f09be97fc706ace6) before this Native hardening can be covered by live installation, backup/restore, upgrade/rollback or load/soak evidence. The decision remains `no-go`.
