"""Standalone Kubernetes management frontend; separate from the native runtime."""
from __future__ import annotations
import argparse,base64,copy,json,os,pathlib,sys,time
from .common import Blocked,atomic,fingerprint,private_read,read_json,write_json
from .kube_spec import Assets,validate,version
from .kube_driver import Driver
from .kube_lifecycle import Lifecycle
from .kube_addons import Addons,order
from .kube_machines import Machines
from .kube_repair import Repair
from .kube_provision import Provision,validate_blueprint
from .kube_conformance import Conformance
from .kube_acceptance import Acceptance
from .kube_restore import Restore
from .kube_cloudscale import CloudScale,validate_request as validate_cloud_scale
from .kube_controller_recovery import ControllerRecovery, validate_request as validate_controller_recovery
from .kube_stateful_recovery import StatefulRecovery, validate_request as validate_stateful_recovery
from .kube_recovery_watch import RecoveryWatch, validate_policy
from .kube_data_restore import DataRestore, validate_spec as validate_data_restore
from .kube_release_evidence import verify as verify_release_evidence
from .cloud import Hetzner

VERSION='0.1.0-dev.3'

def parser():
    p=argparse.ArgumentParser(prog='werft-kube',description='Werftkern Kubernetes backend (k0s). Experimental; no production or CNCF certification claim.')
    p.add_argument('--root',default='/var/lib/werftkern/kubernetes');p.add_argument('--assets',help='Reviewed local tool/chart/image lock file')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('version')
    q=sub.add_parser('plan');q.add_argument('file')
    q=sub.add_parser('qualification');q.add_argument('--candidate',required=True);q.add_argument('--trust',required=True);q.add_argument('--trust-sha256',required=True)
    for cmd in ('create','upgrade','scale','apply'):
        q=sub.add_parser(cmd);q.add_argument('--plan',required=True);q.add_argument('--confirm',required=True)
    sub.add_parser('status');sub.add_parser('backup')
    q=sub.add_parser('restore');q.add_argument('--plan',required=True);q.add_argument('--backup-dir',required=True);q.add_argument('--identity',required=True);q.add_argument('--confirm',required=True)
    for cmd in ('controller-replace','stateful-replace'):
        q=sub.add_parser(cmd);q.add_argument('--spec',required=True);q.add_argument('--token-file',required=True);q.add_argument('--confirm',required=True)
    q=sub.add_parser('recovery-watch');q.add_argument('action',choices=['once','watch']);q.add_argument('--policy',required=True);q.add_argument('--token-file',required=True)
    q=sub.add_parser('data-restore');q.add_argument('--spec',required=True);q.add_argument('--confirm',required=True)
    q=sub.add_parser('setup');q.add_argument('--inventory',required=True,help='JSON array of pinned host identities');q.add_argument('--ssh-key',required=True);q.add_argument('--backup-recipient',required=True)
    q=sub.add_parser('provision');q.add_argument('--blueprint',required=True);q.add_argument('--token-file',required=True);q.add_argument('--confirm',required=True)
    q=sub.add_parser('cloud-scale');q.add_argument('--spec',required=True);q.add_argument('--token-file',required=True);q.add_argument('--confirm',required=True)
    q=sub.add_parser('addons');q.add_argument('action',choices=['plan','apply']);q.add_argument('--spec',required=True);q.add_argument('--confirm')
    q=sub.add_parser('repair');q.add_argument('action',choices=['once','watch']);q.add_argument('--token-file',required=True)
    q=sub.add_parser('sso');q.add_argument('action',choices=['plan','enable','client-config']);q.add_argument('--confirm');q.add_argument('--out')
    q=sub.add_parser('sonobuoy');ss=q.add_subparsers(dest='action',required=True)
    r=ss.add_parser('run');r.add_argument('--run-id',required=True);r.add_argument('--mode',choices=['quick','certified-conformance'],default='quick');r.add_argument('--accept-disruption',action='store_true')
    r=ss.add_parser('collect');r.add_argument('--run-id',required=True);r.add_argument('--inventory',help='Independently reviewed full [Conformance] test inventory for the exact Kubernetes version')
    q=sub.add_parser('acceptance');q.add_argument('action',choices=['run','cleanup']);q.add_argument('--confirm',required=True);q.add_argument('--namespace')
    return p

def print_json(v):print(json.dumps(v,indent=2,sort_keys=True))

def main(argv=None):
    a=parser().parse_args(argv);d=None
    os.umask(0o077)
    try:
        if a.cmd=='version':return print_json({'product':'Werftkern Kubernetes','version':VERSION,'engine':'k0s','nativeRuntimeUnchanged':'0.2.0-dev.4','productionReady':False})
        if a.cmd=='qualification':
            result=verify_release_evidence(a.candidate,a.trust,a.trust_sha256);print_json(result)
            return 0 if result['eligibleForReleaseReview'] else 3
        if a.cmd=='plan':
            v=read_json(a.file)
            validators={'werftkern-kube-fleet/v1':validate_blueprint,'werftkern-controller-recovery/v1':validate_controller_recovery,
                        'werftkern-data-restore/v1':validate_data_restore,'werftkern-stateful-recovery/v1':validate_stateful_recovery,'werftkern-recovery-policy/v1':validate_policy}
            digest=validators.get(v.get('format'),validate)(v)
            return print_json({'sha256':digest,'format':v['format'],'validation':'syntax-not-host-qualification'})
        if a.cmd=='addons' and a.action=='plan':
            v=read_json(a.spec);return print_json({'sha256':fingerprint(v),'order':order(v['addons']),'warning':'Needs pinned local charts/images, credentials, storage and real qualification.'})
        if not a.assets:raise Blocked('REVIEWED_ASSET_LOCK_REQUIRED')
        assets=Assets(a.assets);d=Driver(a.root,assets);life=Lifecycle(d)
        if a.cmd=='setup':
            versions=sorted(assets.data['k0s'],key=version)
            if not versions:raise Blocked('NO_REVIEWED_K0S_ARTIFACT')
            hosts=read_json(a.inventory);n=input('Clustername: ').strip();endpoint=input('Private API-DNS-Adresse (LB bereits eingerichtet): ').strip()
            print('Geprüfte Release-Profile: '+', '.join(versions));v=input('Exakte Version: ').strip()
            if v not in versions:raise Blocked('VERSION_NOT_IN_REVIEWED_ASSETS')
            profile='ha' if sum(h['role']=='controller' for h in hosts)==3 else 'lab'
            plan={'format':'werftkern-kubernetes/v1','name':n,'profile':profile,'version':v,'apiEndpoint':endpoint,
                'podCIDR':'10.244.0.0/16','serviceCIDR':'10.96.0.0/12','sshKeyPath':a.ssh_key,'backupRecipient':a.backup_recipient,
                'hosts':hosts,'repair':{'enabled':False,'unhealthySeconds':600,'observations':5,'minHealthyWorkers':2,
                    'maxUnhealthyPercent':40,'maxPerDay':1,'cooldownSeconds':3600,'acceptDeleteAndCosts':False}}
            if profile=='ha':plan['haControlPlane']={'mode':'external'}
            digest=validate(plan);write_json(d.root/'setup-plan.json',plan)
            print('Plan gespeichert: '+str(d.root/'setup-plan.json')+'\nPlan SHA256: '+digest)
            answer=input('Cluster auf diesen Hosts wirklich installieren? Vollständigen SHA256 eingeben: ').strip()
            return print_json(life.apply(plan,answer))
        if a.cmd in ('create','upgrade','scale','apply'):
            p=read_json(a.plan);old=life.state()
            if a.cmd=='create' and old:raise Blocked('CLUSTER_ALREADY_CREATED_USE_APPLY')
            if a.cmd in ('upgrade','scale') and not old:raise Blocked('CLUSTER_NOT_CREATED')
            if a.cmd=='upgrade' and old['plan']['version']==p['version']:raise Blocked('UPGRADE_NEEDS_DIFFERENT_TARGET_VERSION')
            if a.cmd=='scale' and old['plan']['version']!=p['version']:raise Blocked('SCALE_MUST_NOT_CHANGE_VERSION')
            return print_json(life.apply(p,a.confirm))
        if a.cmd in ('controller-replace','stateful-replace'):
            runner=ControllerRecovery(d,Machines(Hetzner(a.token_file),d)) if a.cmd=='controller-replace' else StatefulRecovery(d,Machines(Hetzner(a.token_file),d))
            return print_json(runner.step(read_json(a.spec,private=True),a.confirm))
        if a.cmd=='recovery-watch':
            runner=RecoveryWatch(d,Machines(Hetzner(a.token_file),d))
            if a.action=='once':return print_json(runner.tick(read_json(a.policy,private=True)))
            while True:
                try:print_json(runner.tick(read_json(a.policy,private=True)))
                except Blocked as e:print_json({'stage':'blocked','reason':str(e)})
                sys.stdout.flush();time.sleep(30)
        if a.cmd=='data-restore':return print_json(DataRestore(d).step(read_json(a.spec,private=True),a.confirm))
        if a.cmd=='status':return print_json(life.inspect())
        if a.cmd=='backup':return print_json(life.backup())
        if a.cmd=='restore':return print_json(Restore(d).apply(read_json(a.plan),a.backup_dir,a.identity,a.confirm))
        if a.cmd=='provision':return print_json(Provision(d,Machines(Hetzner(a.token_file),d)).apply(read_json(a.blueprint),a.confirm))
        if a.cmd=='cloud-scale':return print_json(CloudScale(d,Machines(Hetzner(a.token_file),d),life).apply(read_json(a.spec),a.confirm))
        state=life.state()
        if not state:raise Blocked('CLUSTER_NOT_CREATED')
        if a.cmd=='addons':return print_json(Addons(d,state).apply(read_json(a.spec),a.confirm))
        if a.cmd=='repair':
            runner=Repair(d,Machines(Hetzner(a.token_file),d))
            if a.action=='once':return print_json(runner.tick())
            while True:
                try:print_json(runner.tick())
                except Blocked as e:print_json({'state':'blocked','reason':str(e)})
                sys.stdout.flush();time.sleep(30)
        if a.cmd=='acceptance':
            c=Acceptance(d,state)
            return print_json(c.run(a.confirm) if a.action=='run' else c.cleanup(a.namespace,a.confirm))
        if a.cmd=='sonobuoy':
            c=Conformance(d,state)
            return print_json(c.start(a.run_id,a.mode,a.accept_disruption) if a.action=='run' else c.collect(a.run_id,a.inventory))
        if a.cmd=='sso':
            identity=read_json(d.root/'identity-state.json',private=True);p=copy.deepcopy(state['plan']);p['oidc']={'issuer':identity['issuer'],'clientId':'werft-kubectl'}
            digest=validate(p)
            if a.action=='plan':return print_json({'sha256':digest,'issuer':identity['issuer'],'grants':'viewers=view; no implicit cluster-admin'})
            if a.action=='enable':return print_json(life.apply(p,a.confirm))
            if state['plan'].get('oidc')!=p['oidc']:raise Blocked('ENABLE_OIDC_ON_API_FIRST')
            if not a.out:raise Blocked('CLIENT_CONFIG_OUTPUT_REQUIRED')
            admin=read_json(d.root/'kubeconfig.json',private=True)
            # No administrator private key is copied to the generated user config.
            cfg={'apiVersion':'v1','kind':'Config','clusters':admin['clusters'],'current-context':'werft-oidc',
                'contexts':[{'name':'werft-oidc','context':{'cluster':admin['clusters'][0]['name'],'user':'keycloak'}}],
                'users':[{'name':'keycloak','user':{'exec':{'apiVersion':'client.authentication.k8s.io/v1','interactiveMode':'IfAvailable',
                    'command':'kubectl','args':['oidc-login','get-token','--oidc-issuer-url='+p['oidc']['issuer'],'--oidc-client-id=werft-kubectl']}}}]}
            write_json(a.out,cfg,exclusive=True)
            return print_json({'path':a.out,'requires':'Separately reviewed kubectl oidc-login plugin and a real Keycloak user/group. No default password.'})
    except KeyboardInterrupt:
        print('Abgebrochen; gespeicherte Operationsjournale bleiben erhalten.',file=sys.stderr);return 130
    except (Blocked,KeyError,TypeError,ValueError,OSError) as e:
        # Never expose raw tool outputs, token files, API errors or secret values.
        reason=str(e) if isinstance(e,Blocked) else 'INPUT_OR_DEPENDENCY_ERROR:'+type(e).__name__
        print_json({'state':'BLOCKED','reason':reason,'productionReady':False});return 2
    finally:
        if d:d.close()

if __name__=='__main__':sys.exit(main())
