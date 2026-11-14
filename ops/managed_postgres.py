"""Managed PostgreSQL encrypted backups and staging-only restores.

Unlike the legacy Docker db helper, this operates on EXTERNAL PostgreSQL.
Never passes secrets in command arguments or writes an unencrypted permanent
dump. No production restore mode exists. A provider snapshot is not a backup
until an offsite encrypted archive and a witnessed restore are verified.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote, urlsplit

SCHEME = ("postgresql", "postgres", "postgresql+psycopg")
STAGING_NAME = re.compile(r"^[a-z][a-z0-9_]{0,50}_(?:restore|staging)$")
DEFAULT_TABLES = ("users", "properties", "tenants", "leases", "invoices", "payments", "audit_logs")


class BackupError(RuntimeError):
    pass


def pg_environment(dsn: str, *, require_tls: bool = True) -> tuple[dict, tuple[str, str, str]]:
    """Convert a SQLAlchemy URI to libpq environment, not CLI credentials."""
    if not isinstance(dsn, str) or len(dsn) > 4096:
        raise BackupError("A bounded PostgreSQL DATABASE_URL is required")
    try:
        parsed = urlsplit(dsn)
        pairs = parse_qs(parsed.query, strict_parsing=True)
        hostname = parsed.hostname
        port = parsed.port or 5432
    except ValueError as exc:
        raise BackupError("Invalid PostgreSQL connection details") from exc
    if (parsed.scheme not in SCHEME or not hostname or not parsed.username
            or not parsed.password or not 1 <= port <= 65535
            or parsed.fragment or parsed.path.count("/") != 1
            or not parsed.path.lstrip("/") or parsed.username.startswith("-")):
        raise BackupError("PostgreSQL URL must contain host, user, password and database")
    if set(pairs) - {"sslmode", "sslrootcert"}:
        raise BackupError("Unexpected PostgreSQL URL option; only sslmode/sslrootcert are allowed")
    sslmode = pairs.get("sslmode", [""])[0]
    if require_tls and sslmode != "verify-full":
        raise BackupError("Managed PostgreSQL backup requires sslmode=verify-full")
    if not require_tls and sslmode not in ("verify-full", "require", "disable"):
        raise BackupError("Explicit sslmode is required")
    username = unquote(parsed.username)
    password = unquote(parsed.password)
    dbname = unquote(parsed.path[1:])
    if not all("\x00" not in value and "\n" not in value for value in (username, password, dbname, hostname)):
        raise BackupError("Invalid PostgreSQL connection characters")
    if "/" in dbname or not re.fullmatch(r"[A-Za-z0-9_\-]{1,63}", dbname):
        raise BackupError("Unexpected PostgreSQL database name")
    # Subprocess gets only these explicit PG* values, not arbitrary PGSERVICE/
    # PGOPTIONS/PGHOSTADDR inherited from an operator's shell.
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env.update(PGHOST=hostname, PGPORT=str(port), PGUSER=username,
               PGPASSWORD=password, PGDATABASE=dbname, PGSSLMODE=sslmode)
    cert = pairs.get("sslrootcert", [])
    if cert:
        if len(cert) != 1 or not cert[0]:
            raise BackupError("Invalid PostgreSQL CA setting")
        env["PGSSLROOTCERT"] = cert[0]
    return env, (hostname, str(port), dbname)


def ensure_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise BackupError("Missing required command: " + name)


def check(cmd: list[str], *, env: dict | None = None, output=None, timeout=900) -> None:
    try:
        subprocess.run(cmd, check=True, env=env, stdout=output or subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BackupError("Command failed: " + cmd[0] + " (inspect restricted operator logs)") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def verify_plain_dump(path: Path) -> None:
    ensure_binary("pg_restore")
    if not path.is_file() or path.stat().st_size < 1024:
        raise BackupError("Archive is missing or unexpectedly small")
    try:
        result = subprocess.run(["pg_restore", "--list", str(path)], check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=30, text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BackupError("PostgreSQL archive header or listing is invalid") from exc
    for table in DEFAULT_TABLES:
        if not re.search(r"\bTABLE\s+public\s+" + re.escape(table) + r"\s", result.stdout):
            raise BackupError("Backup is missing required business table " + table)


def archive_name(now=None) -> str:
    now = now or datetime.now(timezone.utc)
    return "kats-" + now.strftime("%Y%m%dT%H%M%SZ") + ".dump.age"


def backup(*, database_url: str, recipient: str, destination: Path, s3_uri: str = "") -> Path:
    env, _ = pg_environment(database_url)
    if not recipient or len(recipient) > 256 or "\n" in recipient:
        raise BackupError("An approved AGE_RECIPIENT is required")
    for command in ("pg_dump", "pg_restore", "age"):
        ensure_binary(command)
    if s3_uri:
        ensure_binary("aws")
        if not re.fullmatch(r"s3://[A-Za-z0-9._-]{3,63}/[A-Za-z0-9_./-]+/", s3_uri):
            raise BackupError("BACKUP_S3_URI must be an explicit s3://bucket/private-prefix/ path")
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = archive_name()
    output = destination / name
    if output.exists():
        raise BackupError("A backup already exists at the selected timestamp")
    with tempfile.TemporaryDirectory(prefix="kats-pg-backup-") as tmp:
        dump = Path(tmp) / "database.dump"
        encrypted = Path(tmp) / name
        check(["pg_dump", "--format=custom", "--no-owner", "--no-acl",
               "--lock-wait-timeout=10s", "--file=" + str(dump)], env=env)
        verify_plain_dump(dump)
        check(["age", "--recipient", recipient, "--output", str(encrypted), str(dump)])
        if encrypted.stat().st_size < 100:
            raise BackupError("Encrypted backup is empty")
        digest = sha256(encrypted)
        # Atomic on a single filesystem. Copy into a temporary target then replace.
        temporary = destination / ("." + name + ".tmp")
        if temporary.exists():
            raise BackupError("Stale temporary backup detected; inspect before continuing")
        try:
            shutil.copyfile(encrypted, temporary)
            os.chmod(temporary, 0o600)
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
        (destination / (name + ".sha256")).write_text(digest + "  " + name + "\n", encoding="ascii")
        if s3_uri:
            remote = s3_uri + name
            check(["aws", "s3", "cp", str(output), remote,
                   "--only-show-errors", "--metadata", "sha256=" + digest])
            try:
                answer = subprocess.run(
                    ["aws", "s3api", "head-object", "--bucket", s3_uri[5:].split("/", 1)[0],
                     "--key", s3_uri[5:].split("/", 1)[1] + name,
                     "--query", "Metadata.sha256", "--output", "text"],
                    check=True, capture_output=True, text=True, timeout=30
                ).stdout.strip()
            except (OSError, subprocess.SubprocessError) as exc:
                raise BackupError("Offsite archive upload could not be verified") from exc
            if answer != digest:
                raise BackupError("Offsite backup SHA-256 metadata does not match upload")
    print("[BACKUP] Encrypted managed PostgreSQL archive and SHA-256 created. "
          + ("Offsite object verified." if s3_uri else
             "NOT OFFSITE: upload the archive and record offsite evidence."),
          flush=True)
    return output


def decrypt_and_validate(archive: Path, identity: str, target_dir: Path) -> Path:
    ensure_binary("age")
    ensure_binary("pg_restore")
    if not identity or not Path(identity).is_file():
        raise BackupError("Valid AGE_IDENTITY file required to verify or restore")
    if not archive.is_file() or archive.suffix != ".age":
        raise BackupError("Explicit encrypted .age archive path required")
    checksum = archive.with_name(archive.name + ".sha256")
    if checksum.is_file():
        expected = checksum.read_text(encoding="ascii").split()[0]
        if not re.fullmatch(r"[a-f0-9]{64}", expected) or expected != sha256(archive):
            raise BackupError("Encrypted archive checksum mismatch")
    plain = target_dir / "verified.dump"
    check(["age", "--decrypt", "--identity", identity, "--output", str(plain), str(archive)])
    verify_plain_dump(plain)
    return plain


def restore_staging(*, archive: Path, identity: str, target_dsn: str, confirmation: str) -> None:
    if os.getenv("APP_ENV") not in ("staging", "development"):
        raise BackupError("Restore requires explicit staging/development APP_ENV")
    if confirmation != "RESTORE_ISOLATED_STAGING_ONLY":
        raise BackupError("Explicit --confirm RESTORE_ISOLATED_STAGING_ONLY is required")
    env, (_, _, name) = pg_environment(target_dsn)
    if not STAGING_NAME.fullmatch(name):
        raise BackupError("Refusing restore: target must be a dedicated *_staging or *_restore database")
    source_url = os.getenv("DATABASE_URL", "")
    if source_url:
        _, source = pg_environment(source_url)
        if source == (env["PGHOST"], env["PGPORT"], name):
            raise BackupError("Source/target match; production or primary data may never be restored over")
    with tempfile.TemporaryDirectory(prefix="kats-pg-restore-") as temp:
        dump = decrypt_and_validate(archive, identity, Path(temp))
        check(["pg_restore", "--clean", "--if-exists", "--no-owner",
               "--no-acl", "--single-transaction", "--exit-on-error",
               "--dbname=" + name, str(dump)], env=env)
    print("[STAGING RESTORE] Completed to explicitly named isolated staging database. "
          "Verify invoice totals, balances, RLS, migrations, and app startup.", flush=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="mode", required=True)
    start = command.add_parser("backup", help="Encrypted managed PostgreSQL backup")
    start.add_argument("--directory", default="backups", type=Path)
    verify = command.add_parser("verify", help="Read-only decrypt and validate archive format")
    verify.add_argument("--archive", type=Path, required=True)
    restore = command.add_parser("restore-staging", help="Destructive isolated staging restore only")
    restore.add_argument("--archive", type=Path, required=True)
    restore.add_argument("--confirm", required=True)
    args = parser.parse_args(argv)
    try:
        os.umask(0o077)
        if args.mode == "backup":
            backup(database_url=os.getenv("DATABASE_URL", ""),
                   recipient=os.getenv("AGE_RECIPIENT", ""),
                   destination=args.directory, s3_uri=os.getenv("BACKUP_S3_URI", ""))
        elif args.mode == "verify":
            with tempfile.TemporaryDirectory(prefix="kats-pg-verify-") as temp:
                decrypt_and_validate(args.archive, os.getenv("AGE_IDENTITY", ""), Path(temp))
            print("[PASS] Archive checksum, age decryption and core PostgreSQL tables verified.")
        else:
            restore_staging(archive=args.archive, identity=os.getenv("AGE_IDENTITY", ""),
                            target_dsn=os.getenv("RESTORE_DATABASE_URL", ""),
                            confirmation=args.confirm)
        return 0
    except BackupError as exc:
        print("[BLOCKED] " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
