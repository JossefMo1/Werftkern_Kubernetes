# Werftkern architecture

Separate Open-Source module; no commercial ClusterPilot runtime dependency.
`werft` is a Go binary (stdlib only); `werft-ops` provides explicit Python3 administrative
operations. Ubuntu/systemd starts control, agent, etcd and optional DNS; these components
are not scheduled by the cluster they bootstrap.

State authority is one bounded etcd-CAS aggregate. Three controllers may propose changes;
only the transaction winner commits capacity, volume ownership and allocations together.
Periodic reconciliation replaces a watch, deliberately trading scalability for simplicity.
Current hard bounds:20 nodes,50 workloads,200 allocations,900000 state bytes. This is
not a published performance envelope or a linear scalability claim.

Nodes authenticate with individual mTLS certificates. A node reports its own allocations,
may read their versioned secrets/volume descriptors, and may read nonsecret discovery
endpoints. Admin identity handles admission. This is not multi-tenant RBAC or OIDC.

The node journal is durable before runtime side effects. Docker resources carry cluster,
allocation and spec identity labels. Containers run nonroot with no-new-privileges,
read-only rootfs, dropped capabilities and bounded resources. The agent still controls
the Docker socket and therefore has high host authority. No rootless claim is made.

Node-bound volume claims are exclusive and retain ownership/data after delete. Stateful
updates wait for confirmed stop, preventing a second planned writer. Loss of contact
is not fencing; no automatic stateful move. Missing initialized storage fails closed.

WireGuard is an optional host mesh; Docker allocates per-node container IPs from fixed
non-overlapping subnets. The agent reports these IPs; the API verifies subnet ownership.
CoreDNS is an independent binary reading generated A/SRV records with expiry behavior.
No service VIP, CNI compatibility, Envoy ingress or per-workload network policy is claimed.

Cloud provisioning persists create intent before HTTP side effects and refuses uncertain
retries. Controller package changes own an etcd-backed maintenance lock and a local
journal. Native release signatures authenticate bytes, not safety or production maturity.

Private snapshots, keys, provisioning journals and deployment kits never belong in Git.
Public-source checks are pattern lint, not comprehensive independent security assessment.
