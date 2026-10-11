"""Opt-in, cost-bounded observer for controller and enrolled stateful recovery.

A policy is prior authorization, not an AI decision. Stale samples, changed
identity, lost quorum and unapproved data workloads do not authorize deletion.
"""
from __future__ import annotations

import time
from .common import Blocked, fingerprint, lock, read_json, write_json
from .kube_spec import fields, integer, boolean, name, validate
from .kube_controller_recovery import ControllerRecovery, validate_request as controller_request
from .kube_stateful_recovery import StatefulRecovery, validate_request as stateful_request
from .kube_repair import ready

FORMAT = 'werftkern-recovery-policy/v1'


def validate_policy(p):
    fields(p, ('format', 'clusterUID', 'enabled', 'acceptDeleteAndCosts', 'kinds', 'unhealthySeconds',
               'observations', 'maxPerDay', 'cooldownSeconds', 'minHealthyWorkers', 'maxUnhealthyPercent',
               'maxAdditionalMonthlyEUR', 'controllerTemplate', 'workerTemplate', 'statefulSets'))
    if p['format'] != FORMAT or not isinstance(p['clusterUID'], str) or not p['clusterUID']:
        raise Blocked('RECOVERY_POLICY_INVALID')
    boolean(p['enabled']); boolean(p['acceptDeleteAndCosts'])
    if p['enabled'] and not p['acceptDeleteAndCosts']:
        raise Blocked('AUTOREPAIR_DELETE_AND_COST_CONSENT_REQUIRED')
    if (not isinstance(p['kinds'], list) or not p['kinds'] or len(p['kinds']) != len(set(p['kinds'])) or
        set(p['kinds']) - {'controller', 'stateful'}):
        raise Blocked('RECOVERY_KINDS_INVALID')
    for key, lower, upper in [('unhealthySeconds', 300, 86400), ('observations', 3, 100),
            ('maxPerDay', 1, 20), ('cooldownSeconds', 300, 86400), ('minHealthyWorkers', 1, 100),
            ('maxUnhealthyPercent', 1, 49), ('maxAdditionalMonthlyEUR', 1, 5000)]:
        integer(p[key], lower, upper)
    for template in (p['controllerTemplate'], p['workerTemplate']):
        controller_request({'format': 'werftkern-controller-recovery/v1', 'clusterUID': p['clusterUID'],
            'sourcePlanHash': '0'*64, 'controller': 'validation', 'expectedPeerURL': 'https://10.0.0.1:2380',
            'template': template, 'acceptDeleteAndCosts': True})
    if not isinstance(p['statefulSets'], list): raise Blocked('STATEFUL_ALLOWLIST_REQUIRED')
    if 'stateful' in p['kinds']:
        stateful_request({'format': 'werftkern-stateful-recovery/v1', 'clusterUID': p['clusterUID'],
            'sourcePlanHash': '0'*64, 'worker': 'validation', 'nodeUID': 'validation', 'template': p['workerTemplate'],
            'statefulSets': p['statefulSets'], 'acceptDeleteAndCosts': True})
    elif p['statefulSets']:
        raise Blocked('STATEFUL_ALLOWLIST_WITHOUT_STATEFUL_POLICY')
    return fingerprint(p)


class RecoveryWatch:
    def __init__(self, driver, machines, clock=time.time):
        self.d, self.m, self.clock = driver, machines, clock

    def tick(self, policy):
        policy_hash = validate_policy(policy)
        root = self.d.root; now = self.clock()
        with lock(root / 'recovery-watch.lock'):
            path = root / 'recovery-watch.json'
            book = read_json(path, private=True) if path.exists() else {'samples': {}, 'starts': [], 'lastSample': 0}
            if not policy['enabled']:
                return {'stage': 'disabled', 'incompleteOperation': bool(book.get('active'))}
            if now < book['lastSample'] or any(v['at'] > now for v in book['starts']):
                raise Blocked('RECOVERY_POLICY_CLOCK_ROLLBACK')
            state = read_json(root / 'cluster.json', private=True)
            if state['clusterUID'] != policy['clusterUID'] or self.d.uid() != policy['clusterUID']:
                raise Blocked('RECOVERY_POLICY_CLUSTER_IDENTITY_CHANGED')
            p = state['plan']; validate(p)
            active = book.get('active')
            if active:
                if active['policyHash'] != policy_hash:
                    raise Blocked('ACTIVE_RECOVERY_POLICY_CHANGED_REQUIRES_REVIEW')
                runner = ControllerRecovery(self.d, self.m, self.clock) if active['kind'] == 'controller' else StatefulRecovery(self.d, self.m, self.clock)
                result = runner.step(active['request'], fingerprint(active['request']))
                if result['stage'] == 'completed':
                    book.pop('active'); book['samples'] = {}; write_json(path, book)
                return result
            if now - book['lastSample'] < 30:
                return {'stage': 'observation-interval', 'mutations': False}
            if now - book['lastSample'] > 120 or book.get('policyHash') != policy_hash:
                book['samples'] = {}
            book['policyHash'], book['lastSample'] = policy_hash, now
            book['starts'] = [x for x in book['starts'] if now-x['at'] < 86400]
            if (len(book['starts']) >= policy['maxPerDay'] or
                book['starts'] and now-max(x['at'] for x in book['starts']) < policy['cooldownSeconds']):
                write_json(path, book); return {'stage': 'budget-or-cooldown', 'mutations': False}
            candidates = []
            if 'controller' in policy['kinds']:
                controllers = [h for h in p['hosts'] if h['role'] == 'controller']
                if len(controllers) != 3: raise Blocked('AUTOMATIC_CONTROLLER_RECOVERY_REQUIRES_THREE_CONTROLLERS')
                health = {h['name']: self.d.controller_reachable(h, state['clusterUID'], p['version']) for h in controllers}
                if sum(health.values()) == 2:
                    for h in controllers:
                        if not health[h['name']] and 'serverId' in h:
                            candidates.append(('controller', h, str(h['serverId'])))
                elif sum(health.values()) < 2:
                    book['samples'] = {}; write_json(path, book)
                    return {'stage': 'quorum-unavailable-no-repair', 'mutations': False}
            if 'stateful' in policy['kinds']:
                snapshot = self.d.snapshot()
                if snapshot['uid'] != state['clusterUID']: raise Blocked('RECOVERY_CLUSTER_CHANGED')
                nodes = {n['metadata']['name']: n for n in snapshot['nodes']}
                workers = [h for h in p['hosts'] if h['role'] == 'worker']
                bad = [h for h in workers if not ready(nodes.get(h['name']))]
                if len(workers)-len(bad) >= policy['minHealthyWorkers'] and len(bad)*100 <= len(workers)*policy['maxUnhealthyPercent']:
                    for h in bad:
                        n = nodes.get(h['name'])
                        if n and 'serverId' in h and state['nodeUIDs'].get(h['name']) == n['metadata']['uid']:
                            candidates.append(('stateful', h, n['metadata']['uid']))
            valid = {kind+':'+h['name'] for kind, h, _ in candidates}
            book['samples'] = {k:v for k,v in book['samples'].items() if k in valid}
            for kind, h, ident in candidates:
                key = kind+':'+h['name']
                sample = book['samples'].get(key)
                if not sample or sample['identity'] != ident:
                    sample = {'identity': ident, 'first': now, 'count': 0}; book['samples'][key] = sample
                sample['count'] += 1
                if sample['count'] < policy['observations'] or now-sample['first'] < policy['unhealthySeconds']:
                    continue
                template = policy['controllerTemplate' if kind == 'controller' else 'workerTemplate']
                cost = template['maxMonthlyEUR']
                if sum(x['monthlyCapEUR'] for x in book['starts']) + cost > policy['maxAdditionalMonthlyEUR']:
                    write_json(path, book); return {'stage': 'monthly-cost-cap', 'mutations': False}
                base = {'clusterUID': state['clusterUID'], 'sourcePlanHash': fingerprint(p),
                        'template': template, 'acceptDeleteAndCosts': True}
                if kind == 'controller':
                    request = {**base, 'format': 'werftkern-controller-recovery/v1', 'controller': h['name'],
                               'expectedPeerURL': 'https://'+h['address']+':2380'}
                else:
                    # Only workloads actually resident on this source are included, all
                    # must already appear in the immutable policy allowlist.
                    pods = self.d.request('GET', '/api/v1/pods?fieldSelector=spec.nodeName%3D'+h['name'])['items']
                    residents = {(v['metadata']['namespace'], o.get('name'), o.get('uid')) for v in pods
                        for o in v['metadata'].get('ownerReferences', []) if o.get('kind') == 'StatefulSet' and o.get('controller') is True}
                    allowed = [v for v in policy['statefulSets'] if (v['namespace'],v['name'],v['uid']) in residents]
                    if not allowed: continue
                    request = {**base, 'format': 'werftkern-stateful-recovery/v1', 'worker': h['name'], 'nodeUID': ident,
                               'statefulSets': allowed}
                book['active'] = {'kind': kind, 'request': request, 'policyHash': policy_hash}
                # Budget is reserved before mutation and not refunded on ambiguous outcomes.
                book['starts'].append({'at': now, 'monthlyCapEUR': cost, 'requestHash': fingerprint(request)})
                write_json(path, book)
                return {'stage': 'recovery-selected', 'kind': kind, 'requestHash': fingerprint(request), 'mutations': False}
            write_json(path, book)
            return {'stage': 'observing', 'mutations': False}
