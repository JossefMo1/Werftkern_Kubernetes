# Governance

Initial model: maintainer-led experimental project. The repository owner appoints maintainers
using GitHub permissions; this document grants no account access and names no unconfirmed team.

API/architecture/security changes need a written decision with alternatives, migration impact,
negative tests and rollback limits. Breaking changes remain possible during alpha but must be
announced and tested. Do not silently change persisted state or reuse identities.

Source merges and production releases are different decisions. The owner must configure branch
protection, required reviews/checks and a protected release environment in GitHub. Files in this
repository cannot enforce those repository settings by themselves. A public alpha is not GA.

Security concerns use SECURITY.md. Contributions are reviewed on technical substance. Be respectful;
no harassment, disclosure of personal data or publication of secrets. Moderation is exercised by
appointed repository maintainers, not an unstaffed or fictitious committee.
