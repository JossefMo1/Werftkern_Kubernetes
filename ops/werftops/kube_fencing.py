"""Irreversible, journal-bound Hetzner host fencing; never a power-off heuristic.

Only permanent deletion of a previously observed, explicitly owned server is
accepted. The caller persists the journal before a request and provides the
cluster lock. A timeout is NOT proof of deletion. No automatic DELETE retries.
"""
from __future__ import annotations

import time
from .common import Blocked, fingerprint
from .kube_provider_identity import identity, assert_identity


def server_identity(server):
    if not isinstance(server, dict) or type(server.get('id')) is not int:
        raise Blocked('FENCE_SERVER_IDENTITY_INVALID')
    if not isinstance(server.get('created'), str) or not server['created']:
        raise Blocked('FENCE_SERVER_CREATION_IDENTITY_REQUIRED')
    return {k: server.get(k) for k in ('id', 'name', 'created', 'labels')}


class Fence:
    def __init__(self, machines, clock=time.time):
        self.m, self.clock = machines, clock

    def step(self, cluster, host, operation, allowed_volume_ids, journal, save):
        now = self.clock()
        if journal and (journal.get('operation') != operation or
                        journal.get('serverId') != host['serverId']):
            raise Blocked('FENCE_JOURNAL_IDENTITY_CHANGED')
        if now < journal.get('lastObservedAt', 0):
            raise Blocked('FENCE_CLOCK_ROLLBACK')
        if journal:assert_identity(self.m,journal)
        credential=identity(self.m)
        server = self.m.get(host['serverId'])
        if not journal:
            self.m.ownership(server, cluster, host['role'], host.get('pool', 'default'), host['name'])
            if server.get('id') != host['serverId']:
                raise Blocked('FENCE_PROVIDER_ID_MISMATCH')
            networks = server.get('private_net', [])
            if host['address'] not in [n.get('ip') for n in networks]:
                raise Blocked('FENCE_PROVIDER_PRIVATE_ADDRESS_CHANGED')
            if set(server.get('volumes', [])) - set(allowed_volume_ids):
                raise Blocked('FENCE_UNAPPROVED_ATTACHED_VOLUMES')
            if server.get('protection', {}).get('delete'):
                raise Blocked('FENCE_SERVER_DELETE_PROTECTION_ENABLED')
            journal.update(providerCredential=credential,operation=operation, serverId=host['serverId'],
                           source=server_identity(server), allowedVolumes=sorted(allowed_volume_ids),
                           stage='delete-intent', intentAt=now, lastObservedAt=now,
                           sourceFingerprint=fingerprint(server_identity(server)), absenceCount=0)
            save()  # Crash before the request is conservative: operator review, not blind retry.
            try:
                self.m.api.call('DELETE', '/servers/' + str(host['serverId']))
            except Blocked:
                pass  # Both known failures and ambiguous responses stay unconfirmed.
            return False
        if journal['allowedVolumes'] != sorted(allowed_volume_ids):
            raise Blocked('FENCE_VOLUME_SCOPE_CHANGED')
        if server is not None:
            if fingerprint(server_identity(server)) != journal['sourceFingerprint']:
                raise Blocked('FENCE_SOURCE_IDENTITY_CHANGED')
            if journal['stage'] == 'confirmed-absent':
                raise Blocked('FENCE_ABSENT_SERVER_REAPPEARED')
            journal['absenceCount'] = 0
            journal['lastObservedAt'] = now
            save()
            return False
        # Two separated live reads; a cached local receipt alone never authorizes new work.
        if journal['stage'] == 'confirmed-absent':
            journal['lastObservedAt'] = now
            save()
            return True
        if now - journal['lastObservedAt'] < 1:
            return False
        journal['absenceCount'] += 1
        journal['lastObservedAt'] = now
        if journal['absenceCount'] >= 2:
            journal['stage'] = 'confirmed-absent'
            journal['confirmedAt'] = now
        save()
        return journal['stage'] == 'confirmed-absent'
