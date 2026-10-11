#!/usr/bin/env python3
"""Authenticate a real target .deb with the actual previous installed verifier.

Local process/crypto/package check, not dpkg installation or host qualification.
The random test key is ephemeral; no production signature is issued or exported.
"""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, subprocess, tempfile


def checked(args, **kwargs):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False, timeout=60, **kwargs)
    if result.returncode:
        # Do not disclose arbitrary external stderr, keys or protected file data.
        raise RuntimeError('PACKAGE_CHECK_COMMAND_FAILED:' + pathlib.Path(args[0]).name)
    return result.stdout


def exercise(previous, package):
    previous = pathlib.Path(previous).resolve(strict=True)
    package = pathlib.Path(package).resolve(strict=True)
    if checked([str(previous), 'version']).decode().splitlines()[0] != 'Werftkern 0.2.0-dev.3':
        raise RuntimeError('ACTUAL_PREVIOUS_VERSION_REQUIRED')
    if checked(['dpkg-deb', '-f', str(package), 'Package']).strip() != b'werftkern':
        raise RuntimeError('ACTUAL_WERFTKERN_PACKAGE_REQUIRED')
    if checked(['dpkg-deb', '-f', str(package), 'Version']).strip() != b'0.2.0~dev4':
        raise RuntimeError('TARGET_PACKAGE_VERSION_REQUIRED')
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    manifest = dict(format='werftkern-release/v1', version='0.2.0-dev.4',
                    packageVersion='0.2.0~dev4', packageSha256=digest,
                    stateSchema=2, sources=['0.2.0~dev3'], architecture='amd64')
    with tempfile.TemporaryDirectory(prefix='werft-signature-lab-') as temporary:
        base = pathlib.Path(temporary)
        key, pub, spec, sig = [base / n for n in ('private.pem', 'public.pem', 'release.json', 'release.sig')]
        checked(['openssl', 'genpkey', '-algorithm', 'ED25519', '-out', str(key)])
        os.chmod(key, 0o600)
        checked(['openssl', 'pkey', '-in', str(key), '-pubout', '-out', str(pub)])
        spec.write_bytes((json.dumps(manifest, sort_keys=True) + '\n').encode())
        checked(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', str(key),
                 '-in', str(spec), '-out', str(sig)])
        args = [str(previous), 'release', 'verify', '--package', str(package),
                '--manifest', str(spec), '--signature', str(sig), '--public-key', str(pub)]
        result = json.loads(checked(args))
        if result != manifest:
            raise RuntimeError('PREDECESSOR_VERIFICATION_RESULT_MISMATCH')
        changed = bytearray(sig.read_bytes()); changed[0] ^= 1; sig.write_bytes(changed)
        invalid = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 check=False, timeout=60)
        if invalid.returncode == 0:
            raise RuntimeError('TAMPERED_SIGNATURE_ACCEPTED')
    return {'status': 'passed', 'checks': ['real-deb-identity', 'actual-dev3-verifies-dev4',
             'mutated-signature-rejected'], 'packageSha256': digest,
             'previousBinarySha256': hashlib.sha256(previous.read_bytes()).hexdigest(),
             'temporaryKeyFilesRemoved': True, 'productionSigned': False,
             'hostInstallationTested': False, 'scope': 'actual OpenSSL, previous executable and package bytes; no dpkg install'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous-binary', required=True)
    parser.add_argument('--package', required=True)
    parser.add_argument('--evidence', required=True)
    args = parser.parse_args()
    result = exercise(args.previous_binary, args.package)
    pathlib.Path(args.evidence).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
