"""Bounded controller replacement for an existing three-controller k0s cluster.

Provider deletion precedes etcd-member removal. Two surviving controllers must
independently agree on membership and cluster identity before either operation.
This is NOT quorum-loss recovery and never uses force-new-cluster.
"""
from __future__ import annotations

import copy
import re
import time
from .common import Blocked, fingerprint, lock, read_json, write_json, sha
from .kube_spec import fields, name, integer, validate
from .kube_fencing import Fence
from .kube_provider_identity import assert_identity


FORMAT = 'werftkern-controller-recovery/v1'


def validate_request(r):
    fields(r, ('format', 'clusterUID', 'sourcePlanHash', 'controller', 'expectedPeerURL',
               'template', 'acceptDeleteAndCosts'))
    if r['format'] != FORMAT or r['acceptDeleteAndCosts'] is not True:
        raise Blocked('CONTROLLER_RECOVERY_EXPLICIT_DELETE_AND_COST_CONSENT_REQUIRED')
    name(r['controller']); sha(r['sourcePlanHash'])
    if not isinstance(r['clusterUID'], str) or not 1 <= len(r['clusterUID']) <= 128:
        raise Blocked('CLUSTER_UID_REQUIRED')
    t = r['template']
    fields(t, ('location', 'serverType', 'imageId', 'networkId', 'firewallId', 'sshKeyId', 'maxMonthlyEUR'))
    name(t['location']); name(t['serverType'])
    for k in ('imageId', 'networkId', 'firewallId', 'sshKeyId'):
        integer(t[k], 1, 2**63 - 1)
    integer(t['maxMonthlyEUR'], 1, 1000)
    if not isinstance(r['expectedPeerURL'], str) or not re.fullmatch(r'https://[0-9.]+:2380', r['expectedPeerURL']):
        raise Blocked('EXPECTED_ETCD_PEER_REQUIRED')
    return fingerprint(r)


def assert_members(members, expected):
    if not isinstance(members, dict) or members != expected:
        raise Blocked('ETCD_MEMBERSHIP_DIFFERS_FROM_PINNED_TOPOLOGY')


class ControllerRecovery:
    def __init__(self, driver, machines, clock=time.time):
        self.d, self.m, self.clock = driver, machines, clock
        self.fence = Fence(machines, clock)

    def _survivors(self, plan, old, cluster_uid, expected):
        survivors = [h for h in plan['hosts'] if h['role'] == 'controller' and h['name'] != old['name']]
        if len(survivors) != 2:
            raise Blocked('EXACTLY_TWO_SURVIVING_CONTROLLERS_REQUIRED')
        for h in survivors:
            self.d.controller_observe(h, cluster_uid, plan['version'])
            assert_members(self.d.etcd_members(plan, h), expected)
        return survivors

    def step(self, request, confirm):
        digest = validate_request(request)
        if digest != confirm:
            raise Blocked('EXACT_CONTROLLER_RECOVERY_CONFIRMATION_REQUIRED')
        root = self.d.root
        with lock(root / 'manager.lock'):
            state = read_json(root / 'cluster.json', private=True)
            jp = root / 'controller-recovery.json'
            j = read_json(jp, private=True) if jp.exists() else None
            operation = fingerprint({'request': request, 'assets': self.d.assets.fingerprint})
            if j and j['operation'] != operation:
                if j['stage'] != 'completed':
                    raise Blocked('OTHER_CONTROLLER_RECOVERY_IN_PROGRESS')
                j = None
            if j and j['stage'] == 'completed':
                return {'stage': 'completed', 'historicallyCompleted': True, 'operation': operation}
            active = read_json(root / 'active.json', private=True) if (root / 'active.json').exists() else None
            if active and active['stage'] != 'completed':
                raise Blocked('LIFECYCLE_OPERATION_IN_PROGRESS')
            if not j:
                p = state['plan']; validate(p)
                if p['profile'] != 'ha' or state['clusterUID'] != request['clusterUID'] or fingerprint(p) != request['sourcePlanHash']:
                    raise Blocked('CONTROLLER_RECOVERY_SOURCE_CHANGED')
                old = next((h for h in p['hosts'] if h['name'] == request['controller'] and h['role'] == 'controller'), None)
                if not old or 'serverId' not in old:
                    raise Blocked('MANAGED_HETZNER_CONTROLLER_REQUIRED')
                if request['expectedPeerURL'] != 'https://' + old['address'] + ':2380':
                    raise Blocked('ETCD_PEER_DOES_NOT_MATCH_SOURCE_HOST')
                expected = {h['name']: 'https://' + h['address'] + ':2380' for h in p['hosts'] if h['role'] == 'controller'}
                self._survivors(p, old, state['clusterUID'], expected)
                if self.d.controller_reachable(old, state['clusterUID'], p['version']):
                    raise Blocked('CONTROLLER_RECOVERED_OR_NOT_FAILED')
                if self.d.request('GET', '/api/v1/nodes/' + old['name'], notfound=True):
                    raise Blocked('COMBINED_CONTROLLER_WORKER_NOT_SUPPORTED')
                self.m.preflight(request['template'])
                self.d.distributed_lock('controller-' + operation, state['clusterUID'])
                j = {'format': FORMAT, 'operation': operation, 'stage': 'preflight', 'source': state,
                     'request': request, 'old': old, 'expectedMembers': expected, 'fence': {}, 'machine': {}, 'startedAt': self.clock()}
                write_json(jp, j)
            p, old, uid = j['source']['plan'], j['old'], j['source']['clusterUID']
            if state['clusterUID'] != uid or (fingerprint(state['plan']) != fingerprint(p) and
                                            state['plan'] != j.get('target')):
                raise Blocked('CONTROLLER_RECOVERY_SOURCE_CHANGED')
            if j['fence']:assert_identity(self.m,j['fence'])
            if self.clock() < j['startedAt']:
                raise Blocked('RECOVERY_CLOCK_ROLLBACK')
            if j['stage'] != 'unlocking':
                self.d.distributed_lock('controller-' + operation, uid)
            def save(): write_json(jp, j)
            if j['stage'] == 'preflight':
                survivors = self._survivors(p, old, uid, j['expectedMembers'])
                if self.d.controller_reachable(old, uid, p['version']):
                    raise Blocked('CONTROLLER_RECOVERED_BEFORE_DESTRUCTION')
                # Backup uses a survivor only; no SSH attempt to the failed member.
                j['backup'] = self.d.backup_survivor(p, survivors[0], root / 'backups' / ('controller-' + operation))
                if j['backup'].get('clusterUID') != uid:
                    raise Blocked('CONTROLLER_BACKUP_CLUSTER_MISMATCH')
                control = self.d.control_node(old['name'])
                j['controlNode'] = control
                j['stage'] = 'fencing'; save()
            if j['stage'] == 'fencing':
                self._survivors(p, old, uid, j['expectedMembers'])
                if not j['fence'] and self.d.controller_reachable(old, uid, p['version']):
                    raise Blocked('CONTROLLER_RECOVERED_BEFORE_DESTRUCTION')
                if not self.fence.step(p['name'], old, operation, [], j['fence'], save):
                    return {'stage': 'waiting-provider-fence', 'operation': operation}
                j['stage'] = 'removing-member'; save()
            expected_left = {n: u for n, u in j['expectedMembers'].items() if n != old['name']}
            if j['stage'] in ('removing-member', 'member-remove-intent'):
                if not self.fence.step(p['name'], old, operation, [], j['fence'], save):
                    raise Blocked('PERMANENT_FENCE_REQUIRED')
                survivors = [h for h in p['hosts'] if h['role'] == 'controller' and h['name'] != old['name']]
                observed = []
                for h in survivors:
                    self.d.controller_observe(h, uid, p['version'])
                    observed.append(self.d.etcd_members(p, h))
                if observed[0] != observed[1]:
                    raise Blocked('SURVIVOR_ETCD_MEMBERSHIP_DISAGREEMENT')
                if observed[0] == expected_left:
                    if j['stage'] != 'member-remove-intent':
                        raise Blocked('ETCD_MEMBERSHIP_CHANGED_OUTSIDE_OPERATION')
                else:
                    assert_members(observed[0], j['expectedMembers'])
                    if j['stage'] == 'member-remove-intent':
                        raise Blocked('ETCD_LEAVE_OUTCOME_UNKNOWN_NO_BLIND_RETRY')
                    self.d.delete_control_node(j['controlNode'])
                    j['stage'] = 'member-remove-intent'; save()
                    self.d.etcd_leave(p, survivors[0], request['expectedPeerURL'])
                    return {'stage': 'waiting-member-removal', 'operation': operation}
                j['stage'] = 'creating'; save()
            if j['stage'] == 'creating':
                self._survivors(p, old, uid, expected_left)
                if not self.fence.step(p['name'], old, operation, [], j['fence'], save):
                    raise Blocked('PERMANENT_FENCE_REQUIRED')
                replacement = self.m.create(p['name'], 'controller', old.get('pool', 'default'), operation,
                                            request['template'], root / 'controller-machines' / operation, j['machine'], save)
                target = copy.deepcopy(p)
                target['hosts'] = [h for h in p['hosts'] if h['name'] != old['name']] + [replacement]
                validate(target)
                if replacement['serverId'] == old['serverId'] or replacement['address'] == old['address']:
                    raise Blocked('FRESH_CONTROLLER_IDENTITY_REQUIRED')
                j['new'], j['target'], j['stage'] = replacement, target, 'preparing'; save()
            if j['stage'] == 'preparing':
                self.d.fresh_hosts(j['target'], [j['new']['name']])
                j['stage'] = 'joining'; save()
            if j['stage'] == 'joining':
                if not self.fence.step(p['name'], old, operation, [], j['fence'], save):
                    raise Blocked('PERMANENT_FENCE_REQUIRED')
                self.d.apply(j['target'])  # k0sctl owns idempotent host reconciliation.
                j['stage'] = 'verifying'; save()
            if j['stage'] == 'verifying':
                result = self.d.verify(j['target'], uid)
                expected = {h['name']: 'https://' + h['address'] + ':2380' for h in j['target']['hosts'] if h['role'] == 'controller'}
                for h in (h for h in j['target']['hosts'] if h['role'] == 'controller'):
                    assert_members(self.d.etcd_members(j['target'], h), expected)
                j['result'] = result; j['stage'] = 'commit'; save()
            if j['stage'] == 'commit':
                write_json(root / 'cluster.json', {'format': 'werftkern-kube-state/v1', 'plan': j['target'], **j['result']})
                j['stage'] = 'unlocking'; save()
            if j['stage'] == 'unlocking':
                self.d.unlock('controller-' + operation, uid)
                j['stage'] = 'completed'; j['completedAt'] = self.clock(); save()
                write_json(root / 'controller-history' / (operation + '.json'), j)
            return {'stage': j['stage'], 'operation': operation, 'productionQualified': False}
