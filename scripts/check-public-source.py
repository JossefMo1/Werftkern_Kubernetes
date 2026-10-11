#!/usr/bin/env python3
"""Bounded publication lint, not a substitute for a dedicated secret/IP review.
Inspects the exact exported working-tree files. Excludes build outputs/history;
public ZIP generation uses the same exclusions. Never prints matched secrets.
"""
from pathlib import Path
import argparse, json, re, subprocess
SKIP = {'.git','build','dist','evidence','__pycache__','.pytest_cache'}
PATTERNS = {
 'private-key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----[\r\n]'),
 'github-token':re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
 'aws-key':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
 'credential-url':re.compile(rb'https?://[^\s/]+:[^\s/@]+@'),
}
def files(root):
 for p in sorted(root.rglob('*')):
  if any(x in SKIP for x in p.relative_to(root).parts): continue
  if p.is_file() or p.is_symlink(): yield p

def scan(root):
 issues=[];count=0
 for p in files(root):
  name=p.relative_to(root).as_posix();count+=1
  if p.is_symlink():issues.append({'path':name,'reason':'symlink-not-allowed'});continue
  if p.stat().st_size>2_000_000:issues.append({'path':name,'reason':'unexpected-large-source-file'});continue
  if name.endswith(('.key','.pem','.join.json','.deb','.zip')):issues.append({'path':name,'reason':'sensitive-or-generated-extension'})
  b=p.read_bytes()
  if b'\x00' in b:issues.append({'path':name,'reason':'binary-in-source-tree'})
  for label,pattern in PATTERNS.items():
   if pattern.search(b):issues.append({'path':name,'reason':label})
 for required in ['LICENSE','NOTICE.md','SECURITY.md','CONTRIBUTING.md','README.md','docs/STATUS.md']:
  if not (root/required).is_file():issues.append({'path':required,'reason':'required-file-missing'})
 return {'status':'failed' if issues else 'passed','filesScanned':count,'findings':issues,'scope':'working-tree text lint, not independent security or ownership clearance'}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=parser.parse_args()
 report=scan(a.root.resolve());print(json.dumps(report,indent=2));raise SystemExit(1 if report['findings'] else 0)
