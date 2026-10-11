#!/usr/bin/env python3
"""Fail-closed, heuristic audit of all reachable Git blobs before a PUBLIC release.

Does not prove absence of secrets, clear copyright, or assess dependencies.
Reports only object IDs, paths and categories; never secret values.
"""
import argparse
import json
import re
import subprocess
import sys

MAX_BLOB = 2_000_000
PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
    "github-token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    "aws-access-key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "gitlab-token": re.compile(rb"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    "stripe-live-secret": re.compile(rb"\bsk_live_[A-Za-z0-9]{20,}\b"),
    "resend-api-key": re.compile(rb"\bre_[A-Za-z0-9]{30,}\b"),
    "credential-url": re.compile(rb"https?://[^\s/:@]+:[^\s/@]+@"),
}
SENSITIVE_NAMES = {".env", ".env.local", ".env.production", ".env.staging",
                   "id_rsa", "id_ed25519", "credentials.json", ".npmrc", ".pypirc"}
SENSITIVE_SUFFIXES = (".key", ".p12", ".pfx", ".tfstate", ".tfstate.backup",
                      ".kubeconfig", ".pem", ".join.json", ".kit.json")


def git(*args):
    p = subprocess.run(["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False)
    if p.returncode:
        raise RuntimeError("git invocation failed; repository must be readable")
    return p.stdout


def sensitive_path(path):
    basename = path.rsplit("/", 1)[-1].lower()
    return basename in SENSITIVE_NAMES or basename.endswith(SENSITIVE_SUFFIXES)


def scan(require_noreply=False):
    findings = []
    objects = git("rev-list", "--objects", "--all").decode("utf-8", "replace").splitlines()
    if not objects:
        raise RuntimeError("no Git history available to inspect")
    seen = set()
    checked = 0
    for item in objects:
        oid, _, path = item.partition(" ")
        if not re.fullmatch(r"[0-9a-f]{40,64}", oid):
            raise RuntimeError("invalid Git object ID")
        if git("cat-file", "-t", oid).strip() != b"blob":
            continue
        if sensitive_path(path):
            findings.append({"object": oid[:12], "path": path, "reason": "sensitive-filename"})
        if oid in seen:
            continue
        seen.add(oid)
        checked += 1
        size = int(git("cat-file", "-s", oid).strip())
        if size > MAX_BLOB:
            findings.append({"object": oid[:12], "path": path, "reason": "blob-too-large-to-scan"})
            continue
        content = git("cat-file", "blob", oid)
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append({"object": oid[:12], "path": path, "reason": label})
    if require_noreply:
        emails = git("log", "--all", "--format=%ae%n%ce").decode("utf-8", "replace").splitlines()
        for index, email in enumerate(emails):
            if email and not email.lower().endswith("@users.noreply.github.com"):
                findings.append({"object": "commit-metadata", "path": "email-" + str(index),
                                 "reason": "non-noreply-email"})
    return {"status": "BLOCKED" if findings else "PASS", "blobsScanned": checked,
            "findings": findings,
            "limitations": "Heuristic historical blob scan, not a complete secrets/IP/security audit"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-noreply", action="store_true",
                        help="Extra one-time publication check; may reject consenting contributors' emails")
    args = parser.parse_args()
    try:
        report = scan(args.require_noreply)
    except (OSError, RuntimeError, ValueError) as exc:
        report = {"status": "BLOCKED", "findings": [{"reason": "audit-incomplete"}]}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
