# Third-party notices

The supplied laboratory executable and demo image statically include Go's runtime
and standard library. Their copyright/license text is preserved in
`third_party/go.LICENSE`, copied into Debian package documentation and the demo image.
This does not relicense Go under Apache-2.0.

No external Go modules are vendored. Docker Engine, etcd and Ubuntu packages are
installed separately from operator-controlled package sources and retain their
respective licenses. The current source snapshot is not an independent license audit.
Design provenance is recorded in NOTICE.md.

The new database integration invokes PostgreSQL, Patroni, pgBackRest and OpenSSL as
separately installed system tools. Their source/binaries are not included in this
repository or the laboratory Debian package; they retain their own licenses.
The integration's settings were checked against their upstream documentation.
No upstream dependency is relabeled as an original Werftkern database/consensus engine.
