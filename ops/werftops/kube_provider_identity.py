"""Bind destructive recovery to the same provider credential across restarts.

A 404 under a DIFFERENT project/token must never be accepted as fencing proof.
Only a domain-separated digest of a high-entropy credential is stored in private
journals. Raw credentials are never written or exposed by these helpers.
"""
from .common import Blocked, sha


def identity(machines):
    value=getattr(machines.api,'credential_fingerprint',None)
    if not isinstance(value,str):raise Blocked('PROVIDER_CREDENTIAL_IDENTITY_REQUIRED')
    sha(value)
    return value


def assert_identity(machines,journal):
    if journal.get('providerCredential')!=identity(machines):
        raise Blocked('PROVIDER_CREDENTIAL_CHANGED_OR_UNBOUND_REQUIRES_REVIEW')
