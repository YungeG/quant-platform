"""Planner-only synthetic declarations; no research target is imported or run."""
import builtins
import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("validation_profiles", ROOT / "tools/validate_change.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def scope(path="docs/notes/example.md", role="informational"):
    return {"schema_version": 1, "changes": [
        {"path": path, "role": role, "review_basis": "Synthetic reviewed explanation"}],
        "previous_manifest": {"files": {}, "checks": {}},
        "current_manifest": {"files": {}, "checks": {}}}


def ids(plan):
    return [c["id"] for c in plan["checks"]]


def test_offline_pc_planner_entry_is_single_and_not_pass():
    plan = v.build_plan(scope(v.PROXY, "local"))
    assert plan["overall_status"] == "NOT_RUN"
    entry = plan["offline_execution_entry"]
    assert entry["profile"] == "offline-pc"
    assert entry["covers"] == list(v.PLAN_IDS[1:4])
    assert entry["automatic_execution"] is False
    assert entry["argv_template"][-1] == "<EXCLUSIVE_OUTPUT>"
    assert all(c["execution_status"] == "NOT_RUN" for c in plan["checks"])
    assert plan["verification_passed"] is False and plan["reuse_allowed"] is False
    assert v.build_plan(scope())["offline_execution_entry"] is None
    assert v.build_plan(scope(v.CAPTURE_PATHS[0], "public"))["overall_status"] == "BLOCKED"


def test_manual_b0_selection_sentinel():
    assert ids(v.build_plan(scope())) == list(v.PLAN_IDS[:1])
    assert ids(v.build_plan(scope(v.PROXY, "local"))) == list(v.PLAN_IDS[1:4])
    assert ids(v.build_plan(scope(v.CAPTURE_PATHS[0], "public"))) == list(v.PLAN_IDS[1:])


@pytest.mark.parametrize("path", ["CONTEXT.md", "AGENTS.md", "CLAUDE.md", "a/AGENTS.md",
    "implementation/notes.md", "overall/notes.md", "backtest/docs/adr/example.md",
    "docs/agents/notes.md"])
def test_normative_cannot_downgrade(path):
    plan = v.build_plan(scope(path))
    assert plan["overall_status"] == "BLOCKED" and plan["unmodeled_scope"]
    assert ids(plan) == []


@pytest.mark.parametrize("role", ["informational", "unknown", "dependency", "fixture", "public"])
def test_proxy_role_mismatch_keeps_requirements(role):
    plan = v.build_plan(scope(v.PROXY, role))
    assert ids(plan) == list(v.PLAN_IDS[1:4])
    assert plan["unmodeled_scope"]


@pytest.mark.parametrize("path", v.CAPTURE_PATHS)
def test_capture_paths_cannot_downgrade(path):
    plan = v.build_plan(scope(path))
    assert ids(plan) == list(v.PLAN_IDS[1:]) and plan["unmodeled_scope"]


def test_authority_and_mixed_unknown():
    assert ids(v.build_plan(scope("other/code.py", "authority"))) == list(v.PLAN_IDS[1:])
    value = scope(v.PROXY, "local")
    value["changes"].append(scope("unknown/code.py", "unknown")["changes"][0])
    plan = v.build_plan(value)
    assert ids(plan) == list(v.PLAN_IDS[1:4]) and len(plan["unmodeled_scope"]) == 1
    assert v.build_plan(scope("unknown/code.py", "local"))["overall_status"] == "BLOCKED"
    assert v.build_plan(scope("docs/note.md", "local"))["overall_status"] == "BLOCKED"
    value = scope()
    value["changes"][0]["review_basis"] = " "
    assert v.build_plan(value)["overall_status"] == "BLOCKED"


@pytest.mark.parametrize("path", ["", "/abs", "../a", "a/../b", "./a", "a//b", "a/", "a\\b", "a\nb", "a b", "a/.", "x" * 257])
def test_invalid_paths(path):
    with pytest.raises(v.Blocked):
        v.build_plan(scope(path))


def test_closed_shapes_and_limits():
    invalid = []
    for key, value in [("schema_version", True), ("schema_version", 2), ("changes", {}),
                       ("changes", []), ("approval", True)]:
        item = scope()
        item[key] = value
        invalid.append(item)
    item = scope()
    item["changes"] *= 2
    invalid.append(item)
    for field, value in [("role", True), ("role", "approved"), ("review_basis", "x" * 257),
                         ("review_basis", None), ("extra", False)]:
        item = scope()
        item["changes"][0][field] = value
        invalid.append(item)
    item = scope()
    item["changes"] = [dict(item["changes"][0], path=f"docs/{n}.md") for n in range(65)]
    invalid.append(item)
    for manifest in [{}, {"files": [], "checks": {}}, {"files": {"../bad": "a" * 64}, "checks": {}},
                     {"files": {"a": True}, "checks": {}}, {"files": {}, "checks": {"bogus": {}}},
                     {"files": {}, "checks": {"proxy_smoke": {"source": "bad"}}},
                     {"files": {}, "checks": {"proxy_smoke": {"argv": [False]}}},
                     {"files": {}, "checks": {"proxy_smoke": {"extra": None}}}]:
        item = scope()
        item["current_manifest"] = manifest
        invalid.append(item)
    for item in invalid:
        with pytest.raises(v.Blocked):
            v.build_plan(item)


def identity():
    return {d: ["synthetic"] if d == "argv" else "a" * 64 for d in v.DIMENSIONS}


@pytest.mark.parametrize("dimension", v.DIMENSIONS)
def test_comparison_precedence_no_reuse(dimension):
    old = {"proxy_smoke": identity()}
    current = copy.deepcopy(old)
    assert v.compare_evidence(old, current)["proxy_smoke"]["state"] == "UNCHANGED_DECLARED"
    current["proxy_smoke"][dimension] = ["different"] if dimension == "argv" else "b" * 64
    result = v.compare_evidence(old, current)["proxy_smoke"]
    assert result["state"] == "INVALIDATED" and result["reuse_allowed"] is False
    del current["proxy_smoke"]["source" if dimension != "source" else "env"]
    assert v.compare_evidence(old, current)["proxy_smoke"]["state"] == "INVALIDATED"
    current = {"proxy_smoke": {}}
    assert v.compare_evidence(old, current)["proxy_smoke"]["state"] == "UNKNOWN"
    assert v.compare_evidence({}, {})["proxy_smoke"]["state"] == "UNKNOWN"


def test_pure_functions_no_io_or_business_imports(monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError("forbidden planner action")
    original_import = builtins.__import__
    def guarded_import(name, *args, **kwargs):
        if name.startswith(("experiments", "backtest", "research")):
            forbidden()
        return original_import(name, *args, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(builtins, "open", forbidden)
        m.setattr(Path, "stat", forbidden)
        m.setattr(Path, "open", forbidden)
        m.setattr(v, "environment", forbidden)
        m.setattr(v, "run_process", forbidden)
        m.setattr(builtins, "__import__", guarded_import)
        assert ids(v.build_plan(scope())) == ["document_review"]
        assert v.compare_evidence({}, {})["proxy_smoke"]["state"] == "UNKNOWN"


def test_status_commands_and_preserved_manifests():
    value = scope(v.CAPTURE_PATHS[0], "public")
    value["current_manifest"]["checks"] = {name: identity() for name in v.PLAN_IDS}
    before = copy.deepcopy(value)
    plan = v.build_plan(value)
    assert value == before and plan["current_manifest"] == value["current_manifest"]
    assert plan["artifact_kind"] == "validation_plan" and plan["plan_status"] == "GENERATED"
    assert plan["scope_completeness"] == "DECLARED_ONLY" and plan["identity_trust"] == "UNVERIFIED"
    assert plan["overall_status"] == "BLOCKED"
    assert plan["verification_passed"] is False and plan["reuse_allowed"] is False
    for check in plan["checks"]:
        assert check["execution_status"] in ("NOT_RUN", "BLOCKED")
        assert check["exit_code"] is None and check["duration_ms"] is None
    smoke, proxy, capture, native = plan["checks"]
    assert smoke["intended_argv"] == [str(ROOT / ".venv/bin/python"), "-I", "-B", "-m", "pytest",
        "-c", str(ROOT / "pyproject.toml"), f"--confcutdir={ROOT / 'tests/research'}",
        "-p", "no:cacheprovider", "-q", *v.SMOKE_NODES]
    assert smoke["declared_argv_matches_intended"] is False
    assert proxy["blocked_reasons"] == capture["blocked_reasons"] == []
    assert proxy["execution_status"] == capture["execution_status"] == "NOT_RUN"
    assert native["intended_argv"] is None and native["blocked_reasons"] == ["no_native_authorization"]


def pc_module():
    spec = importlib.util.spec_from_file_location("pc_test", ROOT / "tools/validation_offline_pc.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    return pc


def pc_reports(pc):
    nodes = []
    for name, count in [("test_unapproved_endpoint_rejected", 4),
                        ("test_failure_redacted_no_retry_no_failover_no_refund", 4),
                        ("test_capture_retains_exact_safe_bytes_without_pandas_or_second_request", 1)]:
        nodes.extend(pc.FILES[0] + "::" + name + (f"[{i}]" if count > 1 else "") for i in range(count))
    nodes.extend(pc.FILES[0] + f"::test_synthetic_{i}" for i in range(48))
    nodes.extend(pc.FILES[1] + f"::test_synthetic_{i}" for i in range(41))
    return {"nodes": nodes, "errors": 0, "deselected": 0}, [
        {"nodeid": n, "when": phase, "outcome": "passed", "wasxfail": False}
        for n in nodes for phase in ("setup", "call", "teardown")]


@pytest.mark.parametrize("fault", ["none", "skip", "xfail", "missing", "duplicate", "deselect", "empty", "group", "extra"])
def test_offline_pc_requires_complete_pass_reports(fault):
    pc = pc_module()
    collection, reports = pc_reports(pc)
    if fault == "skip":
        reports[1]["outcome"] = "skipped"
    elif fault == "xfail":
        reports[1]["wasxfail"] = True
    elif fault == "missing":
        reports.pop()
    elif fault == "duplicate":
        reports.append(dict(reports[0]))
    elif fault == "deselect":
        collection["deselected"] = 1
    elif fault == "empty":
        collection["nodes"] = []
    elif fault == "group":
        old = collection["nodes"][0]
        collection["nodes"][0] = pc.FILES[0] + "::test_wrong_group"
        for row in reports:
            if row["nodeid"] == old:
                row["nodeid"] = collection["nodes"][0]
    elif fault == "extra":
        collection["nodes"].append(pc.FILES[0] + "::test_extra")
    if fault == "none":
        assert pc.coverage_for(collection, reports)["covered"] == list(v.PLAN_IDS[1:4])
    else:
        with pytest.raises(pc.QualificationError):
            pc.coverage_for(collection, reports)


def pc_evidence(pc, argv):
    collection, reports = pc_reports(pc)
    env = {"safe_values": pc.clean_env(), "unexpected_key_count": 0}
    before = {"files": {}}
    report = {"schema_version": 1, "profile": "offline-pc", "argv": argv, "cwd": str(ROOT),
        "before": before, "after": before, "env_before": env, "env_after": env,
        "guard_selftest": [{"event": e, "reason": r, "synthetic": True} for e, r in
            [("socket.connect", "NETWORK_FORBIDDEN"), ("subprocess.Popen", "PROCESS_LAUNCH_FORBIDDEN"),
             ("open", "SOURCE_OR_CREDENTIAL_FORBIDDEN")]], "unexpected_guard_events": [],
        "collection": collection, "reports": reports, "pytest_exit": 0, "post_only_modules": {}, "error": None}
    process = {"status": "PASS", "exit_code": 0, "argv": argv, "popen_env": pc.clean_env()}
    return process, report, before


@pytest.mark.parametrize("fault", ["none", "identity", "environment", "exit", "false-exit", "guard", "unknown-module", "keys"])
def test_offline_pc_binds_identity_env_and_reports(fault):
    pc = pc_module()
    argv = pc.argv_for_pc(ROOT, Path("/synthetic-output"))
    process, report, before = pc_evidence(pc, argv)
    after = copy.deepcopy(before)
    if fault == "identity":
        after["changed"] = True
    elif fault == "environment":
        report["env_before"]["unexpected_key_count"] = 1
    elif fault == "exit":
        process["exit_code"] = 4
    elif fault == "false-exit":
        report["pytest_exit"] = False
    elif fault == "guard":
        report["unexpected_guard_events"] = [{"event": "open"}]
    elif fault == "unknown-module":
        report["post_only_modules"] = {"experiments.unreviewed": {}}
    elif fault == "keys":
        report["caller_qualified"] = True
    if fault == "none":
        assert pc.validate_pc(process, report, before, after, argv)["unique_collected"] == 98
    else:
        with pytest.raises(pc.QualificationError):
            pc.validate_pc(process, report, before, after, argv)
    assert len(pc.module_paths(ROOT)) == 46


def test_offline_pc_fixed_entry_and_exclusive_output(tmp_path, monkeypatch):
    pc = pc_module()
    output = tmp_path / "output"
    argv = pc.argv_for_pc(ROOT, output)
    process, report, before = pc_evidence(pc, argv)
    calls = []
    def run(actual, cwd, log, deadline, seconds, cap, *, env):
        calls.append((actual, cwd, seconds, cap, env))
        return process
    monkeypatch.setattr(v, "_load_offline_pc", lambda: pc)
    monkeypatch.setattr(v, "environment", lambda root: {})
    monkeypatch.setattr(pc, "snapshot_pc", lambda root, runtime: before)
    monkeypatch.setattr(pc, "read_child_report", lambda target: report)
    monkeypatch.setattr(v, "run_process", run)
    assert v.main(["--profile", "offline-pc", "--output", str(output)]) == 0
    result = json.loads((output / "result.json").read_text())
    assert result["coverage"]["covered"] == list(pc.COVERS)
    assert result["source_qualified"] is result["native_authorized"] is result["reuse_allowed"] is False
    assert calls == [(argv, ROOT, 60, 2 * 1024 * 1024, pc.clean_env())]
    assert v.main(["--profile", "offline-pc", "--output", str(output)]) == 2
    assert v.main(["--profile", "offline-pc", "--output", str(output), "--scope", "unused"]) == 2
    assert len(calls) == 1


@pytest.mark.parametrize("reason,exit_code", [("PROCESS_ERROR: synthetic", None), ("CLEANUP_ERROR", 0), ("EXIT_NONZERO", 9)])
@pytest.mark.parametrize("after_error", [False, True])
def test_offline_pc_preserves_primary_process_failure(tmp_path, monkeypatch, reason, exit_code, after_error):
    pc = pc_module()
    monkeypatch.setattr(v, "_load_offline_pc", lambda: pc)
    monkeypatch.setattr(v, "environment", lambda root: {})
    calls = []
    def snapshot(root, runtime):
        calls.append(True)
        if len(calls) == 2 and after_error:
            raise pc.QualificationError("SYNTHETIC_AFTER_FAILURE")
        return {"files": {}}
    def run(argv, *args, **kwargs):
        return {"status": "FAIL", "reason": reason, "exit_code": exit_code, "argv": argv}
    monkeypatch.setattr(pc, "snapshot_pc", snapshot)
    monkeypatch.setattr(v, "run_process", run)
    output = tmp_path / "failed"
    assert v.main(["--profile", "offline-pc", "--output", str(output)]) == 1
    result = json.loads((output / "result.json").read_text())
    check = result["checks"][1]
    assert result["reason"] == check["reason"] == reason
    assert check["process_result"]["reason"] == reason and check["process_result"]["exit_code"] == exit_code
    assert check.get("secondary_reasons", []) == (["AFTER_SNAPSHOT: SYNTHETIC_AFTER_FAILURE"] if after_error else [])


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_offline_pc_stop_preserves_pack_failure(tmp_path, monkeypatch, signum):
    pc = pc_module()
    monkeypatch.setattr(v, "_load_offline_pc", lambda: pc)
    monkeypatch.setattr(v, "environment", lambda root: {})
    monkeypatch.setattr(pc, "snapshot_pc", lambda root, runtime: {"files": {}})
    def stop(*_a, **_k):
        raise v.Stopped(signum)
    def fail(*_a):
        raise OSError("synthetic persistence failure")
    monkeypatch.setattr(v, "run_process", stop)
    monkeypatch.setattr(v, "persist", fail)
    assert v.main(["--profile", "offline-pc", "--output", str(tmp_path / "stop")]) == 128 + signum


@pytest.mark.parametrize("kind", ["duplicate", "fifo", "symlink", "oversize"])
def test_offline_pc_bounded_report(tmp_path, kind, monkeypatch):
    pc = pc_module()
    (tmp_path / "child").mkdir()
    path = tmp_path / "child/child.json"
    if kind == "fifo":
        os.mkfifo(path)
    elif kind == "symlink":
        target = tmp_path / "real"
        target.write_text("{}")
        path.symlink_to(target)
    else:
        path.write_text('{"a":1,"a":2}' if kind == "duplicate" else " " * 50)
        if kind == "oversize":
            monkeypatch.setitem(pc.LIMITS, "report_bytes", 5)
    with pytest.raises(pc.QualificationError):
        pc.read_child_report(tmp_path)


def test_offline_pc_explicit_env_and_synthetic_guard(tmp_path, monkeypatch):
    pc = pc_module()
    guard = pc.Guard(ROOT, tmp_path, [])
    assert guard.check("/dev/null") is None and guard.check("/dev/null", True) is None
    assert guard.check("/dev/other-unreviewed") is not None
    guard.audit("open", ("/", "r", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
    guard.audit("open", (str(tmp_path.parent), "r", os.O_RDONLY | os.O_DIRECTORY))
    with pytest.raises(OSError):
        guard.audit("open", ("/srv", "r", os.O_RDONLY | os.O_DIRECTORY))
    with pytest.raises(OSError):
        guard.audit("open", ("/srv/original.csv", "r", os.O_RDONLY))
    assert guard.check(str(ROOT / ".venv/lib/python3.13/site-packages/crypto_quant_domain/unreviewed.py")) is not None
    monkeypatch.setenv("PC_POISON_SECRET", "DO_NOT_INHERIT")
    code = ("import importlib.util,json; from pathlib import Path; "
        f"s=importlib.util.spec_from_file_location('p',{str(ROOT / 'tools/validation_offline_pc.py')!r}); "
        "p=importlib.util.module_from_spec(s);s.loader.exec_module(p); "
        f"g=p.Guard(p.ROOT,Path({str(tmp_path)!r}),[]);g.install();g.selftest(); "
        "f=p.os.open('/',p.os.O_RDONLY|p.os.O_DIRECTORY);p.os.close(f); "
        "print(json.dumps({'env':p.observed_env(),'synthetic':len(g.events)}))")
    log = tmp_path / "env.log"
    result = v.run_process([str(ROOT / ".venv/bin/python"), "-I", "-B", "-c", code],
        ROOT, log, __import__("time").monotonic() + 10, 8, env=pc.clean_env())
    assert result["exit_code"] == 0 and result["popen_env"] == pc.clean_env()
    data = json.loads(log.read_text())
    assert pc.valid_env(data["env"]) and data["synthetic"] == 3
    assert "DO_NOT_INHERIT" not in log.read_text()
    env = {"safe_values": {**pc.clean_env(), "LC_CTYPE": "C.UTF-8"}, "unexpected_key_count": 0}
    assert pc.valid_env(env)
    env["safe_values"]["LC_CTYPE"] = "other"
    assert not pc.valid_env(env)


def invoke(source, output):
    return v.main(["--profile", "plan", "--scope", str(source), "--output", str(output)])


def test_cli_local_no_execution_and_exclusive_output(tmp_path, monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError("forbidden execution")
    monkeypatch.setattr(v, "environment", forbidden)
    monkeypatch.setattr(v, "run_process", forbidden)
    source = tmp_path / "scope.json"
    source.write_text(json.dumps(scope()))
    output = tmp_path / "output"
    assert invoke(source, output) == 3
    assert json.loads((output / "scope.json").read_text()) == scope()
    assert json.loads((output / "plan.json").read_text())["overall_status"] == "NOT_RUN"
    assert invoke(source, output) == 1
    source.write_text(json.dumps(scope(v.PROXY, "local")))
    assert invoke(source, tmp_path / "pc-required") == 3
    assert invoke(source, source) == 1
    assert invoke(source, tmp_path) == 1
    assert v.main(["--profile", "self", "--scope", str(source), "--output", str(output)]) == 2


@pytest.mark.parametrize("kind", ["duplicate", "oversize", "badjson", "fifo", "symlink", "directory", "permission"])
def test_bad_scope_files(tmp_path, kind, capsys):
    source = tmp_path / "scope.json"
    if kind == "fifo":
        os.mkfifo(source)
    elif kind == "symlink":
        target = tmp_path / "target"
        target.write_text(json.dumps(scope()))
        source.symlink_to(target)
    elif kind == "directory":
        source.mkdir()
    else:
        source.write_text('{"secret":"DO_NOT_ECHO", "secret": 1}' if kind == "duplicate"
                          else " " * (v.SCOPE_CAP + 1) if kind == "oversize"
                          else "DO_NOT_ECHO" if kind == "badjson" else json.dumps(scope()))
        if kind == "permission":
            source.chmod(0)
    try:
        assert invoke(source, tmp_path / "output") == 1
        assert "DO_NOT_ECHO" not in capsys.readouterr().err
    finally:
        if kind == "permission":
            source.chmod(0o600)


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_stop_preserved_on_read_or_pack(tmp_path, monkeypatch, signum):
    source = tmp_path / "scope.json"
    source.write_text(json.dumps(scope()))
    def stop(*_a):
        os.kill(os.getpid(), signum)
    with monkeypatch.context() as m:
        m.setattr(v, "_read_scope", stop)
        assert invoke(source, tmp_path / "stopped-read") == 128 + signum
    with monkeypatch.context() as m:
        m.setattr(v, "_persist_plan", stop)
        assert invoke(source, tmp_path / "stopped-pack") == 128 + signum


def test_packaging_errors_and_readback(tmp_path, monkeypatch):
    source = tmp_path / "scope.json"
    source.write_text(json.dumps(scope()))
    with monkeypatch.context() as m:
        def fail(*_a):
            raise OSError("DO_NOT_ECHO")
        m.setattr(v.os, "fsync", fail)
        assert invoke(source, tmp_path / "fsync") == 1
    original = Path.read_bytes
    with monkeypatch.context() as m:
        m.setattr(Path, "read_bytes", lambda p: b"wrong" if p.name == "plan.json" else original(p))
        assert invoke(source, tmp_path / "readback") == 1
    with monkeypatch.context() as m:
        m.setattr(v, "OUTPUT_CAP", 1)
        assert invoke(source, tmp_path / "cap") == 1


def test_real_plan_cli(tmp_path):
    source = tmp_path / "scope.json"
    source.write_text(json.dumps(scope()))
    proc = subprocess.run([str(ROOT / ".venv/bin/python"), "-B", str(ROOT / "tools/validate_change.py"),
        "--profile", "plan", "--scope", str(source), "--output", str(tmp_path / "output")],
        capture_output=True, text=True, timeout=10, env=v.OPTIONS)
    assert proc.returncode == 3 and json.loads(proc.stdout)["status"] == "NOT_RUN"
    assert not proc.stderr


def test_self_rejects_scope_without_reading(monkeypatch):
    def forbidden(*_a):
        raise AssertionError("scope read")
    monkeypatch.setattr(v, "_read_scope", forbidden)
    monkeypatch.setattr(v.os, "execve", forbidden)
    assert v.main(["--profile", "self", "--scope", "unused", "--output", "unused"]) == 2


def test_plan_equals_missing_scope_argument_sentinel(capsys):
    assert v.main(["--profile=plan", "--output", "unused", "--scope"]) == 1
    assert capsys.readouterr().err == "invalid command arguments\n"


def test_argument_errors_redacted(capsys):
    assert v.main(["--profile", "plan", "--output", "unused", "--secret=DO_NOT_ECHO"]) == 1
    assert "DO_NOT_ECHO" not in capsys.readouterr().err
    assert v.main(["--profile", "plan", "--output", "unused"]) == 1


def test_declared_output_overlap_without_target_io(tmp_path, monkeypatch):
    monkeypatch.setattr(v, "ROOT", tmp_path / "project")
    source = tmp_path / "scope.json"
    source.write_text(json.dumps(scope("notes/plan.json", "unknown")))
    assert invoke(source, v.ROOT / "notes") == 1
    assert not v.ROOT.exists()


def test_bounded_read_and_duplicate_manifest(tmp_path, monkeypatch):
    source = tmp_path / "scope.json"
    source.write_text(json.dumps(scope()))
    original = v.os.fdopen
    sizes = []
    class Reader:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def fileno(self):
            return self.stream.fileno()
        def read(self, size):
            sizes.append(size)
            return self.stream.read(size)
    monkeypatch.setattr(v.os, "fdopen", lambda *a: Reader(original(*a)))
    assert invoke(source, tmp_path / "output") == 3
    assert sizes == [v.SCOPE_CAP + 1]
    raw = json.dumps(scope()).replace('"files": {}', '"files": {"a": "' + 'a' * 64 + '", "a": "' + 'b' * 64 + '"}', 1)
    source.write_text(raw)
    assert invoke(source, tmp_path / "duplicate") == 1


PARSER_CASES = [
    (["--profile=plan", "--output", "unused", "--scope"], 1),
    (["--profile", "plan", "--output=unused", "--scope"], 1),
    (["--output", "unused", "--scope", "--profile=plan"], 1),
    (["--profile", "self", "--output", "plan", "--unknown"], 2),
    (["--output=plan", "--unknown", "--profile=self"], 2),
    (["--scope", "plan", "--output", "unused", "--unknown"], 2),
    (["--profile", "plan", "--help"], 1),
    (["--help", "--profile=plan"], 1),
    (["--profile=plan", "-h"], 1),
    (["--profile", "self", "--help"], 0),
    (["--help"], 0),
    (["--output", "plan", "--help"], 0),
    (["--profile=plan", "--profile", "self", "--output", "plan", "--unknown"], 2),
    (["--profile=self", "--profile", "plan", "--output", "unused", "--unknown"], 1),
    (["--profile", "plan", "--profile=self", "--help"], 0),
    (["--profile", "self", "--profile=plan", "--help"], 1),
    (["--profile=plan", "--output", "unused", "--unknown=DO_NOT_ECHO"], 1),
    (["--profile=self", "--output", "plan", "--unknown=DO_NOT_ECHO"], 2),
    (["--profile=plan", "--profile"], 1),
    (["--help", "--profile=plan", "--profile"], 1),
    (["--profile", "--help", "--profile=plan"], 1),
    (["--profile=plan", "--profile=self", "--profile"], 2),
]


@pytest.mark.parametrize("argv,expected", PARSER_CASES)
def test_profile_parser_contract(argv, expected, capsys, monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError("unexpected validation or planner execution")
    monkeypatch.setattr(v, "_plan_main", forbidden)
    monkeypatch.setattr(v, "prepare_output", forbidden)
    assert v.main(argv) == expected
    captured = capsys.readouterr()
    assert "DO_NOT_ECHO" not in captured.err
    assert "PASS" not in captured.out


@pytest.mark.parametrize("argv,expected", PARSER_CASES)
def test_real_profile_parser_contract(argv, expected):
    proc = subprocess.run([str(ROOT / ".venv/bin/python"), "-I", "-B",
        str(ROOT / "tools/validate_change.py"), *argv],
        capture_output=True, text=True, timeout=10, env=v.OPTIONS)
    assert proc.returncode == expected
    assert "DO_NOT_ECHO" not in proc.stderr
    assert "PASS" not in proc.stdout
