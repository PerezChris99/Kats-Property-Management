"""Managed-PostgreSQL recovery regression tests: fail closed, no Docker db."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import os
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = spec_from_file_location("kats_managed_postgres", ROOT / "ops" / "managed_postgres.py")
pg = module_from_spec(spec)
spec.loader.exec_module(pg)


def dsn(db="kats", sslmode="verify-full"):
    return f"postgresql+psycopg://app_user:s3cret%21@db.internal.example:5432/{db}?sslmode={sslmode}"


def test_pg_dump_uses_environment_not_password_in_command(monkeypatch):
    env, identity = pg.pg_environment(dsn())
    assert identity == ("db.internal.example", "5432", "kats")
    assert env["PGUSER"] == "app_user" and env["PGPASSWORD"] == "s3cret!"
    assert env["PGSSLMODE"] == "verify-full"
    assert "s3cret!" not in " ".join(["pg_dump", "--format=custom", "--no-owner", "--no-acl"])
    monkeypatch.setenv("PGOPTIONS", "-c rogue_option=bad")
    assert "PGOPTIONS" not in pg.pg_environment(dsn())[0]


@pytest.mark.parametrize("invalid", [
    "", "sqlite:///real.db", "postgresql://app:pass@db/kats",
    "postgresql://app:pass@db/kats?sslmode=disable",
    "postgresql://app:pass@db/kats?sslmode=require",
    "postgresql://app:pass@db/kats?sslmode=verify-full&options=evil",
    "postgresql://app:pass@db/kats/other?sslmode=verify-full",
    "postgresql://app:pass@db:99999/kats?sslmode=verify-full",
])
def test_managed_postgres_never_uses_unsafe_or_invalid_connection(invalid):
    with pytest.raises(pg.BackupError):
        pg.pg_environment(invalid)


def test_staging_restore_will_not_touch_production(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(pg.BackupError, match="staging"):
        pg.restore_staging(archive=tmp_path/"archive.age", identity="id",
                           target_dsn=dsn("kats_restore"),
                           confirmation="RESTORE_ISOLATED_STAGING_ONLY")


def test_staging_restore_rejects_ordinary_business_database(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for database in ("kats", "kats_production", "postgres", "kats_test"):
        with pytest.raises(pg.BackupError, match="dedicated"):
            pg.restore_staging(archive=tmp_path/"archive.age", identity="id",
                               target_dsn=dsn(database),
                               confirmation="RESTORE_ISOLATED_STAGING_ONLY")


def test_staging_restore_requires_explicit_double_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "staging")
    with pytest.raises(pg.BackupError, match="confirm"):
        pg.restore_staging(archive=tmp_path/"archive.age", identity="id",
                           target_dsn=dsn("kats_staging"), confirmation="")


def test_staging_restore_does_not_target_same_primary(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DATABASE_URL", dsn("kats_staging"))
    with pytest.raises(pg.BackupError, match="Source/target"):
        pg.restore_staging(archive=tmp_path/"archive.age", identity="id",
                           target_dsn=dsn("kats_staging"),
                           confirmation="RESTORE_ISOLATED_STAGING_ONLY")


def test_backup_encrypts_and_checksums_before_publishing(monkeypatch, tmp_path, capsys):
    calls = []
    monkeypatch.setattr(pg, "ensure_binary", lambda name: None)
    monkeypatch.setattr(pg, "verify_plain_dump", lambda path: None)
    monkeypatch.setattr(pg, "check", lambda cmd, **kw: (
        calls.append(cmd[:]) or
        (Path(next(x[7:] for x in cmd if x.startswith("--file="))).write_bytes(b"plain-data" * 200)
         if cmd[0] == "pg_dump" else
         Path(cmd[cmd.index("--output") + 1]).write_bytes(b"age-encrypted-payload" * 20))
    ))
    archive = pg.backup(database_url=dsn(), recipient="age1testrecipient",
                        destination=tmp_path / "backups")
    assert archive.exists() and archive.name.endswith(".dump.age")
    assert archive.read_bytes().startswith(b"age-encrypted")
    checksum = archive.with_name(archive.name + ".sha256")
    assert checksum.read_text(encoding="ascii").split()[0] == pg.sha256(archive)
    assert calls[0][0] == "pg_dump" and calls[-1][0] == "age"
    assert "NOT OFFSITE" in capsys.readouterr().out


def test_invalid_archive_checksum_blocks_decryption(monkeypatch, tmp_path):
    archive = tmp_path / "dump.age"
    archive.write_bytes(b"encrypted")
    (tmp_path / "dump.age.sha256").write_text("0" * 64 + " dump.age", encoding="ascii")
    identity = tmp_path / "identity.txt"
    identity.write_text("private-test-key")
    monkeypatch.setattr(pg, "ensure_binary", lambda command: None)
    monkeypatch.setattr(pg, "check", lambda *args, **kw:pytest.fail("Tamper check must precede decryption"))
    with pytest.raises(pg.BackupError, match="checksum mismatch"):
        pg.decrypt_and_validate(archive, str(identity), tmp_path)


def test_scripts_no_longer_use_nonexistent_compose_db():
    backup = (ROOT/"ops"/"backup-postgres.sh").read_text(encoding="utf-8")
    restore = (ROOT/"ops"/"restore-staging.sh").read_text(encoding="utf-8")
    assert "docker compose exec" not in backup + restore
    assert "managed_postgres.py" in backup and "managed_postgres.py" in restore
    assert "restore-staging" in restore
