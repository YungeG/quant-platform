"""Synthetic offline contract checks; the five self nodes never call self."""
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("validate_change", ROOT / "tools/validate_change.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def synthetic(tmp_path, name, code, **kwargs):
    return v.run_process([sys.executable, "-I", "-B", "-c", code], tmp_path,
                         tmp_path / (name + ".log"), time.monotonic() + 5, **kwargs)


def passing():
    checks = v.blank_checks(v.ROOT)
    checks[0].update(status="PASS")
    checks[1].update(status="PASS", exit_code=0)
    return checks


def test_failure_is_not_masked(tmp_path):
    first = synthetic(tmp_path, "first", "print('first failed'); raise SystemExit(7)")
    last = synthetic(tmp_path, "last", "print('last passed')")
    assert first["exit_code"] == 7 and last["exit_code"] == 0
    checks = [dict(first, id="environment"), dict(last, id="validator_contract")]
    assert v.aggregate(checks, {"same": 1}, {"same": 1}) == ("FAIL", "REQUIRED_CHECK_FAILED", 1)
    assert (tmp_path / "first.log").read_text() == "first failed\n"


def fixture_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    for relative in v.FILES[:-1]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture " + relative)
    return root


def install_synthetic(monkeypatch, root, fail_environment=False):
    monkeypatch.setattr(v, "ROOT", root)
    def env(_root):
        if fail_environment:
            raise v.Blocked("missing dependency (synthetic)")
        return {"dependency": "fixture-v1"}
    monkeypatch.setattr(v, "environment", env)
    process_original = v.run_process
    # Capture the real runner, not this adapter, to avoid recursion.
    def adapter(argv, cwd, log, deadline, *limits):
        result = process_original([sys.executable, "-I", "-B", "-c", "print('kept log')"], cwd, log, deadline)
        result["argv"] = argv
        return result
    monkeypatch.setattr(v, "run_process", adapter)


def read_result(output):
    return json.loads((output / "result.json").read_text())


def test_packaging_failure_is_nonzero(tmp_path, monkeypatch):
    root = fixture_root(tmp_path)
    install_synthetic(monkeypatch, root)
    output = tmp_path / "blocked-result"
    run = v.run_process
    def deny_result(*args, **kwargs):
        result = run(*args, **kwargs)
        # Actual OS permission failure, only on the synthetic output directory.
        output.chmod(0o500)
        return result
    monkeypatch.setattr(v, "run_process", deny_result)
    try:
        assert v.main(["--profile", "self", "--output", str(output)]) == 1
        assert (output / "validator_contract.log").read_text() == "kept log\n"
        assert not (output / "result.json").exists()
    finally:
        if output.exists():
            output.chmod(0o700)
    # A completed candidate file is still not success if readback fails.
    output2 = tmp_path / "bad-readback"
    original_read = Path.read_bytes
    with monkeypatch.context() as m:
        m.setattr(v, "run_process", run)
        def bad_read(path):
            if path == output2 / "result.json":
                raise OSError("synthetic readback failure")
            return original_read(path)
        m.setattr(Path, "read_bytes", bad_read)
        assert v.main(["--profile", "self", "--output", str(output2)]) == 1
        assert (output2 / "validator_contract.log").read_text() == "kept log\n"
    cancelled = {"overall_status": "CANCELLED"}
    with monkeypatch.context() as m:
        m.setattr(v, "persist", lambda *_: (_ for _ in ()).throw(OSError("packing")))
        assert v.deliver(output, {}, cancelled, 130) == 130
        assert v.deliver(output, {}, cancelled, 143) == 143


def test_input_identity_change_prevents_pass(tmp_path, monkeypatch):
    root = fixture_root(tmp_path)
    install_synthetic(monkeypatch, root)
    initial = v.snapshot(root)
    checks = passing()
    assert v.aggregate(checks, initial, initial)[2] == 0
    # Actual synthetic source bytes and optional conftest presence are bound.
    source = root / v.FILES[0]
    source.write_text("changed bytes")
    assert v.aggregate(checks, initial, v.snapshot(root))[2] == 1
    source.write_text("fixture " + v.FILES[0])
    assert v.snapshot(root) == initial
    conf = root / v.FILES[-1]
    conf.write_text("# synthetic fixture")
    assert v.aggregate(checks, initial, v.snapshot(root))[2] == 1
    conf.unlink()
    with monkeypatch.context() as m:
        m.setattr(v, "environment", lambda _: {"dependency": "fixture-v2"})
        assert v.aggregate(checks, initial, v.snapshot(root))[2] == 1
    with monkeypatch.context() as m:
        m.setattr(v, "OPTIONS", {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "changed"})
        assert v.aggregate(checks, initial, v.snapshot(root))[2] == 1
    with monkeypatch.context() as m:
        m.setattr(v, "NODES", (*v.NODES[:-1], "different-node"))
        assert v.aggregate(checks, initial, v.snapshot(root))[2] == 1
    runner = v.run_process
    def mutate(*args, **kwargs):
        result = runner(*args, **kwargs)
        source.write_text("changed during check")
        return result
    monkeypatch.setattr(v, "run_process", mutate)
    output = tmp_path / "changed"
    assert v.main(["--profile", "self", "--output", str(output)]) == 1
    result = read_result(output)
    assert result["reason"] == "INPUT_IDENTITY_CHANGED"
    assert result["input_before_sha256"] != result["input_after_sha256"]


def not_running(pid):
    path = Path(f"/proc/{pid}/stat")
    return not path.exists() or path.read_text().split()[2] == "Z"


def test_stop_preserves_reason_and_cleans_child(tmp_path, monkeypatch):
    signal_windows(tmp_path, monkeypatch)
    # Descendant ignores TERM and outlives its parent unless the owned group is killed.
    for mode in ("timeout", "int", "term"):
        pidfile = tmp_path / (mode + ".pid")
        code = (
            "import os,signal,subprocess,sys,time; "
            "p=subprocess.Popen([sys.executable,'-I','-B','-c',"
            "'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(20)']); "
            f"open({str(pidfile)!r},'w').write(str(p.pid)); "
        )
        if mode != "timeout":
            signum = signal.SIGINT if mode == "int" else signal.SIGTERM
            code += f"time.sleep(.05); os.kill(os.getppid(),{int(signum)}); "
        code += "time.sleep(20)"
        old = {s: signal.signal(s, lambda s, _: (_ for _ in ()).throw(v.Stopped(s)))
               for s in (signal.SIGINT, signal.SIGTERM)}
        try:
            result = synthetic(tmp_path, mode, code, seconds=.25)
        finally:
            for s, handler in old.items():
                signal.signal(s, handler)
        assert result["reason"] == ("TIMEOUT" if mode == "timeout" else f"SIGNAL_{int(signum)}")
        assert result["status"] == ("FAIL" if mode == "timeout" else "CANCELLED")
        child = int(pidfile.read_text())
        until = time.monotonic() + 1
        while not not_running(child) and time.monotonic() < until:
            time.sleep(.01)
        assert not_running(child)
        assert result["exit_code"] is not None
    overflow = synthetic(tmp_path, "overflow", "import os; os.write(1,b'x'*4096)", cap=128)
    assert overflow["reason"] == "LOG_LIMIT" and overflow["log_truncated"]
    assert (tmp_path / "overflow.log").stat().st_size == 128
    # Main preserves cancellation and leaves later required work NOT_RUN.
    root = fixture_root(tmp_path)
    real_runner = v.run_process
    install_synthetic(monkeypatch, root)
    for signum in (signal.SIGINT, signal.SIGTERM):
        with monkeypatch.context() as m:
            def stop(_):
                raise v.Stopped(signum)
            m.setattr(v, "snapshot", stop)
            output = tmp_path / f"cancelled-{signum}"
            assert v.main(["--profile", "self", "--output", str(output)]) == 128 + signum
            result = read_result(output)
            assert result["overall_status"] == "CANCELLED"
            assert result["checks"][1]["status"] == "NOT_RUN"
    # First stop after a successful child exit must reach main's terminal receipt.
    for signum in (signal.SIGINT, signal.SIGTERM):
        with monkeypatch.context() as m:
            close = v.close_group
            def first_stop(*args):
                close(*args)
                signal.raise_signal(signum)
            m.setattr(v, "close_group", first_stop)
            output = tmp_path / f"close-cancelled-{signum}"
            assert v.main(["--profile", "self", "--output", str(output)]) == 128 + signum
            result = read_result(output)
            assert result["overall_status"] == "CANCELLED"
            assert result["reason"] == f"SIGNAL_{int(signum)}"
    # A cleanup failure must not replace an original cancellation.
    with monkeypatch.context() as m:
        real_close = v.close_group
        def bad_close(*args):
            real_close(*args)
            raise OSError("synthetic cleanup error")
        m.setattr(v, "close_group", bad_close)
        result = real_runner([sys.executable, "-I", "-B", "-c", "import time; time.sleep(20)"],
                             tmp_path, tmp_path / "cleanup.log", time.monotonic() + .05)
        assert result["reason"] == "TIMEOUT" and "cleanup_error" in result
        old = signal.signal(signal.SIGTERM, lambda s, _: (_ for _ in ()).throw(v.Stopped(s)))
        try:
            stopped = real_runner([sys.executable, "-I", "-B", "-c",
                                  "import os,signal,time; os.kill(os.getppid(),signal.SIGTERM); time.sleep(20)"],
                                 tmp_path, tmp_path / "stop-cleanup.log", time.monotonic() + 2)
        finally:
            signal.signal(signal.SIGTERM, old)
        assert stopped["reason"] == "SIGNAL_15" and stopped["status"] == "CANCELLED"
        assert "cleanup_error" in stopped


def test_required_check_set_is_exact(tmp_path, monkeypatch):
    isolated_metadata(tmp_path)
    checks = passing()
    for invalid in ([], checks[:1], checks[1:], checks[::-1], checks + [checks[1]],
                    [checks[0], dict(checks[1], id="unknown")]):
        assert v.aggregate(invalid, {}, {})[2] == 1
    for changed in (dict(checks[1], exit_code=None), dict(checks[1], exit_code=7),
                    dict(checks[1], status="NOT_RUN"), dict(checks[1], argv=["unexpected"])):
        assert v.aggregate([checks[0], changed], {}, {})[2] == 1
    root = fixture_root(tmp_path)
    # Wrong interpreter is a real preflight rejection, before dependency loading.
    with pytest.raises(v.Blocked, match="interpreter"):
        v.environment(root)
    install_synthetic(monkeypatch, root, fail_environment=True)
    output = tmp_path / "missing-dependency"
    monkeypatch.setattr(v, "run_process", lambda *_: pytest.fail("must not run after blocked environment"))
    assert v.main(["--profile", "self", "--output", str(output)]) == 2
    result = read_result(output)
    assert [c["status"] for c in result["checks"]] == ["BLOCKED", "NOT_RUN"]
    assert result["checks"][1]["duration_ms"] is None
    # Time spent in preflight is bounded and subsequent work does not start.
    with monkeypatch.context() as m:
        limits = dict(v.LIMITS, check_seconds=.02)
        m.setattr(v, "LIMITS", limits)
        m.setattr(v, "snapshot", lambda _: time.sleep(1))
        timeout_output = tmp_path / "preflight-timeout"
        assert v.main(["--profile", "self", "--output", str(timeout_output)]) == 1
        timed = read_result(timeout_output)
        assert timed["reason"] == "TIMEOUT" and timed["overall_status"] == "FAIL"
        assert timed["checks"][1]["status"] == "NOT_RUN"
    with pytest.raises(v.Blocked):
        v.prepare_output(root, output)
    for path in (root, root / "tools/validate_change.py", root / "uv.lock/child"):
        with pytest.raises(v.Blocked):
            v.prepare_output(root, path)
    link = tmp_path / "link"
    link.symlink_to(root, target_is_directory=True)
    with pytest.raises(v.Blocked, match="symlink"):
        v.prepare_output(root, link / "output")
    protected = root / "uv.lock"
    protected.unlink()
    protected.symlink_to(root / "pyproject.toml")
    with pytest.raises(v.Blocked, match="symlink"):
        v.file_identity(protected)
    protected.unlink()
    with pytest.raises(v.Blocked, match="missing"):
        v.file_identity(protected)
    protected.write_text("unreadable synthetic input")
    protected.chmod(0)
    try:
        with pytest.raises(PermissionError):
            v.file_identity(protected)
    finally:
        protected.chmod(0o600)


def test_self_cli_end_to_end(tmp_path):
    output = tmp_path / "self-output"
    # Deliberately poisoned implicit pytest entries are not inherited by self.
    poison = tmp_path / "poison"
    dist = poison / "pytest-0.0.dist-info"
    dist.mkdir(parents=True)
    (dist / "METADATA").write_text("Name: pytest\nVersion: 0.0\n")
    env = dict(v.OPTIONS, PYTHONPATH=str(poison), PYTEST_ADDOPTS="--invalid-implicit-option",
               PYTEST_PLUGINS="missing_plugin")
    result = subprocess.run([str(ROOT / ".venv/bin/python"), "-B", str(ROOT / "tools/validate_change.py"),
                             "--profile", "self", "--output", str(output)],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    record = read_result(output)
    receipt = json.loads(result.stdout)
    assert receipt["sha256"] == v.digest((output / "result.json").read_bytes())
    assert record["overall_status"] == "PASS"
    assert [c["id"] for c in record["checks"]] == list(v.IDS)
    assert record["checks"][0]["argv"] == []
    assert record["checks"][1]["argv"] == v.argv_for(ROOT)
    assert record["checks"][1]["exit_code"] == 0
    assert record["input_before_sha256"] == record["input_after_sha256"]
    inputs = json.loads((output / "inputs.json").read_text())
    assert v.digest(v.encoded(inputs["before"])) == record["input_before_sha256"]
    assert inputs["before"] == inputs["after"]
    assert set(inputs["before"]["runtime"]["distributions"]) >= {"pytest", "packaging"}
    assert str(poison) not in json.dumps(inputs)
    assert not (output / ".pytest_cache").exists()
    assert "5 passed" in (output / "validator_contract.log").read_text()
    assert str(output) not in json.dumps(inputs)


def signal_windows(tmp_path, monkeypatch):
    real_popen, real_close = v.subprocess.Popen, v.close_group
    for phase in ("launch", "close", "stdout"):
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGALRM):
            if phase != "launch" and signum == signal.SIGALRM:
                continue
            owned = []
            pidfile = tmp_path / f"{phase}-{signum}.pid"
            code = (
                "import subprocess,sys,time; "
                "p=subprocess.Popen([sys.executable,'-I','-B','-c','import time; time.sleep(20)']); "
                f"open({str(pidfile)!r},'w').write(str(p.pid)); time.sleep(20)"
            ) if phase == "launch" else "pass"
            with monkeypatch.context() as m:
                def create(*args, **kwargs):
                    proc = real_popen(*args, **kwargs)
                    owned.append(proc)
                    if phase == "launch":
                        until = time.monotonic() + 2
                        while not pidfile.exists() and time.monotonic() < until:
                            time.sleep(.005)
                        assert pidfile.exists()
                        signal.raise_signal(signum)
                    if phase == "stdout":
                        stdout = proc.stdout
                        class BadClose:
                            def __getattr__(self, name):
                                return getattr(stdout, name)
                            def close(self):
                                stdout.close()
                                signal.raise_signal(signum)
                                raise OSError("synthetic stdout close failure")
                        proc.stdout = BadClose()
                    return proc
                def close(*args):
                    real_close(*args)
                    if phase == "close":
                        assert args[0].returncode == 0
                        signal.raise_signal(signum)
                        raise OSError("synthetic close failure after first stop")
                m.setattr(v.subprocess, "Popen", create)
                m.setattr(v, "close_group", close)
                old = {s: signal.signal(s, lambda s, _: (_ for _ in ()).throw(
                    v.TimedOut() if s == signal.SIGALRM else v.Stopped(s)))
                    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGALRM)}
                try:
                    result = v.run_process([sys.executable, "-I", "-B", "-c", code], tmp_path,
                                           tmp_path / f"{phase}-{signum}.log", time.monotonic() + 3)
                    assert result["reason"] == ("TIMEOUT" if signum == signal.SIGALRM else f"SIGNAL_{int(signum)}")
                    assert result["status"] == ("FAIL" if signum == signal.SIGALRM else "CANCELLED")
                    assert all(not_running(p.pid) for p in owned)
                    if phase == "launch":
                        assert not_running(int(pidfile.read_text()))
                finally:
                    for s, handler in old.items():
                        signal.signal(s, handler)
                    # Also bound the intentionally failing original-candidate reproduction.
                    for proc in owned:
                        real_close(proc, time.monotonic() + 2)
                        if proc.stdout:
                            try:
                                if phase != "stdout":
                                    proc.stdout.close()
                            except OSError:
                                pass


def isolated_metadata(tmp_path):
    root = tmp_path / "metadata-project"
    (root / ".venv/bin").mkdir(parents=True)
    (root / ".venv/bin/python").write_bytes(b"synthetic identity")
    (root / ".venv/pyvenv.cfg").write_text("synthetic")
    (root / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.13,<3.14"\n[dependency-groups]\ndev = ["pytest==8.4.2"]\n')
    actual, poison = tmp_path / "actual-install", tmp_path / "pythonpath-install"
    for location, version in ((actual, "8.4.1"), (poison, "8.4.2")):
        dist = location / f"pytest-{version}.dist-info"
        dist.mkdir(parents=True)
        (dist / "METADATA").write_text(f"Name: pytest\nVersion: {version}\n")
        (dist / "RECORD").write_text(f"{dist.name}/METADATA,,\n{dist.name}/RECORD,,\n")
    probe = (
        "import importlib.util,json,pathlib,sys; "
        f"s=importlib.util.spec_from_file_location('v',{str(Path(v.__file__).absolute())!r}); "
        "v=importlib.util.module_from_spec(s); s.loader.exec_module(v); "
        f"root=pathlib.Path({str(root)!r}); sys.prefix=str(root/'.venv'); "
        "sys.executable=str(root/'.venv/bin/python'); "
        f"sys.path.insert(0,{str(actual)!r}); "
        f"sys.path[:0]=[] if sys.flags.isolated else [{str(poison)!r}]; "
        "\ntry:\n print(json.dumps(v.environment(root)))\n"
        "except v.Blocked as e:\n print(str(e)); sys.exit(2)\n"
    )
    # Missing metadata is checked under real -I/-B flags, never host flag patches.
    missing_probe = probe.replace(
        "\ntry:",
        "\ndef missing(_):\n raise v.metadata.PackageNotFoundError('synthetic missing metadata')\n"
        "v.metadata.distribution=missing\ntry:")
    result = subprocess.run([sys.executable, "-I", "-B", "-c", missing_probe],
                            env=dict(v.OPTIONS), capture_output=True, text=True, timeout=5)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "metadata unavailable" in result.stdout
    # Fake PYTHONPATH metadata cannot rescue an invalid actual installation.
    env = dict(v.OPTIONS, PYTHONPATH=str(poison))
    for flags in (("-B",), ("-I", "-B")):
        result = subprocess.run([sys.executable, *flags, "-c", probe], env=env,
                                capture_output=True, text=True, timeout=5)
        assert result.returncode == 2, result.stdout + result.stderr
    # Reverse the versions: isolated identity must bind actual, not poison.
    for location, version in ((actual, "8.4.2"), (poison, "8.4.1")):
        dist = next(location.glob("*.dist-info"))
        (dist / "METADATA").write_text(f"Name: pytest\nVersion: {version}\n")
    result = subprocess.run([sys.executable, "-I", "-B", "-c", probe], env=env,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stdout + result.stderr
    runtime = json.loads(result.stdout)
    assert runtime["distributions"]["pytest"]["location"] == str(actual)
    assert runtime["distributions"]["pytest"]["version"] == "8.4.2"
