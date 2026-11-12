"""PostgreSQL demo startup must be idempotent and never recreate roles casually."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = spec_from_file_location("local_pg_demo_prepare_tests", ROOT/"ops"/"local_postgres_demo.py")
pg = module_from_spec(spec)
spec.loader.exec_module(pg)


def test_configured_prepare_is_strictly_read_only_and_never_reseeds(monkeypatch,tmp_path):
    config=tmp_path/".env.pg-demo"
    config.write_text("exists", encoding="utf-8")
    monkeypatch.setattr(pg,"CONFIG",config)
    values={"KATS_DEMO_INSTANCE":"x"*32}
    monkeypatch.setattr(pg,"load",lambda:values)
    calls=[]
    monkeypatch.setattr(pg,"marker",lambda vals,role=pg.OWNER:calls.append(("marker",role)))
    monkeypatch.setattr(pg,"run",lambda *_a,**_kw:pytest.fail("Warm startup must never migrate or seed"))
    monkeypatch.setattr(pg,"grants",lambda *_a:pytest.fail("Warm startup must not mutate grants"))
    monkeypatch.setattr(pg,"admin_bootstrap",lambda *_a:pytest.fail("Warm startup must not prompt for admin"))
    pg.prepare()
    pg.prepare()
    assert calls==[("marker",pg.OWNER),("marker",pg.RUNTIME)] * 2


def test_manual_upgrade_only_migrates_permissions_never_seeds(monkeypatch):
    monkeypatch.setattr(pg,"load",lambda:{"KATS_DEMO_INSTANCE":"x"*32})
    calls=[]
    monkeypatch.setattr(pg,"marker",lambda *_a,**_kw:None)
    monkeypatch.setattr(pg,"run",lambda vals,role,args,cwd=pg.ROOT:
                        calls.append(("run",role,list(map(str,args)))))
    monkeypatch.setattr(pg,"grants",lambda vals:calls.append(("grants",)))
    pg.upgrade_schema()
    assert any("upgrade" in cmd for action,role,cmd in calls if action=="run")
    assert any("seed-permissions" in cmd for action,role,cmd in calls if action=="run")
    assert not any("--postgres" in cmd for action,role,cmd in calls if action=="run")


def test_first_run_requires_explicit_isolated_database_setup(monkeypatch,tmp_path):
    monkeypatch.setattr(pg,"CONFIG",tmp_path/".env.pg-demo")
    events=[]
    monkeypatch.setattr(pg,"setup",lambda:events.append("safe-setup"))
    pg.prepare()
    assert events==["safe-setup"]


def test_configured_marker_failure_blocks_all_changes(monkeypatch,tmp_path):
    path=tmp_path/".env.pg-demo"
    path.write_text("exists",encoding="utf-8")
    monkeypatch.setattr(pg,"CONFIG",path)
    monkeypatch.setattr(pg,"load",lambda:{"KATS_DEMO_INSTANCE":"x"*32})
    monkeypatch.setattr(pg,"marker",lambda *_a,**_kw: (_ for _ in ()).throw(RuntimeError("marker mismatch")))
    monkeypatch.setattr(pg,"run",lambda *_a,**_kw:pytest.fail("Unsafe migration attempted"))
    with pytest.raises(RuntimeError,match="marker mismatch"):
        pg.prepare()


def test_interrupted_first_setup_can_resume_through_safe_bootstrap(monkeypatch,tmp_path):
    config=tmp_path/".env.pg-demo"
    config.write_text("preallocated-first-run-config",encoding="utf-8")
    monkeypatch.setattr(pg,"CONFIG",config)
    monkeypatch.setattr(pg,"load",lambda:{"KATS_DEMO_INSTANCE":"x"*32})
    monkeypatch.setattr(pg,"marker",lambda *_a,**_kw: (_ for _ in ()).throw(
        pg.psycopg.OperationalError("role missing after incomplete local setup")))
    calls=[]
    monkeypatch.setattr(pg,"setup",lambda:calls.append("guarded-setup"))
    pg.prepare()
    assert calls==["guarded-setup"]
