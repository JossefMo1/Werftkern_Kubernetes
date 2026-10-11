"""Lifecycle of evidence with command/Kubernetes fixtures; no live Sonobuoy run."""
import copy,hashlib,io,json,pathlib,tarfile,tempfile,unittest
from test_backend import plan,FakeDriver,IMG
from werftops.common import Blocked,canonical,fingerprint,read_json
from werftops.kube_conformance import Conformance
from werftops.kube_acceptance import Acceptance

class SonobuoyDriver(FakeDriver):
    def __init__(self,root):
        super().__init__(root);self.namespaces={};self.run_count=0;self.lose=False;self.outside=False
        out=io.BytesIO()
        with tarfile.open(fileobj=out,mode='w:gz') as tf:
            b=canonical({'gitVersion':'v1.35.1+k0s'});i=tarfile.TarInfo('serverversion.json');i.size=len(b);tf.addfile(i,io.BytesIO(b))
        self.archive=out.getvalue()
    def request(self,m,p,payload=None,notfound=False):
        if p.startswith('/api/v1/namespaces/'):
            ns=p.split('/')[4]
            if p.endswith('/pods'):return {'items':[{'spec':{'containers':[{'image':IMG}]}}]}
            if m=='GET':
                if ns not in self.namespaces and not notfound:raise Blocked('KUBE_HTTP_404')
                return self.namespaces.get(ns)
        return super().request(m,p,payload,notfound)
    def command(self,tool,args,**kw):
        args=list(map(str,args));self.calls.append(('cmd',tool,args))
        if args[0]=='run':
            self.run_count+=1;ns=args[args.index('--namespace')+1];self.namespaces[ns]={'metadata':{'uid':'ns-uid'}}
            if self.lose:raise Blocked('RUN_ACK_LOST')
            return b''
        if args[0]=='status':
            return canonical({'status':'complete','plugins':[{'plugin':'e2e','status':'complete'}],
              'tar-info':{'sha256':hashlib.sha256(self.archive).hexdigest(),'size':len(self.archive)}})
        if args[0]=='retrieve':
            (pathlib.Path(args[1])/args[args.index('--filename')+1]).write_bytes(self.archive);return b''
        if args[0]=='results':return canonical({'name':'fixture [Conformance] networking','status':'passed'})+b'\n'
        raise AssertionError(args)

class RunTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.d=SonobuoyDriver(self.tmp.name);self.c=Conformance(self.d,{'plan':plan(),'clusterUID':'cluster-uid'})
    def tearDown(self):self.tmp.cleanup()
    def test_exact_run_flags_no_focus_skip_or_rerun(self):
        self.c.start('proof','certified-conformance',True)
        cmd=next(x[2] for x in self.d.calls if x[0]=='cmd')
        self.assertIn('certified-conformance',cmd);self.assertIn('--kube-conformance-image',cmd)
        self.assertFalse(any(x in cmd for x in ('--skip-preflight','--e2e-focus','--e2e-skip','--rerun-failed')))
    def test_lost_start_ack_is_not_reissued(self):
        self.d.lose=True
        with self.assertRaises(Blocked):self.c.start('proof','certified-conformance',True)
        self.c.start('proof','certified-conformance',True)
        self.assertEqual(self.d.run_count,1)
        r=self.c.collect('proof');self.assertTrue(r['allReportedConformancePassed']);self.assertFalse(r['cncfCertified'])
    def test_collect_checks_archive_and_never_certifies(self):
        self.c.start('proof','certified-conformance',True);r=self.c.collect('proof')
        self.assertFalse(r['cncfCertified']);self.assertFalse(r['fullInventoryVerified']);self.assertFalse(r['productionReady'])
        self.assertTrue((self.d.root/'conformance/proof/results.tar.gz').exists())
    def test_changed_archive_rejected(self):
        self.c.start('proof','certified-conformance',True);self.c.collect('proof')
        (self.d.root/'conformance/proof/results.tar.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(Blocked,'ARCHIVE_CHANGED'):self.c.collect('proof')
    def test_foreign_namespace_not_adopted(self):
        self.d.namespaces['werft-test-proof']={'metadata':{'uid':'foreign'}}
        with self.assertRaises(Blocked):self.c.start('proof','quick',False)
        self.assertEqual(self.d.run_count,0)
    def test_changed_namespace_uid_rejected(self):
        self.c.start('proof','quick',False);self.d.namespaces['werft-test-proof']['metadata']['uid']='replacement'
        with self.assertRaises(Blocked):self.c.collect('proof')
    def test_no_real_smoke_without_explicit_disposable_ack(self):
        with self.assertRaises(Blocked):Acceptance(self.d,{'plan':plan(),'clusterUID':'cluster-uid'}).run('yes')
        self.assertEqual(self.d.calls,[])

if __name__=='__main__':unittest.main()
