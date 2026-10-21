"""Bounded offline self-validation; not a sandbox or research acceptance receipt."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import os
from pathlib import Path
import selectors
import re
import stat
import signal
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
FILES = ("tools/validate_change.py", "tests/validation/test_validate_change.py",
         "pyproject.toml", "uv.lock", "tests/validation/conftest.py")
NODES = tuple("tests/validation/test_validate_change.py::" + name for name in (
    "test_failure_is_not_masked", "test_packaging_failure_is_nonzero",
    "test_input_identity_change_prevents_pass", "test_stop_preserves_reason_and_cleans_child",
    "test_required_check_set_is_exact"))
IDS = ("environment", "validator_contract")
LIMITS = {"check_seconds": 30, "log_bytes": 1024 * 1024,
          "total_seconds": 120, "close_seconds": 10}
OPTIONS = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}


class Blocked(Exception):
    pass


class TimedOut(BaseException):
    pass


class Stopped(BaseException):
    def __init__(self, signum):
        self.signum = signum


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def no_symlinks(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            raise Blocked(f"symlink not permitted: {part}")


def file_identity(path, optional=False):
    no_symlinks(path)
    if optional and not path.exists():
        return {"path": str(path), "exists": False}
    if not path.is_file():
        raise Blocked(f"required regular file missing: {path}")
    return {"path": str(path), "exists": True, "sha256": digest(path.read_bytes())}


def argv_for(root):
    return [str(root / ".venv/bin/python"), "-I", "-B", "-m", "pytest", "-c",
            str(root / "pyproject.toml"), f"--confcutdir={root / 'tests/validation'}",
            "-p", "no:cacheprovider", "-q", *NODES]


def environment(root):
    """Only pytest's active declared dependency closure is inspected."""
    entry = root / ".venv/bin/python"
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise Blocked("isolated -I -B interpreter required")
    if not entry.is_file() or Path(sys.prefix) != root / ".venv" or Path(sys.executable).absolute() != entry:
        raise Blocked("interpreter must be project .venv/bin/python; no fallback")
    try:
        from packaging.requirements import Requirement
        from packaging.specifiers import SpecifierSet
        config = tomllib.loads((root / "pyproject.toml").read_text())
        if not SpecifierSet(config["project"]["requires-python"]).contains(sys.version.split()[0]):
            raise Blocked("Python version violates requires-python")
        requirements = [Requirement(s) for s in config["dependency-groups"]["dev"]]
        pytest_req = next(r for r in requirements if r.name.lower() == "pytest")
        pending, found = [pytest_req, Requirement("packaging")], {}
        while pending:
            req = pending.pop()
            if req.marker and not req.marker.evaluate({"extra": ""}):
                continue
            dist = metadata.distribution(req.name)
            if not req.specifier.contains(dist.version):
                raise Blocked(f"dependency version mismatch: {req.name}")
            name = dist.metadata["Name"]
            if name in found:
                continue
            paths = list(dist.files or ())
            hashes = {}
            for basename in ("METADATA", "RECORD"):
                matches = [p for p in paths if p.name == basename and p.parent.name.endswith('.dist-info')]
                if len(matches) != 1:
                    raise Blocked(f"missing or ambiguous {name} {basename}")
                hashes[basename] = file_identity(Path(dist.locate_file(matches[0])).absolute())
            found[name] = {"version": dist.version, "location": str(dist.locate_file('')), "metadata": hashes}
            pending.extend(Requirement(s) for s in (dist.requires or ()))
        return {"entry": str(entry), "resolved_executable": str(entry.resolve()),
                "executable_sha256": digest(entry.read_bytes()),
                "pyvenv": file_identity(root / ".venv/pyvenv.cfg"),
                "python": sys.version, "implementation": sys.implementation.name,
                "distributions": dict(sorted(found.items()))}
    except Blocked:
        raise
    except Exception as exc:
        raise Blocked(f"dependency metadata unavailable: {type(exc).__name__}: {exc}") from exc


def snapshot(root):
    return {"identity_scope": "self-inputs-v1", "schema_version": 1,
            "files": [file_identity(root / p, p == FILES[-1]) for p in sorted(FILES)],
            "runtime": environment(root), "checks": [
                {"id": IDS[0], "argv": []}, {"id": IDS[1], "argv": argv_for(root)}],
            "options": OPTIONS, "limits": LIMITS,
            "exclusions": ["output root", "result.json", "stdout/stderr", "temporary fixtures",
                           ".pytest_cache", "__pycache__"]}


def prepare_output(root, output):
    output = Path(os.path.abspath(output))
    no_symlinks(output)
    for relative in FILES:
        path = root / relative
        if output == path or output in path.parents or path in output.parents:
            raise Blocked("output overlaps input")
    try:
        output.mkdir(mode=0o700)  # parent must already exist; exclusive, never overwrite
    except OSError as exc:
        raise Blocked(f"exclusive output unavailable: {exc}") from exc
    return output


def blank_checks(root):
    return [{"id": name, "status": "NOT_RUN", "argv": [] if name == IDS[0] else argv_for(root),
             "exit_code": None, "duration_ms": None, "reason": None,
             "started_at": None, "finished_at": None} for name in IDS]


def aggregate(checks, before, after):
    if [c["id"] for c in checks] != list(IDS):
        return "FAIL", "REQUIRED_CHECK_SET", 1
    if before is None or after is None or before != after:
        return "FAIL", "INPUT_IDENTITY_CHANGED", 1
    if any(c["status"] != "PASS" or c["exit_code"] not in (None, 0) for c in checks):
        return "FAIL", "REQUIRED_CHECK_FAILED", 1
    if checks[1]["exit_code"] != 0 or checks[0]["exit_code"] is not None:
        return "FAIL", "MISSING_PROCESS_EXIT", 1
    if checks[0]["argv"] != [] or checks[1]["argv"] != argv_for(ROOT):
        return "FAIL", "COMMAND_MISMATCH", 1
    return "PASS", None, 0


def close_group(proc, deadline):
    """Close only the new session owned by this invocation, including descendants."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=max(0.001, min(0.2, deadline - time.monotonic())))
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait(timeout=max(0.001, deadline - time.monotonic()))


def run_process(argv, cwd, log, deadline, seconds=30, cap=1024 * 1024, *, env=None):
    start = time.monotonic()
    result = {"status": "FAIL", "reason": None, "exit_code": None, "argv": argv,
              "started_at": utc(), "finished_at": None, "duration_ms": None,
              "log": str(log), "log_bytes": 0, "log_truncated": False}
    proc = None
    pending = []
    # Latch rather than raise across Popen's creation/ownership handoff and cleanup.
    # No signal mask is inherited by the child; exec resets these handlers.
    def latch(signum, _frame):
        if not pending:
            pending.append((signum, result["reason"]))
    handlers = {s: signal.signal(s, latch)
                for s in (signal.SIGINT, signal.SIGTERM, signal.SIGALRM)}
    def checkpoint():
        if pending:
            if pending[0][0] == signal.SIGALRM:
                raise TimedOut()
            raise Stopped(pending[0][0])
    try:
        with open(log, "xb") as stream, selectors.DefaultSelector() as selector:
            child_env = dict(OPTIONS if env is None else env)
            if env is not None:
                result["popen_env"] = child_env.copy()
            proc = subprocess.Popen(argv, cwd=cwd, env=child_env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
            checkpoint()
            os.set_blocking(proc.stdout.fileno(), False)
            selector.register(proc.stdout, selectors.EVENT_READ)
            until = min(deadline, start + seconds)
            while selector.get_map():
                checkpoint()
                if time.monotonic() >= until:
                    result["reason"] = "TIMEOUT"
                    break
                for key, _ in selector.select(min(0.05, max(0, until - time.monotonic()))):
                    data = os.read(key.fd, 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    remaining = cap - result["log_bytes"]
                    stream.write(data[:remaining])
                    result["log_bytes"] += min(len(data), remaining)
                    if len(data) > remaining:
                        result.update(reason="LOG_LIMIT", log_truncated=True)
                        break
                if result["reason"]:
                    break
            if result["reason"] is None:
                try:
                    while proc.poll() is None:
                        checkpoint()
                        if time.monotonic() >= until:
                            raise subprocess.TimeoutExpired(argv, seconds)
                        time.sleep(min(.05, max(0, until - time.monotonic())))
                    checkpoint()
                    code = proc.returncode
                    result.update(status="PASS" if code == 0 else "FAIL", reason=None if code == 0 else "EXIT_NONZERO")
                except subprocess.TimeoutExpired:
                    result["reason"] = "TIMEOUT"
    except Stopped as exc:
        result.update(status="CANCELLED", reason=f"SIGNAL_{exc.signum}", signal=exc.signum)
    except TimedOut:
        result["reason"] = "TIMEOUT"
    except Exception as exc:
        if result["reason"] is None:
            result["reason"] = f"PROCESS_ERROR: {type(exc).__name__}: {exc}"
        else:
            result["cleanup_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        def cleanup_failure(exc):
            result["cleanup_error"] = f"{type(exc).__name__}: {exc}"
            if result["reason"] is None:
                result.update(status="FAIL", reason="CLEANUP_ERROR")
        try:
            if proc is not None:
                try:
                    close_group(proc, time.monotonic() + LIMITS["close_seconds"])
                except (Exception, Stopped, TimedOut) as exc:
                    cleanup_failure(exc)
                result["exit_code"] = proc.returncode
                try:
                    proc.stdout.close()
                except (Exception, Stopped, TimedOut) as exc:
                    cleanup_failure(exc)
        finally:
            for s, handler in handlers.items():
                signal.signal(s, handler)
        # First stop during normal close is still a stop, even if close also failed.
        # A prior stop/timeout retains precedence over all secondary close errors.
        if pending and pending[0][1] not in ("TIMEOUT", "LOG_LIMIT") and result["status"] != "CANCELLED":
            if pending[0][0] == signal.SIGALRM:
                result.update(status="FAIL", reason="TIMEOUT")
            else:
                result.update(status="CANCELLED", reason=f"SIGNAL_{pending[0][0]}", signal=pending[0][0])
        result.update(finished_at=utc(), duration_ms=int((time.monotonic() - start) * 1000))
    return result


def persist(output, inputs, result):
    for name, value in (("inputs.json", inputs), ("result.json", result)):
        data = encoded(value)
        path = output / name
        with open(path, "xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != data:
            raise OSError(f"readback mismatch: {name}")
    fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return digest(encoded(result))


def deliver(output, inputs, result, code):
    try:
        sha = persist(output, inputs, result)
    except (Exception, Stopped, TimedOut) as exc:
        print(f"result persistence failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        if code in (130, 143):
            return code
        return 128 + exc.signum if isinstance(exc, Stopped) else 1
    print(json.dumps({"result": str(output / 'result.json'), "sha256": sha,
                      "status": result["overall_status"], "exit_code": code}))
    return code


# Planner identities are caller declarations, never execution receipts.
PLAN_IDS = ("document_review", "proxy_smoke", "proxy_regression",
            "capture_integration", "native_policy")
DIMENSIONS = ("source", "contract", "test", "fixture", "argv", "env", "dependency")
PROXY = "experiments/a_share_ingestion/proxy.py"
CAPTURE_PATHS = (
    "experiments/a_share_ingestion/retro_capture_v1.py",
    "experiments/a_share_price_volume_retro_inputs_v1.py",
    "experiments/a_share_price_volume_retro_resources_v1.py",
    "experiments/run_a_share_price_volume_retro_real_v1.py")
SMOKE_NODES = tuple("tests/research/test_a_share_ingestion_proxy.py::" + name for name in (
    "test_unapproved_endpoint_rejected",
    "test_failure_redacted_no_retry_no_failover_no_refund",
    "test_capture_retains_exact_safe_bytes_without_pandas_or_second_request"))
SCOPE_CAP = 65536
OUTPUT_CAP = 262144


def _invalid():
    raise Blocked("invalid scope declaration")


def _shape(value, allowed, required=()):
    if type(value) is not dict or set(value) - set(allowed) or set(required) - set(value):
        _invalid()


def _path(value):
    if (type(value) is not str or not 0 < len(value) <= 256
            or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/" for c in value)
            or any(p in ("", ".", "..") for p in value.split("/"))):
        _invalid()


def _hash(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        _invalid()


def _checks(value):
    _shape(value, PLAN_IDS)
    for identity in value.values():
        _shape(identity, DIMENSIONS)
        for dim, item in identity.items():
            if item is None:
                continue
            if dim == "argv":
                if (type(item) is not list or len(item) > 64
                        or any(type(s) is not str or len(s) > 1024 for s in item)):
                    _invalid()
            else:
                _hash(item)


def _manifest(value):
    _shape(value, ("files", "checks"), ("files", "checks"))
    files = value["files"]
    if type(files) is not dict or len(files) > 64:
        _invalid()
    for path, sha in files.items():
        _path(path)
        _hash(sha)
    _checks(value["checks"])


def compare_evidence(old, current):
    """Compare check declarations only; even complete agreement never permits reuse."""
    _checks(old)
    _checks(current)
    result = {}
    for name in PLAN_IDS:
        before, after = old.get(name, {}), current.get(name, {})
        different = [d for d in DIMENSIONS if before.get(d) is not None
                     and after.get(d) is not None and before[d] != after[d]]
        missing = [d for d in DIMENSIONS if before.get(d) is None or after.get(d) is None]
        result[name] = {"state": "INVALIDATED" if different else
                        "UNKNOWN" if missing else "UNCHANGED_DECLARED",
                        "changed_dimensions": different, "missing_dimensions": missing,
                        "identity_trust": "UNVERIFIED", "reuse_allowed": False}
    return result


def _normative(path):
    parts = path.split("/")
    return (parts[-1].upper() in ("CONTEXT.MD", "AGENTS.MD", "CLAUDE.MD")
            or parts[0] in ("implementation", "overall")
            or any(p.lower() in ("adr", "adrs") for p in parts[:-1])
            or path.startswith("docs/agents/"))


def build_plan(scope):
    """Build obligations from bounded caller declarations, without target file I/O."""
    fields = ("schema_version", "changes", "previous_manifest", "current_manifest")
    _shape(scope, fields, fields)
    if type(scope["schema_version"]) is not int or scope["schema_version"] != 1:
        _invalid()
    changes = scope["changes"]
    if type(changes) is not list or not 0 < len(changes) <= 64:
        _invalid()
    for key in ("previous_manifest", "current_manifest"):
        _manifest(scope[key])
    selected, seen, unmodeled = set(), set(), []
    for change in changes:
        _shape(change, ("path", "role", "review_basis"), ("path", "role", "review_basis"))
        path, role, basis = change["path"], change["role"], change["review_basis"]
        _path(path)
        if (path in seen or type(role) is not str or role not in
                ("informational", "local", "public", "authority", "dependency", "fixture", "unknown")
                or type(basis) is not str or len(basis) > 256):
            _invalid()
        seen.add(path)
        known = False
        if path == PROXY:
            selected.update(PLAN_IDS[1:4])
            known = role == "local"
        if path in CAPTURE_PATHS or role == "authority":
            selected.update(PLAN_IDS[1:])
            known = role in ("public", "authority")
        if role == "informational" and path.endswith(".md") and not _normative(path) and basis.strip():
            selected.add(PLAN_IDS[0])
            known = True
        if not known or role in ("dependency", "fixture", "unknown"):
            unmodeled.append({"path": path, "reason": "unmodeled_scope_or_role_mismatch"})
    comparisons = compare_evidence(scope["previous_manifest"]["checks"], scope["current_manifest"]["checks"])
    prefix = [str(ROOT / ".venv/bin/python"), "-I", "-B", "-m", "pytest", "-c",
              str(ROOT / "pyproject.toml"), f"--confcutdir={ROOT / 'tests/research'}",
              "-p", "no:cacheprovider", "-q"]
    commands = {"proxy_smoke": prefix + list(SMOKE_NODES),
                "proxy_regression": prefix + ["tests/research/test_a_share_ingestion_proxy.py"],
                "capture_integration": prefix + ["tests/research/test_a_share_retro_capture_v1.py"]}
    # Availability of a fixed guarded entry is not runtime qualification or PASS.
    blocks = {"native_policy": "no_native_authorization"}
    checks = []
    for name in PLAN_IDS:
        if name not in selected:
            continue
        argv = commands.get(name)
        checks.append({"id": name, "execution_status": "BLOCKED" if name in blocks else "NOT_RUN",
                       "exit_code": None, "duration_ms": None, "intended_argv": argv,
                       "manual_obligation": "review_links_and_declarations" if name == PLAN_IDS[0]
                       else "separate_native_authorization_and_validation" if name == PLAN_IDS[-1] else None,
                       "blocked_reasons": [blocks[name]] if name in blocks else [],
                       "identity_comparison": comparisons[name],
                       "declared_argv_matches_intended": None if argv is None else
                       scope["current_manifest"]["checks"].get(name, {}).get("argv") == argv})
    return {"schema_version": 1, "profile": "plan", "artifact_kind": "validation_plan",
            "plan_status": "GENERATED", "overall_status": "BLOCKED" if unmodeled or
            any(c["execution_status"] == "BLOCKED" for c in checks) else "NOT_RUN",
            "verification_passed": False, "reuse_allowed": False,
            "scope_completeness": "DECLARED_ONLY", "identity_trust": "UNVERIFIED",
            "unmodeled_scope": unmodeled, "checks": checks,
            "offline_execution_entry": None if not selected.intersection(PLAN_IDS[1:4]) else {
                "profile": "offline-pc", "covers": list(PLAN_IDS[1:4]),
                "argv_template": [str(ROOT / ".venv/bin/python"), "-I", "-B",
                    str(ROOT / "tools/validate_change.py"), "--profile", "offline-pc",
                    "--output", "<EXCLUSIVE_OUTPUT>"],
                "cwd": str(ROOT), "automatic_execution": False},
            "previous_manifest": json.loads(json.dumps(scope["previous_manifest"])),
            "current_manifest": json.loads(json.dumps(scope["current_manifest"]))}


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _invalid()
        value[key] = item
    return value


def _read_scope(path):
    no_symlinks(path)
    # Nonblocking open prevents a synthetic FIFO from hanging before fstat.
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            _invalid()
        data = stream.read(SCOPE_CAP + 1)
    if len(data) > SCOPE_CAP:
        _invalid()
    return json.loads(data, object_pairs_hook=_unique_object)


def _persist_plan(output, scope, plan):
    values = (("scope.json", encoded(scope)), ("plan.json", encoded(plan)))
    if sum(len(data) for _, data in values) > OUTPUT_CAP:
        raise Blocked("plan output limit")
    for name, data in values:
        path = output / name
        with open(path, "xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != data:
            raise Blocked("plan readback failure")
    fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return digest(values[1][1])


def _plan_main(args):
    def stop(signum, _frame):
        raise Stopped(signum)
    handlers = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        if args.scope is None:
            _invalid()
        source = Path(os.path.abspath(args.scope))
        output = Path(os.path.abspath(args.output))
        if source == output or source in output.parents or output in source.parents:
            raise Blocked("input/output overlap")
        scope = _read_scope(source)
        plan = build_plan(scope)
        declared = {change["path"] for change in scope["changes"]}
        for name in ("previous_manifest", "current_manifest"):
            declared.update(scope[name]["files"])
        for relative in declared:
            target = ROOT / relative
            if output == target or output in target.parents or target in output.parents:
                raise Blocked("input/output overlap")
        output = prepare_output(ROOT, output)
        sha = _persist_plan(output, scope, plan)
        code = 2 if plan["overall_status"] == "BLOCKED" else 3
        print(json.dumps({"plan": str(output / "plan.json"), "sha256": sha,
                          "status": plan["overall_status"], "exit_code": code}))
        return code
    except Stopped as exc:
        return 128 + exc.signum
    except Exception:
        # Do not echo untrusted paths, JSON, reasons, or exception details.
        print("plan input/output error", file=sys.stderr)
        return 1
    finally:
        for s, handler in handlers.items():
            signal.signal(s, handler)


def _load_offline_pc():
    spec = importlib.util.spec_from_file_location("validation_offline_pc", ROOT / "tools/validation_offline_pc.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _offline_pc_main(args):
    try:
        pc = _load_offline_pc()
    except Exception:
        print("offline-pc entry unavailable", file=sys.stderr)
        return 2
    started, wall = time.monotonic(), utc()
    output, before, after, coverage = None, None, None, None
    checks = [{"id": name, "status": "NOT_RUN", "exit_code": None, "argv": [], "reason": None,
               "duration_ms": None, "started_at": None, "finished_at": None}
              for name in ("environment", "offline_pc_contract")]
    status, reason, code = "BLOCKED", None, 2
    def stop(signum, _frame):
        raise Stopped(signum)
    def timeout(_signum, _frame):
        raise TimedOut()
    handlers = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
    handlers[signal.SIGALRM] = signal.signal(signal.SIGALRM, timeout)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, pc.LIMITS["preflight_seconds"])
    try:
        try:
            candidate = Path(os.path.abspath(args.output))
            if candidate == ROOT or ROOT in candidate.parents or candidate in ROOT.parents:
                raise Blocked("output must be outside project")
            output = prepare_output(ROOT, candidate)
            checks[0]["started_at"] = utc()
            before = pc.snapshot_pc(ROOT, environment(ROOT))
            checks[0].update(status="PASS", finished_at=utc(),
                             duration_ms=int((time.monotonic() - started) * 1000))
            deadline = started + pc.LIMITS["total_seconds"] - pc.LIMITS["close_seconds"]
            signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - time.monotonic()))
            argv = pc.argv_for_pc(ROOT, output)
            checks[1].update(run_process(argv, ROOT, output / "offline_pc.log", deadline,
                pc.LIMITS["child_seconds"], pc.LIMITS["log_bytes"], env=pc.clean_env()))
            process = dict(checks[1])
            checks[1]["process_result"] = process
            if process["status"] == "CANCELLED":
                raise Stopped(process["signal"])
            if process["reason"] in ("TIMEOUT", "LOG_LIMIT"):
                status, reason, code = "FAIL", process["reason"], 1
            else:
                try:
                    after = pc.snapshot_pc(ROOT, environment(ROOT))
                except Exception as exc:
                    detail = str(exc) if isinstance(exc, pc.QualificationError) else type(exc).__name__
                    checks[1]["secondary_reasons"] = ["AFTER_SNAPSHOT: " + detail]
                if process["status"] != "PASS" or process["exit_code"] != 0:
                    raise pc.QualificationError(process["reason"] or "CHILD_PROCESS_FAILED")
                report = pc.read_child_report(output)
                coverage = pc.validate_pc(process, report, before, after, argv)
                status, reason, code = "PASS", None, 0
        except Stopped as exc:
            status, reason, code = "CANCELLED", f"SIGNAL_{exc.signum}", 128 + exc.signum
        except TimedOut:
            status, reason, code = "FAIL", "TIMEOUT", 1
        except Exception as exc:
            status, code = ("BLOCKED", 2) if before is None else ("FAIL", 1)
            reason = str(exc) if isinstance(exc, pc.QualificationError) else type(exc).__name__
        if status != "PASS":
            target = checks[0] if before is None else checks[1]
            if target["started_at"] is not None or before is not None:
                target.update(status=status, reason=reason, finished_at=utc())
        signal.setitimer(signal.ITIMER_REAL, max(.001, started + pc.LIMITS["total_seconds"] - time.monotonic()))
        if code in (130, 143):
            for s in (signal.SIGINT, signal.SIGTERM):
                signal.signal(s, signal.SIG_IGN)
        result = {"schema_version": 1, "profile": "offline-pc", "identity_scope": "offline-pc-inputs-v1",
            "input_manifest": "inputs.json", "input_before_sha256": digest(encoded(before)) if before else None,
            "input_after_sha256": digest(encoded(after)) if after else None, "overall_status": status,
            "verification_passed": status == "PASS", "reason": reason, "checks": checks, "coverage": coverage,
            "qualification_limits": pc.QUALIFICATION_LIMITS, "source_qualified": False, "native_authorized": False,
            "reuse_allowed": False, "started_at": wall, "finished_at": utc(),
            "duration_ms": int((time.monotonic() - started) * 1000)}
        if output is None:
            print("offline-pc output unavailable", file=sys.stderr)
            return code
        try:
            return deliver(output, {"before": before, "after": after}, result, code)
        except (Stopped, TimedOut) as exc:
            return code if code in (130, 143) else 128 + exc.signum if isinstance(exc, Stopped) else 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        for s, handler in handlers.items():
            signal.signal(s, handler)


class _Arguments(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default diagnostic echoes raw caller-controlled arguments.
        raise Blocked("invalid command arguments")


def main(argv=None):
    # Match argparse's profile syntax and last-value-wins policy, without help
    # or validation of unrelated arguments in this classification-only pass.
    profile_parser = _Arguments(add_help=False)
    profile_parser.add_argument("--profile", nargs="?", const=argparse.SUPPRESS)
    profile_hint = argparse.Namespace(profile=None)
    try:
        profile_parser.parse_known_args(argv, namespace=profile_hint)
    except Blocked:
        pass
    requested_profile = profile_hint.profile
    parser = _Arguments(description=__doc__)
    parser.add_argument("--profile", required=True, choices=["self", "plan", "offline-pc"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--scope")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 1 if requested_profile == "plan" else int(exc.code)
    except Blocked:
        print("invalid command arguments", file=sys.stderr)
        return 1 if requested_profile == "plan" else 2
    if args.profile == "plan":
        return _plan_main(args)
    if args.profile == "offline-pc":
        if args.scope is not None:
            print("offline-pc does not accept scope", file=sys.stderr)
            return 2
        return _offline_pc_main(args)
    if args.scope is not None:
        print("self does not accept scope", file=sys.stderr)
        return 2
    started, wall = time.monotonic(), utc()
    output, before, after = None, None, None
    checks = blank_checks(ROOT)
    status, reason, code = "BLOCKED", None, 2
    def stop(signum, _frame):
        raise Stopped(signum)
    handlers = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
    def timeout(_signum, _frame):
        raise TimedOut()
    handlers[signal.SIGALRM] = signal.signal(signal.SIGALRM, timeout)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, LIMITS["check_seconds"])
    try:
        output = prepare_output(ROOT, args.output)
        t = time.monotonic()
        checks[0]["started_at"] = utc()
        before = snapshot(ROOT)
        checks[0].update(status="PASS", finished_at=utc(), duration_ms=int((time.monotonic() - t) * 1000))
        signal.setitimer(signal.ITIMER_REAL, max(.001, started + LIMITS["total_seconds"] - LIMITS["close_seconds"] - time.monotonic()))
        checks[1].update(run_process(argv_for(ROOT), ROOT, output / "validator_contract.log",
                                    started + LIMITS["total_seconds"] - LIMITS["close_seconds"],
                                    LIMITS["check_seconds"], LIMITS["log_bytes"]))
        if checks[1]["status"] == "CANCELLED":
            raise Stopped(checks[1]["signal"])
        if checks[1]["reason"] not in ("TIMEOUT", "LOG_LIMIT"):
            signal.setitimer(signal.ITIMER_REAL, max(.001, min(LIMITS["check_seconds"], started + LIMITS["total_seconds"] - LIMITS["close_seconds"] - time.monotonic())))
            after = snapshot(ROOT)
        status, reason, code = aggregate(checks, before, after)
        if checks[1]["reason"] in ("TIMEOUT", "LOG_LIMIT"):
            reason = checks[1]["reason"]
        if time.monotonic() - started >= LIMITS["total_seconds"] - LIMITS["close_seconds"]:
            status, reason, code = "FAIL", "TIMEOUT", 1
    except Stopped as exc:
        status, reason, code = "CANCELLED", f"SIGNAL_{exc.signum}", 128 + exc.signum
        for c in checks:
            if c["started_at"] and c["status"] == "NOT_RUN":
                c.update(status="CANCELLED", reason=reason, finished_at=utc(),
                         duration_ms=int((time.monotonic() - started) * 1000))
    except TimedOut:
        status, reason, code = "FAIL", "TIMEOUT", 1
        for c in checks:
            if c["started_at"] and c["status"] == "NOT_RUN":
                c.update(status="FAIL", reason=reason, finished_at=utc(),
                         duration_ms=int((time.monotonic() - started) * 1000))
    except Exception as exc:
        status = "BLOCKED" if before is None else "FAIL"
        code = 2 if before is None else 1
        reason = f"{type(exc).__name__}: {exc}"
        if before is None:
            checks[0].update(status="BLOCKED", reason=reason, finished_at=utc(),
                             duration_ms=int((time.monotonic() - started) * 1000))
    finally:
        signal.setitimer(signal.ITIMER_REAL, max(.001, started + LIMITS["total_seconds"] - time.monotonic()))
        if code in (130, 143):
            # The original stop reason wins over repeated stops during close.
            for s in (signal.SIGINT, signal.SIGTERM):
                signal.signal(s, signal.SIG_IGN)
    try:
        result = {"schema_version": 1, "profile": "self", "identity_scope": "self-inputs-v1",
                  "input_manifest": "inputs.json", "input_before_sha256": digest(encoded(before)) if before else None,
                  "input_after_sha256": digest(encoded(after)) if after else None,
                  "overall_status": status, "reason": reason, "checks": checks,
                  "started_at": wall, "finished_at": utc(), "duration_ms": int((time.monotonic() - started) * 1000)}
        if output is None:
            print(reason, file=sys.stderr)
            return code
        return deliver(output, {"before": before, "after": after}, result, code)
    except (Stopped, TimedOut) as exc:
        if code in (130, 143):
            return code
        return 128 + exc.signum if isinstance(exc, Stopped) else 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        for s, handler in handlers.items():
            signal.signal(s, handler)


if __name__ == "__main__":
    # Only the real CLI may replace its process; internal main callers stay local.
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        entry = ROOT / ".venv/bin/python"
        try:
            os.execve(entry, [str(entry), "-I", "-B", str(ROOT / "tools/validate_change.py"),
                              *sys.argv[1:]], dict(OPTIONS))
        except OSError as exc:
            print(f"isolated project interpreter unavailable: {exc}", file=sys.stderr)
            sys.exit(2)
    sys.exit(main())
