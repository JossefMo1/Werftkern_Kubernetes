## Scope and issue
Describe the change and reference relevant issues / ADRs.

## Executed tests (exact evidence)
Provide command, environment, result and CI links. Distinguish
fixtures and simulated results from actual live VM, Kubernetes,
etcd, network partition, backup or database evidence.

## Trust boundaries, security and supply chain
- [ ] No credentials, private keys, tokens, customer/private data or
      unintended intellectual-property transfers.
- [ ] Source tree and reachable Git history reviewed for sensitive data.
- [ ] No privileged self-hosted workflow execution of untrusted PR code.
- [ ] Permissions are minimal; workflows avoid `pull_request_target`
      with an untrusted checkout.
- [ ] Known risks, concurrency and recovery replay behavior explained.

## Compatibility, migrations and rollback
Explain version/source compatibility and any unavailable historical
baseline. A missing historical Git commit is an UNVERIFIED gate, not a pass.

## Release and claims
- [ ] No unsupported claim of production readiness, CNCF certification,
      signed artifact provenance, SLA or independent audit.
- [ ] Documentation, changelog and license notices updated as needed.
- [ ] Maintainer review requested for critical operations.

Commit signatures are **optional**. Use of a Signed-off-by trailer for
contribution provenance is separate from GPG/SSH commit signing.
