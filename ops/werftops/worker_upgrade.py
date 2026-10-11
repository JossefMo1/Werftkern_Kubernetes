"""Node-local, signed same-schema update helper.

Can be executed from an already signature-verified target package, BEFORE that
package is installed. It never receives a controller admin certificate, never
unlocks a cluster and never retries an uncertain dpkg mutation automatically.
"""
from __future__ import annotations
import json
import pathlib
import re
import time
from .common import Blocked, fingerprint, host_preflight, lock, read_json, run, write_json
from . import upgrade

ROOT = pathlib.Path('/var/lib/werftkern')
CONFIG = pathlib.Path('/etc/werftkern')
TRUST = CONFIG / 'trust/releases.pem'
VERSION = '0.2.0-dev.4'

def ident(v):
    if not isinstance(v, str) or not re.fullmatch('[a-f0-9]{32}', v):
        raise Blocked('INVALID_OPERATION_OR_NODE_ID')
    return v

def _owned_node(status, cfg, operation, cluster, node):
    if not isinstance(status, dict) or status.get('clusterId') != cluster or status.get('nodeId') != node or status.get('instanceId') != cfg['instanceId'] or status.get('address') != cfg['address']:
        raise Blocked('WORKER_SCOPE_IDENTITY_MISMATCH')
    if status.get('maintenanceId') != operation or status.get('drain') is not True or status.get('unconfirmedAllocations') != 0:
        raise Blocked('OWNED_DRAINED_EMPTY_NODE_REQUIRED')
    if status.get('stateSchema') != 2 or status.get('controllerVersion') != VERSION:
        raise Blocked('TARGET_CONTROLLERS_REQUIRED')

def install(package, manifest, signature, operation, cluster, node, staged_binary, runner=run):
    host_preflight()
    ident(operation); ident(cluster); ident(node)
    if (CONFIG / 'control.json').exists():
        raise Blocked('WORKER_ONLY_HOST_REQUIRED')
    cfg = read_json(CONFIG / 'agent.json', private=True)
    if cfg.get('nodeId') != node or cfg.get('client', {}).get('clusterId') != cluster:
        raise Blocked('LOCAL_WORKER_IDENTITY_MISMATCH')
    m = upgrade.verify(package, manifest, signature, TRUST, runner)
    if m.get('version') != VERSION or m.get('stateSchema') != 2:
        raise Blocked('TARGET_HELPER_VERSION_MISMATCH')
    pv = runner(['dpkg-deb', '-f', str(package), 'Version']).decode().strip()
    pn = runner(['dpkg-deb', '-f', str(package), 'Package']).decode().strip()
    if pn != 'werftkern' or pv != m['packageVersion']:
        raise Blocked('PACKAGE_IDENTITY_MISMATCH')
    socket = cfg.get('socket')
    if not isinstance(socket,str) or not socket.startswith('/') or '\x00' in socket or '\n' in socket:
        raise Blocked('LOCAL_ENGINE_SOCKET_REQUIRED')
    request = fingerprint({'operation': operation, 'cluster': cluster, 'node': node,
                           'instance': cfg['instanceId'], 'manifest': m})
    home = ROOT / 'worker-updates' / operation
    with lock(ROOT / 'update.lock'):
        journal = home / 'host.json'
        if journal.exists():
            j = read_json(journal, private=True)
            if j.get('requestHash') != request:
                raise Blocked('WORKER_UPDATE_REPLAY_CONFLICT')
            # No mutation on replay: even a missing SSH reply cannot justify a
            # second package installation. A partial install is operator recovery.
            if j.get('phase') != 'installed-awaiting-controller':
                raise Blocked('UNCERTAIN_WORKER_UPDATE_REQUIRES_INSPECTION')
            actual = runner(['dpkg-query', '-W', '-f=${Version}', 'werftkern']).decode().strip()
            if actual != m['packageVersion']:
                raise Blocked('REPLAY_INSTALLED_PACKAGE_CHANGED')
            return j
        current = runner(['dpkg-query', '-W', '-f=${Version}', 'werftkern']).decode().strip()
        if current not in m['sources']:
            raise Blocked('WORKER_SOURCE_NOT_ALLOWED')
        status = json.loads(runner([str(staged_binary), 'worker-status', '--json']))
        _owned_node(status, cfg, operation, cluster, node)
        if status.get('healthy') is not True or type(status.get('heartbeatSequence')) is not int or status['heartbeatSequence'] <= 0:
            raise Blocked('LIVE_WORKER_REQUIRED_BEFORE_STOP')
        def empty_engine():
            ids = runner(['docker', '--host', 'unix://'+socket, 'ps', '-aq', '--filter', 'label=org.werftkern.runtime.cluster='+cluster], env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin'}).strip()
            if ids:
                raise Blocked('OWNED_CONTAINERS_STILL_PRESENT')
        empty_engine()
        j = {'format': 'werftkern-worker-update/v1', 'requestHash': request, 'operationId': operation,
             'clusterId': cluster, 'nodeId': node, 'instanceId': cfg['instanceId'],
             'packageSha256': m['packageSha256'], 'packageVersion': pv, 'version': VERSION,
             'from': current, 'beforeSequence': status['heartbeatSequence'], 'phase': 'stop-intent'}
        write_json(journal, j, exclusive=True)
        runner(['systemctl', 'stop', 'werftkern-agent'])
        empty_engine()
        # Query authoritative state again AFTER stopping. A stopped process is
        # not sufficient when another admin has removed the maintenance lock.
        _owned_node(json.loads(runner([str(staged_binary), 'worker-status', '--json'])), cfg, operation, cluster, node)
        j['phase'] = 'install-intent'; write_json(journal, j)
        runner(['dpkg', '--install', str(package)], timeout=600)
        actual = runner(['dpkg-query', '-W', '-f=${Version}', 'werftkern']).decode().strip()
        version = runner(['/usr/bin/werft', 'version']).decode().splitlines()
        if actual != pv or not version or version[0] != 'Werftkern '+VERSION:
            raise Blocked('WORKER_INSTALLED_IDENTITY_MISMATCH')
        j['phase'] = 'start-intent'; write_json(journal, j)
        runner(['systemctl', 'start', 'werftkern-agent'])
        runner(['systemctl', 'is-active', '--quiet', 'werftkern-agent'])
        j['phase'] = 'installed-awaiting-controller'; write_json(journal, j)
        return j

def receipt(operation):
    ident(operation)
    j = read_json(ROOT / 'worker-updates' / operation / 'host.json', private=True)
    if j.get('format') != 'werftkern-worker-update/v1' or j.get('operationId') != operation:
        raise Blocked('WORKER_RECEIPT_INVALID')
    return j
