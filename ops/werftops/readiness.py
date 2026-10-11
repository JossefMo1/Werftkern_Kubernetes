"""Strict observed-runtime readiness for update completion, not an SLA/audit.

Never interprets API reachability, an empty reply or a cached green phase as
application health. All comparisons use the authenticated state snapshot.
"""
from __future__ import annotations
import datetime
from .common import Blocked

UTC = datetime.timezone.utc

def timestamp(value, now):
    try:
        t = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if t.tzinfo is None or not -5 <= (now - t).total_seconds() <= 30:
            raise ValueError()
        return t
    except (ValueError, TypeError, AttributeError):
        raise Blocked('OBSERVATION_STALE_OR_INVALID') from None

def check(state, cluster, operation, version, schema, now=None):
    now = now or datetime.datetime.now(UTC)
    if not isinstance(state, dict) or state.get('clusterId') != cluster:
        raise Blocked('UPDATE_CLUSTER_IDENTITY_MISMATCH')
    if state.get('schema') != schema or state.get('maintenanceId', '') != operation:
        raise Blocked('UPDATE_SCHEMA_OR_MAINTENANCE_MISMATCH')
    maps = [state.get(k) for k in ('nodes', 'workloads', 'allocations')]
    if any(not isinstance(m, dict) for m in maps):
        raise Blocked('INCOMPLETE_RUNTIME_SNAPSHOT')
    nodes, workloads, allocations = maps
    seq = {}
    for ident, node in nodes.items():
        if not isinstance(node, dict) or node.get('id') != ident:
            raise Blocked('NODE_IDENTITY_INVALID')
        if node.get('revoked') is True:
            continue
        if node.get('healthy') is not True or node.get('version') != version:
            raise Blocked('NODE_HEALTH_OR_VERSION_NOT_VERIFIED')
        timestamp(node.get('lastSeen'), now)
        n = node.get('heartbeatSequence')
        if type(n) is not int or n <= 0:
            raise Blocked('FRESH_NODE_SEQUENCE_REQUIRED')
        seq[ident] = n
    live = {}
    for ident, a in allocations.items():
        if not isinstance(a, dict) or a.get('id') != ident:
            raise Blocked('ALLOCATION_IDENTITY_INVALID')
        if a.get('phase') == 'stopped' and a.get('desired') == 'stop':
            continue
        # Pending stop/old generation/unknown owner all block completion.
        if a.get('desired') != 'run' or a.get('phase') != 'ready' or a.get('nodeId') not in seq:
            raise Blocked('ALLOCATION_NOT_OBSERVED_READY')
        timestamp(a.get('updatedAt'), now)
        name = a.get('name')
        w = workloads.get(name)
        if not isinstance(w, dict) or w.get('deleting') is True:
            raise Blocked('ORPHANED_OR_DELETING_WORKLOAD')
        if a.get('workloadUid') != w.get('uid') or a.get('generation') != w.get('generation') or a.get('spec') != w.get('spec'):
            raise Blocked('ALLOCATION_REVISION_MISMATCH')
        live[name] = live.get(name, 0) + 1
    for name, w in workloads.items():
        if not isinstance(w, dict) or w.get('name') != name or not isinstance(w.get('spec'), dict):
            raise Blocked('WORKLOAD_INVALID')
        replicas = w['spec'].get('replicas')
        if type(replicas) is not int or replicas < 0 or w.get('deleting') is True:
            raise Blocked('WORKLOAD_NOT_STABLE')
        if live.get(name, 0) != (0 if w.get('paused') is True else replicas):
            raise Blocked('REPLICA_COUNT_NOT_OBSERVED')
    return seq

def advanced(previous, current):
    if previous is not None and (set(previous) != set(current) or any(current[n] <= previous[n] for n in current)):
        raise Blocked('HEARTBEATS_DID_NOT_ADVANCE')
