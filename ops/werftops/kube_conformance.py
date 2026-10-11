"""Run official Sonobuoy, preserve evidence, never manufacture CNCF approval."""
from __future__ import annotations
import json, os, pathlib, re, secrets, tarfile, time
from .common import Blocked, atomic, canonical, digest_file, fingerprint, lock, name, read_json, sha, write_json
from .kube_spec import fields,image

def results(raw,expected=None):
    if len(raw)>64*1024*1024:raise Blocked('RESULTS_TOO_LARGE')
    items={};total=0
    for line in raw.splitlines():
        if not line.strip():continue
        total+=1
        if total>30000:raise Blocked('RESULT_COUNT_LIMIT')
        try:d=json.loads(line)
        except (ValueError,TypeError):raise Blocked('SONOBUOY_DETAIL_NOT_JSONL') from None
        if not isinstance(d,dict) or not isinstance(d.get('name'),str):raise Blocked('SONOBUOY_DETAIL_INVALID')
        if '[Conformance]' not in d['name']:continue
        if d['name'] in items:raise Blocked('DUPLICATE_CONFORMANCE_RESULT')
        if d.get('status') not in ('passed','failed','skipped'):raise Blocked('UNKNOWN_TEST_STATUS')
        items[d['name']]=d['status']
    if not items:raise Blocked('NO_CONFORMANCE_TESTS_FOUND')
    matched=False
    if expected is not None:
        if not isinstance(expected,list) or not expected or any(not isinstance(x,str) or '[Conformance]' not in x for x in expected) or len(expected)!=len(set(expected)):
            raise Blocked('INVALID_EXPECTED_TEST_INVENTORY')
        if set(items)!=set(expected):raise Blocked('CONFORMANCE_INVENTORY_MISMATCH')
        matched=True
    counts={s:sum(v==s for v in items.values()) for s in ('passed','failed','skipped')}
    return {'conformanceTests':len(items),**counts,'allReportedConformancePassed':all(v=='passed' for v in items.values()),
            'expectedInventoryMatched':matched,'fullInventoryVerified':False,'inventoryProvenance':'operator-supplied-not-independently-authenticated','cncfCertified':False,'cncfReview':'not-submitted-not-approved'}

def archive_version(file):
    found=[];budget=0
    with tarfile.open(file,'r:gz') as tf:
        for i,m in enumerate(tf):
            budget+=m.size
            if i>200000 or budget>4*1024**3:raise Blocked('SONOBUOY_ARCHIVE_LIMIT')
            if pathlib.PurePosixPath(m.name).name=='serverversion.json':
                if not m.isfile() or m.size>1024*1024:raise Blocked('SERVER_VERSION_ARCHIVE_ENTRY_INVALID')
                found.append(json.load(tf.extractfile(m)).get('gitVersion'))
    if len(found)!=1:raise Blocked('EXACTLY_ONE_SERVER_VERSION_REQUIRED_IN_ARCHIVE')
    return found[0]

class Conformance:
    def __init__(self,driver,state):self.d=driver;self.s=state
    def start(self,run_id,mode,accept_disruption):
        name(run_id)
        if mode not in ('quick','certified-conformance'):raise Blocked('SONOBUOY_MODE_INVALID')
        if mode=='certified-conformance' and not accept_disruption:raise Blocked('DISRUPTIVE_CONFORMANCE_CONFIRMATION_REQUIRED')
        with lock(self.d.root/'manager.lock'):
            op='conformance-'+run_id;dest=self.d.root/'conformance'/run_id;dest.mkdir(mode=0o700,parents=True,exist_ok=True)
            jp=dest/'run.json'
            snapshot=self.d.verify(self.s['plan'],self.s['clusterUID'])
            current=snapshot['version'].split('+')[0]
            imgs=self.d.assets.data['images'];aggregator=image(imgs['sonobuoy']);e2e=image(imgs['conformance:'+current])
            binding={'run':run_id,'mode':mode,'clusterUID':self.s['clusterUID'],'version':current,'assets':self.d.assets.fingerprint,
                'namespace':'werft-test-'+run_id,'sonobuoyImage':aggregator,'conformanceImage':e2e}
            if jp.exists():
                j=read_json(jp,private=True)
                if j['binding']!=binding:raise Blocked('CONFORMANCE_RUN_IDENTITY_CONFLICT')
                return {'run':run_id,'stage':j['stage'],'replayed':True,'note':'Existing intent is not re-executed. Collect or inspect its namespace.'}
            ns=binding['namespace']
            if self.d.request('GET','/api/v1/namespaces/'+ns,notfound=True):raise Blocked('CONFORMANCE_NAMESPACE_ALREADY_EXISTS')
            self.d.distributed_lock(op,self.s['clusterUID'])
            j={'binding':binding,'stage':'run-intent','startedAt':time.time()};write_json(jp,j,exclusive=True)
            args=['run','--namespace',ns,'--mode',mode,'--plugin','e2e','--sonobuoy-image',aggregator,'--kube-conformance-image',e2e,
                  '--kubernetes-version',current,'--timeout','21600']
            # No --skip-preflight, test focus/skip override, rerun-failed or plugin URL.
            self.d.command('sonobuoy',args,timeout=300)
            nsobj=self.d.request('GET','/api/v1/namespaces/'+ns)
            j['namespaceUID']=nsobj['metadata']['uid'];j['stage']='running';write_json(jp,j)
            return {'run':run_id,'stage':'running','cncfCertified':False}
    def collect(self,run_id,inventory=None):
        name(run_id)
        with lock(self.d.root/'manager.lock'):
            dest=self.d.root/'conformance'/run_id;jp=dest/'run.json';j=read_json(jp,private=True);b=j['binding'];ns=b['namespace']
            if b['clusterUID']!=self.s['clusterUID'] or self.d.uid()!=b['clusterUID']:raise Blocked('CONFORMANCE_CLUSTER_CHANGED')
            if b['assets']!=self.d.assets.fingerprint:raise Blocked('CONFORMANCE_TOOLS_CHANGED')
            nsobj=self.d.request('GET','/api/v1/namespaces/'+ns)
            if j.get('namespaceUID') and j['namespaceUID']!=nsobj['metadata']['uid']:raise Blocked('CONFORMANCE_NAMESPACE_REPLACED')
            # With a lost run acknowledgement the exact namespace may be observed,
            # but never recreated. Bind once after checking the aggregator image.
            pods=self.d.request('GET','/api/v1/namespaces/'+ns+'/pods')['items']
            if not any(c.get('image')==b['sonobuoyImage'] for p in pods for c in p.get('spec',{}).get('containers',[])):
                raise Blocked('SONOBUOY_AGGREGATOR_IDENTITY_MISSING')
            j['namespaceUID']=nsobj['metadata']['uid'];write_json(jp,j)
            status=json.loads(self.d.command('sonobuoy',['status','--namespace',ns,'--json']))
            write_json(dest/'status.json',status)
            plugins=[x for x in status.get('plugins',[]) if x.get('plugin')=='e2e']
            if status.get('status')!='complete' or len(plugins)!=1 or plugins[0].get('status')!='complete':
                return {'run':run_id,'stage':'not-complete','cncfCertified':False}
            tar=status.get('tar-info',{});sha(tar.get('sha256'))
            if type(tar.get('size')) is not int or not 1<=tar['size']<=1024**3:raise Blocked('SONOBUOY_ARCHIVE_SIZE_INVALID')
            archive=dest/'results.tar.gz'
            if not archive.exists():
                part=dest/'results.partial.tar.gz';part.unlink(missing_ok=True)
                self.d.command('sonobuoy',['retrieve',str(dest),'--namespace',ns,'--filename',part.name],timeout=1800)
                if part.stat().st_size!=tar['size'] or digest_file(part)!=tar['sha256']:raise Blocked('SONOBUOY_ARCHIVE_HASH_MISMATCH')
                os.chmod(part,0o600);os.replace(part,archive)
            if archive.stat().st_size!=tar['size'] or digest_file(archive)!=tar['sha256']:raise Blocked('SONOBUOY_ARCHIVE_CHANGED')
            if archive_version(archive).split('+')[0]!=b['version']:raise Blocked('ARCHIVE_SERVER_VERSION_MISMATCH')
            raw=self.d.command('sonobuoy',['results',archive,'--plugin','e2e','--mode','detailed'],timeout=120)
            atomic(dest/'results.jsonl',raw)
            expected=None
            if inventory:
                v=read_json(inventory)
                fields(v,('kubernetesVersion','tests'))
                if v['kubernetesVersion']!=b['version']:raise Blocked('INVENTORY_VERSION_MISMATCH')
                expected=v['tests']
            report=results(raw,expected)
            report['pluginResult']=plugins[0].get('result-status','unknown')
            report['runPassed']=report['allReportedConformancePassed'] and report['pluginResult']=='passed'
            report.update({'run':run_id,'mode':b['mode'],'archiveSHA256':tar['sha256'],'clusterUID':b['clusterUID'],
               'kubernetesVersion':b['version'],'certificationTestMode':b['mode']=='certified-conformance',
               'observedCompletedAt':time.time(),'productionReady':False})
            write_json(dest/'report.json',report)
            j['stage']='collected';write_json(jp,j)
            # Retain namespace and original evidence; delete is a separate reviewed
            # operator action. Never submit potentially sensitive data automatically.
            self.d.unlock('conformance-'+run_id,b['clusterUID'])
            return report
