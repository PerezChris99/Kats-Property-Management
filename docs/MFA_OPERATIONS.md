# Staff and owner multi-factor authentication

Kats now supports 6-digit TOTP authenticator codes (RFC 6238) for each
account. User-owned secrets are encrypted using a dedicated Fernet key
(MFA_ENCRYPTION_KEY) before storage. Password confirmation is required to
begin setup, an authenticator code completes enrollment, and session
revocation follows all MFA changes. Login with MFA enabled requires a
fresh unused TOTP step; concurrent replay is rejected.

## Launch acceptance

1. Provision and back up the long-term encryption key in a managed secrets
   system. Generate with:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   Never publish it or paste it into source code.
2. Make all OWNER, SUPER_ADMIN, MANAGER and ACCOUNTANT accounts enroll
   before receiving permission to process live money or personal records.
3. Verify the actual Login and Account Security UI using real authenticator
   apps, time skew, lost-phone and support procedures.
4. Establish a two-person, strongly authenticated recovery process that
   cannot be used merely by a privileged staff account to bypass MFA.
5. Verify MFA audit records and emergency key rotation/recovery procedures.
6. If the MFA encryption key is unavailable, enabled MFA logins fail closed;
   restoring the same managed key is essential for continued operation.

**Limitations:** MFA enrollment is currently opt-in; an operator can not
assert that all administrative accounts have enrolled merely because the
feature exists. Lost-device recovery requires authorized business support
and an approved documented procedure, not automatic insecure bypass.
