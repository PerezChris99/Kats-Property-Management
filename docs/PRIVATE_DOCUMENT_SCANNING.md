# Private S3 document scanning and quarantine (code-only readiness)

Kats must never allow arbitrary files to become downloadable merely because
an object key exists. The application now verifies the exact uploaded length,
MIME signature, and immutable S3 version, then streams the bounded (≤8 MB)
object through a private ClamAV INSTREAM scanner. Only a CLEAN verdict sets
UPLOADED. Infected or nonmatching files become QUARANTINED. An unavailable
scanner is a fail-closed 503: the upload remains unapproved.

**Infrastructure required before enabling documents:**

- A private, version-enabled S3-compatible bucket. The provider must return
  `VersionId` through HeadObject/GetObject and support presigning that version.
- An independently operated, patched ClamAV service on an isolated private
  network (CLAMAV_HOST and CLAMAV_PORT). Never publish the scanner on the internet.
- Storage CORS and credentials restricted to only necessary object operations;
  private ACL, retention, access logs without sensitive links, and alerts.
- Acceptable scanning latency and real provider acceptance tests.
- Previously uploaded unscanned documents have no version or scan timestamp.
  They are intentionally **not downloadable**; reupload and verify them.

The present implementation scans synchronously during upload completion,
with a strict 8 MB cap. An asynchronous scanner would need a separately
scoped database role compatible with FORCE RLS and a durable job queue; do not
introduce an unscoped privileged worker. Consider file CDR, additional
content validation, and abuse/DoS testing before high-risk document use.

The scanner does not establish identity or legal authenticity of tenancy
agreements, nor does it constitute electronic-signature approval.
