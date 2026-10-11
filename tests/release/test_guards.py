import importlib.util, pathlib, tempfile, unittest, json, hashlib, datetime
ROOT=pathlib.Path(__file__).resolve().parents[2]
def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
release=load('check-release');public=load('check-public-source')
class Guards(unittest.TestCase):
 def manifest(self,root):
  (root/'evidence').mkdir();b=b'independent test fixture, NOT production evidence';(root/'evidence/a.txt').write_bytes(b);sha='a'*40
  m={'schema':'clusterpilot/qualification/v1','sourceCommit':sha,'scope':'full-masterplan','features':{f'K20-{i:03d}':{'status':'implemented-and-qualified'} for i in range(1,53)},'gates':{g:{'status':'passed','sourceCommit':sha,'executedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evidence':'evidence/a.txt','sha256':hashlib.sha256(b).hexdigest()} for g in release.REQUIRED}}
  return m,sha
 def test_actual_release_is_blocked(self):
  m=json.loads((ROOT/'release/qualification.json').read_text());self.assertTrue(release.validate(m,ROOT,'a'*40))
 def test_valid_mechanical_fixture(self):
  with tempfile.TemporaryDirectory() as d:
   m,s=self.manifest(pathlib.Path(d));self.assertEqual(release.validate(m,pathlib.Path(d),s),[])
 def test_missing_gate(self):
  with tempfile.TemporaryDirectory() as d:
   m,s=self.manifest(pathlib.Path(d));del m['gates']['real-engine-etcd'];self.assertIn('GATE_NOT_PASSED:real-engine-etcd',release.validate(m,pathlib.Path(d),s))
 def test_mismatched_commit_or_contents(self):
  with tempfile.TemporaryDirectory() as d:
   r=pathlib.Path(d);m,s=self.manifest(r);self.assertTrue(release.validate(m,r,'b'*40));(r/'evidence/a.txt').write_text('changed');self.assertTrue(release.validate(m,r,s))
 def test_traversal_and_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   r=pathlib.Path(d);m,s=self.manifest(r);m['gates']['unit-race']['evidence']='../outside';self.assertTrue(release.validate(m,r,s));m['gates']['unit-race']['evidence']='evidence/link';(r/'evidence/link').symlink_to(r/'evidence/a.txt');self.assertTrue(release.validate(m,r,s))
 def test_partial_feature_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   r=pathlib.Path(d);m,s=self.manifest(r);m['features']['K20-011']['status']='partial';self.assertIn('FEATURE_NOT_QUALIFIED:K20-011',release.validate(m,r,s))
 def test_public_lint_detects_key_without_disclosing_it(self):
  with tempfile.TemporaryDirectory() as d:
   r=pathlib.Path(d);value='-----BEGIN '+'PRIVATE KEY-----\nSENSITIVE';(r/'oops.txt').write_text(value);o=public.scan(r);self.assertTrue(o['findings']);self.assertNotIn('SENSITIVE',json.dumps(o))
if __name__=='__main__':unittest.main()
