"""Verify signed, exact-candidate evidence using separately administered trust.

This authenticates approved signers and material bytes. It cannot establish that
an approved signer told the truth, independently certify CNCF acceptance, or
replace independent review. It NEVER automatically declares production readiness.
Custom evidence format, not a claim of SLSA level or a Sigstore bundle.
"""
from __future__ import annotations
import base64
import datetime as dt
import hashlib
import pathlib
import re
import tempfile
from .common import Blocked, canonical, digest_file, read_json, run, sha
from .kube_spec import fields, name

GATES={
 'ubuntu-e2e':('qualifier','real-vm'),
 'ha-chaos':('qualifier','real-vm'),
 'cloud-lifecycle':('qualifier','real-cloud'),
 'controller-stateful-recovery':('qualifier','real-cloud'),
 'pv-database-restore':('qualifier','real-vm'),
 'sso-rbac':('qualifier','real-vm'),
 'acme':('qualifier','real-acme'),
 'sonobuoy-conformance':('qualifier','real-vm'),
 'upgrade-rollback':('qualifier','real-vm'),
 'load-soak':('qualifier','real-vm'),
 'supply-chain':('builder','protected-build'),
 'independent-security':('independent-reviewer','independent-assessment'),
 'cncf-acceptance':('certification-verifier','external-decision'),
 'release-approval':('release-manager','release-review'),
}


def instant(value):
    if not isinstance(value,str):raise Blocked('EVIDENCE_TIMESTAMP_REQUIRED')
    try:
        parsed=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.utcoffset() is None:raise ValueError()
        return parsed.astimezone(dt.timezone.utc)
    except ValueError:raise Blocked('EVIDENCE_TIMESTAMP_INVALID') from None


def bounded_file(root,reference,limit=100*1024*1024):
    fields(reference,('path','sha256'));sha(reference['sha256'])
    relative=pathlib.Path(reference['path'])
    if relative.is_absolute() or not relative.parts or any(x in ('.','..') for x in relative.parts):
        raise Blocked('EVIDENCE_PATH_INVALID')
    path=root/relative
    if any((root/pathlib.Path(*relative.parts[:i])).is_symlink() for i in range(1,len(relative.parts)+1)):
        raise Blocked('EVIDENCE_SYMLINK_REJECTED')
    if not path.is_file() or path.stat().st_size>limit:raise Blocked('EVIDENCE_FILE_MISSING_OR_TOO_LARGE')
    if digest_file(path)!=reference['sha256']:raise Blocked('EVIDENCE_DIGEST_MISMATCH')
    return path


def verify_signature(statement,signature,key):
    try:raw=base64.b64decode(signature,validate=True)
    except (ValueError,TypeError):raise Blocked('EVIDENCE_SIGNATURE_ENCODING_INVALID') from None
    if len(raw)!=64:raise Blocked('ED25519_SIGNATURE_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='werft-verify-') as tmp:
        root=pathlib.Path(tmp);payload=root/'payload';sig=root/'signature'
        payload.write_bytes(canonical(statement));sig.write_bytes(raw)
        try:
            details=run(['/usr/bin/openssl','pkey','-pubin','-in',str(key),'-text','-noout'])
            if b'ED25519' not in details:raise Blocked('ED25519_PUBLIC_KEY_REQUIRED')
            run(['/usr/bin/openssl','pkeyutl','-verify','-pubin','-inkey',str(key),'-rawin',
                 '-in',str(payload),'-sigfile',str(sig)],timeout=20)
        except Blocked:raise Blocked('EVIDENCE_SIGNATURE_INVALID') from None


def validate_supply_documents(root, documents, candidate):
    fields(documents,('sbom','vulnerabilities','provenance'))
    sbom=read_json(bounded_file(root,documents['sbom']))
    if sbom.get('bomFormat')!='CycloneDX' or not isinstance(sbom.get('components'),list) or not sbom['components']:
        raise Blocked('NONEMPTY_CYCLONEDX_SBOM_REQUIRED')
    # Do not invent zero findings for a missing scan or silently ignore malformed records.
    scan=read_json(bounded_file(root,documents['vulnerabilities']))
    if scan.get('SchemaVersion')!=2 or not isinstance(scan.get('Results'),list) or not scan['Results']:
        raise Blocked('TRIVY_RESULT_REQUIRED')
    for result in scan['Results']:
        if not isinstance(result,dict) or not isinstance(result.get('Target'),str):raise Blocked('VULNERABILITY_RESULT_INVALID')
        findings=result.get('Vulnerabilities',[]) or []
        if not isinstance(findings,list):raise Blocked('VULNERABILITY_RESULT_INVALID')
        for finding in findings:
            if not isinstance(finding,dict) or finding.get('Severity') not in ('LOW','MEDIUM','HIGH','CRITICAL','UNKNOWN'):
                raise Blocked('VULNERABILITY_SEVERITY_INVALID')
            if finding['Severity'] in ('HIGH','CRITICAL','UNKNOWN'):raise Blocked('UNRESOLVED_VULNERABILITY_BLOCKS_RELEASE')
    provenance=read_json(bounded_file(root,documents['provenance']))
    if provenance.get('_type')!='https://in-toto.io/Statement/v1' or provenance.get('predicateType')!='https://slsa.dev/provenance/v1':
        raise Blocked('IN_TOTO_SLSA_PROVENANCE_REQUIRED')
    if provenance.get('subject')!=[{'name':candidate['artifact']['path'],'digest':{'sha256':candidate['artifact']['sha256']}}]:
        raise Blocked('PROVENANCE_ARTIFACT_MISMATCH')
    predicate=provenance.get('predicate',{});build=predicate.get('buildDefinition',{})
    if predicate.get('runDetails',{}).get('builder',{}).get('id')!=candidate['builderId']:
        raise Blocked('PROVENANCE_BUILDER_MISMATCH')
    materials=build.get('resolvedDependencies',[])
    if not any(m.get('uri')==candidate['sourceRepository'] and m.get('digest',{}).get('gitCommit')==candidate['sourceCommit'] for m in materials):
        raise Blocked('PROVENANCE_SOURCE_MISMATCH')
    if not any(m.get('digest',{}).get('sha256')==candidate['assetsSHA256'] for m in materials):
        raise Blocked('PROVENANCE_ASSET_LOCK_MISSING')


def verify(candidate_path,trust_path,trust_sha256,now=None):
    candidate_path=pathlib.Path(candidate_path).absolute();root=candidate_path.parent.resolve()
    trust_path=pathlib.Path(trust_path).absolute();sha(trust_sha256)
    # An evidence package may not choose the keys that approve itself.
    if trust_path.is_symlink() or trust_path.resolve().is_relative_to(root):raise Blocked('TRUST_MUST_BE_CONFIGURED_OUTSIDE_CANDIDATE')
    if digest_file(trust_path)!=trust_sha256:raise Blocked('TRUST_POLICY_HASH_MISMATCH')
    c=read_json(candidate_path);t=read_json(trust_path)
    fields(c,('format','sourceCommit','sourceRepository','builderId','assetsSHA256','artifact','evidence'))
    if c['format']!='werftkern-release-candidate/v1' or not re.fullmatch(r'[a-f0-9]{40}',c['sourceCommit']):raise Blocked('CANDIDATE_INVALID')
    sha(c['assetsSHA256']);bounded_file(root,c['artifact'],2*1024**3)
    if not isinstance(c['sourceRepository'],str) or not c['sourceRepository'].startswith('https://github.com/') or not isinstance(c['builderId'],str) or not c['builderId']:
        raise Blocked('BUILD_IDENTITY_REQUIRED')
    fields(t,('format','keys','maxAgeDays'))
    if t['format']!='werftkern-evidence-trust/v1' or type(t['maxAgeDays']) is not int or not 1<=t['maxAgeDays']<=30:
        raise Blocked('TRUST_POLICY_INVALID')
    keys={}
    for k in t['keys']:
        fields(k,('id','publicKey','roles','organization','validFrom','validUntil'));name(k['id'])
        if k['id'] in keys or not isinstance(k['roles'],list) or not k['roles'] or not k['organization']:raise Blocked('TRUST_KEY_INVALID')
        keys[k['id']]=k
    now=now or dt.datetime.now(dt.timezone.utc)
    if not isinstance(c['evidence'],list) or len(c['evidence'])>30:raise Blocked('EVIDENCE_INVENTORY_INVALID')
    passed={};blockers=[];organizations={};physical_keys={}
    for ref in c['evidence']:
        envelope=read_json(bounded_file(root,ref));fields(envelope,('statement','signature','keyId'))
        s=envelope['statement'];fields(s,('format','gate','sourceCommit','artifactSHA256','assetsSHA256','status',
                                         'startedAt','finishedAt','environment','evidence'),('documents','decisionURL'))
        gate=s['gate']
        if gate not in GATES or gate in passed:raise Blocked('UNKNOWN_OR_DUPLICATE_EVIDENCE_GATE')
        k=keys.get(envelope['keyId'])
        if not k or GATES[gate][0] not in k['roles']:raise Blocked('EVIDENCE_SIGNER_NOT_AUTHORIZED')
        key=bounded_file(trust_path.parent,k['publicKey'],16384)
        der=run(['/usr/bin/openssl','pkey','-pubin','-in',str(key),'-outform','DER'])
        physical_keys[gate]=hashlib.sha256(der).hexdigest()
        verify_signature(s,envelope['signature'],key)
        if (s['format']!='werftkern-gate-evidence/v1' or s['sourceCommit']!=c['sourceCommit'] or
            s['artifactSHA256']!=c['artifact']['sha256'] or s['assetsSHA256']!=c['assetsSHA256']):
            raise Blocked('EVIDENCE_CANDIDATE_IDENTITY_MISMATCH')
        start,end=instant(s['startedAt']),instant(s['finishedAt'])
        if end<start or end>now+dt.timedelta(minutes=5) or now-end>dt.timedelta(days=t['maxAgeDays']):raise Blocked('EVIDENCE_STALE_OR_INVALID_TIME')
        if start<instant(k['validFrom']) or now<instant(k['validFrom']) or now>instant(k['validUntil']) or end>instant(k['validUntil']):raise Blocked('SIGNER_NOT_CURRENTLY_VALID')
        if s['status']!='passed':raise Blocked('EVIDENCE_GATE_NOT_PASSED')
        fields(s['environment'],('kind','identities'))
        if s['environment']['kind']!=GATES[gate][1] or not isinstance(s['environment']['identities'],list) or not s['environment']['identities']:
            raise Blocked('REAL_OR_EXTERNAL_EVIDENCE_REQUIRED')
        if not isinstance(s['evidence'],list) or not s['evidence']:raise Blocked('RAW_EVIDENCE_REQUIRED')
        for material in s['evidence']:bounded_file(root,material)
        if gate=='supply-chain':validate_supply_documents(root,s.get('documents',{}),c)
        if gate=='cncf-acceptance':
            if not re.fullmatch(r'https://github.com/cncf/k8s-conformance/pull/[1-9][0-9]*',s.get('decisionURL','')):
                raise Blocked('OFFICIAL_ACCEPTANCE_REFERENCE_REQUIRED')
        organizations[gate]=k['organization'];passed[gate]=envelope['keyId']
    if 'supply-chain' in passed and 'independent-security' in passed:
        if organizations['supply-chain']==organizations['independent-security'] or physical_keys['supply-chain']==physical_keys['independent-security']:
            raise Blocked('INDEPENDENT_REVIEW_TRUST_SEPARATION_REQUIRED')
    blockers.extend('MISSING_SIGNED_GATE:'+g for g in sorted(set(GATES)-set(passed)))
    return {'status':'BLOCKED' if blockers else 'SIGNED_EVIDENCE_VERIFIED', 'eligibleForReleaseReview':not blockers,
            'productionReady':False,'cncfCertified':False,'verifiedGates':sorted(passed),'blockers':blockers,
            'notice':'Authenticates configured signers and exact files. Does not prove signer honesty, real independence, CNCF approval or product safety.'}
