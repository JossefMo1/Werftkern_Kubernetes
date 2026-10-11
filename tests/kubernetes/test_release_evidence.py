"""Real Ed25519 signatures over synthetic qualification data, NOT real qualification."""
import base64
import copy
import datetime as dt
import pathlib
import tempfile
import unittest
from werftops.common import Blocked, canonical, digest_file, run, write_json
from werftops.kube_release_evidence import GATES, verify


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys_tmp=tempfile.TemporaryDirectory();cls.keys=pathlib.Path(cls.keys_tmp.name)
        for n in ('builder','reviewer'):
            run(['/usr/bin/openssl','genpkey','-algorithm','ED25519','-out',str(cls.keys/(n+'.key'))])
            run(['/usr/bin/openssl','pkey','-in',str(cls.keys/(n+'.key')),'-pubout','-out',str(cls.keys/(n+'.pub'))])
    @classmethod
    def tearDownClass(cls):cls.keys_tmp.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=pathlib.Path(self.tmp.name)
        self.bundle=self.base/'candidate';self.bundle.mkdir();self.trustdir=self.base/'trust';self.trustdir.mkdir()
        for n in ('builder','reviewer'):(self.trustdir/(n+'.pub')).write_bytes((self.keys/(n+'.pub')).read_bytes())
        self.now=dt.datetime(2026,9,26,12,tzinfo=dt.timezone.utc)
        self.artifact=self.bundle/'test.deb';self.artifact.write_bytes(b'synthetic test artifact, not a release package')
        self.c={'format':'werftkern-release-candidate/v1','sourceCommit':'a'*40,'sourceRepository':'https://github.com/example/werftkern',
                'builderId':'https://builder.example.test/build','assetsSHA256':'b'*64,'artifact':self.ref(self.artifact),'evidence':[]}
        self.t={'format':'werftkern-evidence-trust/v1','maxAgeDays':7,'keys':[]}
        for n,roles,org in [('builder',['builder','qualifier','release-manager','certification-verifier'],'product-org'),('reviewer',['independent-reviewer'],'review-org')]:
            self.t['keys'].append({'id':n,'roles':roles,'organization':org,'publicKey':self.ref(self.trustdir/(n+'.pub')),
                                   'validFrom':'2026-01-01T00:00:00Z','validUntil':'2027-01-01T00:00:00Z'})
        self.statements={};self.trustpath=self.trustdir/'trust.json';self.cp=self.bundle/'candidate.json'
    def ref(self,p):return {'path':p.name,'sha256':digest_file(p)}
    def document(self,n,v):
        p=self.bundle/n;write_json(p,v);return self.ref(p)
    def gate(self,g):
        e=self.bundle/(g+'.log');e.write_text('SYNTHETIC TEST EVIDENCE - NOT A REAL QUALIFICATION\n')
        s={'format':'werftkern-gate-evidence/v1','gate':g,'sourceCommit':self.c['sourceCommit'],
           'artifactSHA256':self.c['artifact']['sha256'],'assetsSHA256':self.c['assetsSHA256'],'status':'passed',
           'startedAt':'2026-09-26T10:00:00Z','finishedAt':'2026-09-26T11:00:00Z',
           'environment':{'kind':GATES[g][1],'identities':['synthetic-test-identity']},'evidence':[self.ref(e)]}
        if g=='supply-chain':
            s['documents']={'sbom':self.document('sbom.json',{'bomFormat':'CycloneDX','components':[{'name':'synthetic-test-only'}]}),
                'vulnerabilities':self.document('trivy.json',{'SchemaVersion':2,'Results':[{'Target':'synthetic-test','Vulnerabilities':[]}]}),
                'provenance':self.document('provenance.json',{'_type':'https://in-toto.io/Statement/v1','predicateType':'https://slsa.dev/provenance/v1',
                    'subject':[{'name':self.artifact.name,'digest':{'sha256':self.c['artifact']['sha256']}}],
                    'predicate':{'runDetails':{'builder':{'id':self.c['builderId']}},'buildDefinition':{'resolvedDependencies':[
                        {'uri':self.c['sourceRepository'],'digest':{'gitCommit':self.c['sourceCommit']}},
                        {'uri':'assets.json','digest':{'sha256':self.c['assetsSHA256']}}]}}})}
        if g=='cncf-acceptance':s['decisionURL']='https://github.com/cncf/k8s-conformance/pull/1'
        self.statements[g]=s
    def save(self,signer_override=None):
        self.c['evidence']=[]
        for g,s in self.statements.items():
            key=(signer_override or {}).get(g,'reviewer' if g=='independent-security' else 'builder')
            payload=self.base/'payload';payload.write_bytes(canonical(s));sig=self.base/'sig'
            run(['/usr/bin/openssl','pkeyutl','-sign','-rawin','-inkey',str(self.keys/(key+'.key')),'-in',str(payload),'-out',str(sig)])
            self.c['evidence'].append(self.document(g+'.json',{'statement':s,'keyId':key,'signature':base64.b64encode(sig.read_bytes()).decode()}))
        write_json(self.cp,self.c);write_json(self.trustpath,self.t)
    def check(self):return verify(self.cp,self.trustpath,digest_file(self.trustpath),self.now)
    def test_complete_synthetic_evidence_never_becomes_production_or_certificate(self):
        for g in GATES:self.gate(g)
        self.save();r=self.check();self.assertTrue(r['eligibleForReleaseReview']);self.assertFalse(r['productionReady']);self.assertFalse(r['cncfCertified'])
    def test_no_evidence_is_blocked(self):
        self.save();r=self.check();self.assertFalse(r['eligibleForReleaseReview']);self.assertEqual(len(r['blockers']),14)
    def test_artifact_tamper(self):
        self.save();self.artifact.write_bytes(b'changed')
        with self.assertRaisesRegex(Blocked,'DIGEST'):self.check()
    def test_signature_tamper_even_with_updated_envelope_hash(self):
        self.gate('ubuntu-e2e');self.save();p=self.bundle/'ubuntu-e2e.json'
        import json
        e=json.loads(p.read_bytes());e['statement']['sourceCommit']='f'*40;write_json(p,e)
        self.c['evidence']=[self.ref(p)];write_json(self.cp,self.c)
        with self.assertRaisesRegex(Blocked,'SIGNATURE'):self.check()
    def test_wrong_candidate_commit(self):
        self.gate('ubuntu-e2e');self.save();self.c['sourceCommit']='f'*40;write_json(self.cp,self.c)
        with self.assertRaisesRegex(Blocked,'IDENTITY_MISMATCH'):self.check()
    def test_fixtures_cannot_pass_real_gate(self):
        self.gate('ubuntu-e2e');self.statements['ubuntu-e2e']['environment']['kind']='fixtures';self.save()
        with self.assertRaisesRegex(Blocked,'REAL_OR_EXTERNAL'):self.check()
    def test_raw_evidence_change(self):
        self.gate('ubuntu-e2e');self.save();(self.bundle/'ubuntu-e2e.log').write_text('changed')
        with self.assertRaisesRegex(Blocked,'DIGEST'):self.check()
    def test_expired_key(self):
        self.gate('ubuntu-e2e');self.t['keys'][0]['validUntil']='2026-09-01T00:00:00Z';self.save()
        with self.assertRaisesRegex(Blocked,'NOT_CURRENTLY_VALID'):self.check()
    def test_stale_evidence(self):
        self.gate('ubuntu-e2e');self.statements['ubuntu-e2e']['startedAt']='2026-08-01T00:00:00Z';self.statements['ubuntu-e2e']['finishedAt']='2026-08-02T00:00:00Z';self.save()
        with self.assertRaisesRegex(Blocked,'STALE'):self.check()
    def test_wrong_role(self):
        self.gate('independent-security');self.save({'independent-security':'builder'})
        with self.assertRaisesRegex(Blocked,'NOT_AUTHORIZED'):self.check()
    def test_same_organization_is_not_independent(self):
        self.gate('independent-security');self.gate('supply-chain');self.t['keys'][1]['organization']='product-org';self.save()
        with self.assertRaisesRegex(Blocked,'TRUST_SEPARATION'):self.check()
    def test_untrusted_key_in_bundle(self):
        self.save();p=self.bundle/'trust.json';p.write_bytes(self.trustpath.read_bytes())
        with self.assertRaisesRegex(Blocked,'OUTSIDE'):verify(self.cp,p,digest_file(p),self.now)
    def test_high_vulnerability_blocks_even_if_signed(self):
        self.gate('supply-chain');self.statements['supply-chain']['documents']['vulnerabilities']=self.document('trivy.json',{'SchemaVersion':2,'Results':[{'Target':'x','Vulnerabilities':[{'Severity':'HIGH'}]}]});self.save()
        with self.assertRaisesRegex(Blocked,'VULNERABILITY'):self.check()
    def test_provenance_wrong_builder(self):
        self.gate('supply-chain');self.save();self.c['builderId']='changed-builder';write_json(self.cp,self.c)
        with self.assertRaisesRegex(Blocked,'BUILDER'):self.check()
    def test_synthetic_acceptance_link_not_authority(self):
        self.gate('cncf-acceptance');self.statements['cncf-acceptance']['decisionURL']='https://example.test/approved';self.save()
        with self.assertRaisesRegex(Blocked,'OFFICIAL_ACCEPTANCE'):self.check()
    def test_duplicate_gate(self):
        self.gate('ubuntu-e2e');self.save();self.c['evidence']*=2;write_json(self.cp,self.c)
        with self.assertRaisesRegex(Blocked,'DUPLICATE'):self.check()
    def test_symlink_refused(self):
        self.save();self.artifact.unlink();self.artifact.symlink_to('/etc/hostname')
        with self.assertRaisesRegex(Blocked,'SYMLINK'):self.check()
    def test_trust_hash_mismatch(self):
        self.save()
        with self.assertRaisesRegex(Blocked,'TRUST_POLICY_HASH'):verify(self.cp,self.trustpath,'0'*64,self.now)

if __name__=='__main__':unittest.main()
