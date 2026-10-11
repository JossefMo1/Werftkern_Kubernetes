#!/usr/bin/env python3
"""Fail-closed release evidence consistency check. Does NOT authenticate evidence
producers/reviewers. Run only after independent gates in a protected workflow;
editing JSON to say 'passed' cannot establish production readiness.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, re
REQUIRED = ('unit-race','static-analysis','source-audit','supported-toolchain-security',
 'ubuntu-install-e2e','real-engine-etcd','multi-node-network','ha-partition',
 'restore-new-host','upgrade-rollback','load-soak','independent-security','maintainer-approval')
def validate(m,root,commit):
 problems=[]
 if m.get('schema')!='clusterpilot/qualification/v1':problems.append('SCHEMA_INVALID')
 if not re.fullmatch('[0-9a-f]{40}',commit) or m.get('sourceCommit')!=commit:problems.append('SOURCE_COMMIT_MISMATCH')
 if m.get('scope')!='full-masterplan':problems.append('FULL_SCOPE_REQUIRED')
 features=m.get('features',{})
 if set(features)!=set(f'K20-{i:03d}' for i in range(1,53)):problems.append('FEATURE_INVENTORY_INCOMPLETE')
 for key,item in features.items():
  if not isinstance(item,dict) or item.get('status')!='implemented-and-qualified':problems.append('FEATURE_NOT_QUALIFIED:'+key)
 gates=m.get('gates',{})
 for name in REQUIRED:
  g=gates.get(name,{})
  if not isinstance(g,dict) or g.get('status')!='passed':problems.append('GATE_NOT_PASSED:'+name);continue
  if g.get('sourceCommit')!=commit:problems.append('GATE_COMMIT_MISMATCH:'+name)
  try:
   dt=datetime.datetime.fromisoformat(g['executedAt'].replace('Z','+00:00'))
   age=datetime.datetime.now(datetime.timezone.utc)-dt
   if age<datetime.timedelta(minutes=-5) or age>datetime.timedelta(days=30):raise ValueError()
  except (KeyError,ValueError,TypeError):problems.append('EVIDENCE_TIME_INVALID:'+name)
  path=g.get('evidence','');sha=g.get('sha256','')
  if not isinstance(path,str) or not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):problems.append('EVIDENCE_REFERENCE_INVALID:'+name);continue
  rel=Path(path)
  if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0]!='evidence':problems.append('EVIDENCE_PATH_INVALID:'+name);continue
  p=root/rel
  if any((root/Path(*rel.parts[:i])).is_symlink() for i in range(1,len(rel.parts)+1)) or not p.is_file():problems.append('EVIDENCE_MISSING_OR_SYMLINK:'+name);continue
  if p.stat().st_size>50_000_000:problems.append('EVIDENCE_TOO_LARGE:'+name);continue
  if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:problems.append('EVIDENCE_DIGEST_MISMATCH:'+name)
 return problems
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,default=Path('release/qualification.json'));p.add_argument('--commit',required=True);p.add_argument('--root',type=Path,default=Path('.'));a=p.parse_args()
 try:
  if a.manifest.stat().st_size>2_000_000:raise ValueError('manifest too large')
  m=json.loads(a.manifest.read_text());problems=validate(m,a.root.resolve(),a.commit)
 except (OSError,ValueError,TypeError,AttributeError) as e:problems=['MANIFEST_INVALID']
 print(json.dumps({'productionReady':False,'evidenceConsistent':not problems,'status':'BLOCKED' if problems else 'EVIDENCE_CONSISTENCY_PASSED','blockers':problems,'notice':'Content consistency only. Independent producer authentication and protected approval are required.'},indent=2))
 raise SystemExit(1 if problems else 0)
