"""PostgreSQL demo startup must be idempotent and never recreate roles casually."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = spec_from_file_location("local_pg_demo_prepare_tests", ROOT/"ops"/"local_postgres_demo.py")
pg = module_from_spec(spec)
spec.loader.exec_module(pg)


def test_configured_prepare_reuses_marker_and_never_asks_pg_admin(monkeypatch,tmp_path):
    config=tmp_path/".env.pg-demo"
    config.write_text("exists", encoding="utf-8")
    monkeypatch.setattr(pg,"CONFIG",config)
    values={"KATS_DEMO_INSTANCE":"x"*32}
    monkeypatch.setattr(pg,"load",lambda:values)
    calls=[]
    monkeypatch.setattr(pg,"marker",lambda vals,role=pg.OWNER:calls.append(("marker",role)))
    monkeypatch.setattr(pg,"run",lambda vals,role,args,cwd=pg.ROOT:
                        calls.append(("run",role,list(map(str,args)))))
    monkeypatch.setattr(pg,"grants",lambda vals:calls.append(("grants",)))
    monkeypatch.setattr(pg,"admin_bootstrap",lambda vals:pytest.fail("existing demo must not rebootstrap roles"))
    pg.prepare()
    assert calls[0]==("marker",pg.OWNER)
    assert calls[1]==("marker",pg.RUNTIME)
    assert ("grants",) in calls
    assert calls[-1]==("marker",pg.RUNTIME)
    commands=[entry[2] for entry in calls if entry[0]=="run"]
    assert any("db" in cmd and "upgrade" in cmd for cmd in commands)
    assert any("seed-permissions" in cmd for cmd in commands)
    assert any("--postgres" in cmd for cmd in commands)
    assert all("downgrade" not in cmd for cmd in commands)


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
