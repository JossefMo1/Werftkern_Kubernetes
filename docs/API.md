# Runtime API additions

TLS1.3 client authentication. `admin` controls desired state; `node:ID` is scoped to
one enrolled nonrevoked worker. `gateway:ID` is limited to allowlisted service discovery. Browser origins are refused by native API; dashboard
uses its local authenticated proxy. Versioned Workload API: `werftkern/v1alpha1`.

Existing routes: `/v1/health`, `/v1/state`, `/v1/workloads`, `/v1/workloads/{name}/{action}`,
`/v1/nodes`, `/v1/nodes/{id}`, `/v1/heartbeat`, `/v1/secrets/{name}`,
`/v1/allocations/{id}/secrets`, `/v1/metrics`. Mutation generations and idempotency remain
required where defined by the individual operation; no exactly-once external side-effect claim.

New routes:

| Route | Identity / contract |
|---|---|
| POST `/v1/volumes` | Admin; name,nodeId,uid,gid; same name/attributes replays, conflict otherwise |
| GET `/v1/allocations/{id}/volumes` | Assigned node only; own live allocation; no host path input |
| POST `/v1/volumes/{name}/initialized` | Assigned node; allocationId proof; monotonic initialized flag |
| POST `/v1/volumes/{name}/release` | Admin; exact volumeId; no remaining refs; data retained |
| GET `/v1/discovery` | Admin/enrolled nonrevoked node; current nonsecret A/SRV endpoint inventory |
| POST `/v1/maintenance` | Admin; id,enabled,reason; only the owning operation releases an active lock |

Workload spec adds `volumes[{name,mountPath,readOnly}]`, `runAsUid`, `runAsGid`, `probe`,
`profile`. Check Go JSON tags as the source of truth. A volume requires one pinned node,
max1 replica, no host path freedom and a valid nonroot identity. `postgres17` requires
exact data mount and `postgres-password` SecretRef. Old specs without these fields retain
stateless behavior. Unknown fields are rejected by JSON decoding.

Node admission adds `podCidr`. Reports add `containerIp`, permitted only inside that node's
registered subnet. Discovery does not expose secret or volume values. `maintenanceId` in
State explains why new work is blocked during a host update; reads/heartbeats/pause remain.

## Dev.2 / state schema2

POST `/v1/gateways` (admin): immutable registered ID/name/services; explicit replay.
POST `/v1/gateways/{id}/revoke` (admin): blocks future discovery by that identity.
GET `/v1/discovery` additionally accepts active `gateway:ID`, returns only allowed services.
POST `/v1/volumes/{name}/restore` (admin): id, maintenanceId, operationId, sha256, complete.
Pending reservation precedes local disk writes, completion is the administrator's receipt,
not independent storage attestation. Workloads using pending volumes cannot resume.

Heartbeat requires exact current `version` and a positive durable `sequence`. Same-sequence
changed content conflicts; lower sequence cannot refresh liveness or resurrect stopped state.
Spec `replacementPolicy` defaults to retain; duplicate-safe rejects volumes/database profiles.
The schema1→2 CLI migration directly uses local authenticated etcd with one CAS and is not
a public HTTP mutation endpoint. Existing state key is preserved; new APIs never auto-upgrade it.

## dev.4 additive routes (state schema 2 unchanged)

`GET /v1/node-state`: node mTLS only; own identity, address, observed sequence,
maintenance owner, drain and count of unconfirmed executions. No cross-node data,
application specs or secret values. Revoked/unknown nodes rejected.

`POST /v1/maintenance/nodes/{id}/drain`: admin mTLS, JSON `{ "id": "MAINTENANCE_ID" }`.
Requires owned global maintenance, live authorized node, no concurrent other drain.
Advances only affected workloads, never forces termination or moves pinned volumes.
Repeat explicitly until the projection reports zero unconfirmed executions.

`POST /v1/maintenance/nodes/{id}/uncordon`: admin mTLS, owned maintenance;
JSON includes `id`, `expectedVersion` (current exact target), `minSequence` (>0).
Requires live target version, sufficient heartbeat sequence and no unconfirmed executions.
Neither node endpoint releases global maintenance.

`GET /v1/health` additionally reports `supportedAgentVersions`.
Only dev.3 and dev.4 agents are accepted by dev.4; older/newer values are rejected.
