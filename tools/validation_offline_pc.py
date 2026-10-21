"""Fixed fake P/C verification. Audit hooks are not an OS sandbox."""
from __future__ import annotations

import argparse
import contextvars
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ("tests/research/test_a_share_ingestion_proxy.py",
         "tests/research/test_a_share_retro_capture_v1.py")
COVERS = ("proxy_smoke", "proxy_regression", "capture_integration")
LIMITS = {"preflight_seconds": 30, "child_seconds": 60, "total_seconds": 120,
          "close_seconds": 10, "log_bytes": 2 * 1024 * 1024, "report_bytes": 2 * 1024 * 1024,
          "source_file_bytes": 2 * 1024 * 1024, "snapshot_bytes": 32 * 1024 * 1024}
PINS = {
    FILES[0]: "e74298c88d9e0ec2088a86ba6a374664c266c173ef3ce574e7842d838966c2ba",
    FILES[1]: "8b8f6f812abc574c48eb1bc610b13e0ef62c4bb6ddf3f3c369679e51564b66fc",
    "tests/research/conftest.py": "385b36bb23043a5d5439287f52f130ebd7289a6eda5add3be8c182d54d2a3456",
    "pyproject.toml": "c33c31e91a80ca5c56b1b5ccf1356c18dd8deff28ca07a0605a15448182e0aab",
    "uv.lock": "77e015a4b69f4bce62f61170dc80201a0abee51fd2b4e507819cfd0f4d8a3e5f"}
VERSIONS = {"crypto-quant-domain": "0.1.0", "crypto-quant-foundation": "0.1.0",
            "crypto-quant-research": "0.1.0", "crypto-quant-validation": "0.1.0",
            "pytest": "8.4.2", "packaging": "26.3", "pandas": "3.0.6", "numpy": "2.5.3",
            "iniconfig": "2.3.0", "pluggy": "1.6.0", "pygments": "2.20.0",
            "python-dateutil": "2.9.0.post0", "six": "1.17.0"}
MODULE_GROUPS = {
    "crypto_quant_domain": ("", "accounting", "artifacts", "canonical", "decisions", "execution",
        "identity", "instruments", "numeric", "numeric.quantization", "numeric.rounding",
        "numeric.scales", "numeric.values", "profile_errors", "time"),
    "crypto_quant_foundation": ("", "storage"),
    "crypto_quant_research": ("", "declarations", "integration", "retrospective_study", "statistical_study"),
    "crypto_quant_validation": ("", "integration", "ledger", "paired_portfolio_comparison_v1",
        "paired_portfolio_oos_draft_v0", "retrospective_reservation", "runtime", "sample_consumption",
        "statistical_reservation", "target_runtime"),
    "experiments": ("", "a_share_ingestion", "a_share_ingestion.__main__", "a_share_ingestion.daily",
        "a_share_ingestion.industry", "a_share_ingestion.proxy", "a_share_ingestion.retro_capture_v1",
        "a_share_ingestion.runtime", "a_share_price_volume_research_v1", "a_share_price_volume_retro_inputs_v1",
        "a_share_price_volume_retro_resources_v1", "a_share_price_volume_retro_v1",
        "run_a_share_price_volume_retro_real_v1", "run_a_share_price_volume_retro_v1")}
REPORT_KEYS = {"schema_version", "profile", "argv", "cwd", "before", "after", "env_before", "env_after",
               "guard_selftest", "unexpected_guard_events", "collection", "reports", "pytest_exit",
               "post_only_modules", "error"}
QUALIFICATION_LIMITS = ["Python audit hooks, not OS isolation", "metadata, not complete installed-code authentication",
    "before/after hashes do not detect a restored intervening modification", "no native/data/model authority",
    "thread environment requests, not measured BLAS threads or CPU quota", "no automatic proof reuse"]


class QualificationError(Exception):
    pass


def clean_env():
    return {"PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}


def argv_for_pc(root, output):
    return [str(root / ".venv/bin/python"), "-I", "-B", "-X",
            f"pycache_prefix={output / 'child/bytecode'}", str(root / "tools/validation_offline_pc.py"),
            "--child-output", str(output / "child")]


def module_paths(root):
    bases = {"crypto_quant_domain": root / f".venv/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/crypto_quant_domain",
             "crypto_quant_foundation": root / "foundation/src/crypto_quant_foundation",
             "crypto_quant_research": root / "research-platform/src/crypto_quant_research",
             "crypto_quant_validation": root / "strategy-validation/src/crypto_quant_validation",
             "experiments": root / "experiments"}
    result = {}
    for package, tails in MODULE_GROUPS.items():
        for tail in tails:
            relative = Path(*tail.split(".")) if tail else Path()
            path = bases[package] / relative
            if not tail or tail in ("numeric", "a_share_ingestion"):
                path /= "__init__.py"
            else:
                path = path.with_suffix(".py")
            result[package + ("." + tail if tail else "")] = path
    return result


class Reader:
    def __init__(self):
        self.bytes = 0

    def identity(self, path):
        path = Path(path).absolute()
        for part in (path, *path.parents):
            if part.is_symlink():
                raise QualificationError("INPUT_SYMLINK")
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > LIMITS["source_file_bytes"]:
                raise QualificationError("INPUT_TYPE_OR_SIZE")
            data = stream.read(LIMITS["source_file_bytes"] + 1)
            after = os.fstat(stream.fileno())
        self.bytes += len(data)
        if (len(data) > LIMITS["source_file_bytes"] or self.bytes > LIMITS["snapshot_bytes"]
                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise QualificationError("INPUT_CHANGED_OR_LIMIT")
        return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def distribution_snapshot(reader):
    from packaging.requirements import Requirement
    pending = [Requirement(n + "==" + VERSIONS[n]) for n in
               ("pytest", "packaging", "pandas", "numpy", "crypto-quant-domain",
                "crypto-quant-foundation", "crypto-quant-research", "crypto-quant-validation")]
    found = {}
    while pending:
        req = pending.pop()
        if req.marker and not req.marker.evaluate({"extra": ""}):
            continue
        dist = metadata.distribution(req.name)
        name = dist.metadata["Name"].lower().replace("_", "-")
        if name not in VERSIONS or dist.version != VERSIONS[name] or not req.specifier.contains(dist.version):
            raise QualificationError("DEPENDENCY_QUALIFICATION_CHANGED")
        if name in found:
            continue
        files = list(dist.files or ())
        hashes = {}
        for leaf in ("METADATA", "RECORD"):
            matches = [p for p in files if p.name == leaf and p.parent.name.endswith(".dist-info")]
            if len(matches) != 1:
                raise QualificationError("DEPENDENCY_METADATA_AMBIGUOUS")
            hashes[leaf] = reader.identity(dist.locate_file(matches[0]))
        found[name] = {"version": dist.version, "metadata": hashes}
        pending.extend(Requirement(s) for s in dist.requires or ())
    if set(found) != set(VERSIONS):
        raise QualificationError("DEPENDENCY_CLOSURE_CHANGED")
    return dict(sorted(found.items()))


def snapshot_pc(root, runtime):
    reader = Reader()
    paths = {str(p.relative_to(root)) for p in module_paths(root).values()}
    paths.update(PINS)
    paths.update(("tools/validate_change.py", "tools/validation_offline_pc.py"))
    files = {rel: reader.identity(root / rel) for rel in sorted(paths)}
    if any(files[rel]["sha256"] != expected for rel, expected in PINS.items()):
        raise QualificationError("FIXTURE_OR_CONFIG_QUALIFICATION_CHANGED")
    return {"schema_version": 1, "identity_scope": "offline-pc-inputs-v1", "files": files,
            "runtime": runtime, "distributions": distribution_snapshot(reader), "env": clean_env(),
            "argv_template": argv_for_pc(root, Path("<EXCLUSIVE_OUTPUT>")), "cwd": str(root),
            "limits": LIMITS, "coverage_contract": "98-all-phases-S4/4/1-v1",
            "guard_contract": "fixed-pc-audit-v1", "exclusions": ["output", "logs", "fixtures", "bytecode"]}


def observed_env():
    keys = set(clean_env()) | {"LC_CTYPE"}
    values = {k: os.environ[k] for k in sorted(keys) if k in os.environ}
    return {"safe_values": values, "unexpected_key_count": len(set(os.environ) - keys)}


def valid_env(value):
    if type(value) is not dict or set(value) != {"safe_values", "unexpected_key_count"}:
        return False
    values = value["safe_values"]
    return (type(values) is dict and set(values) in (set(clean_env()), set(clean_env()) | {"LC_CTYPE"})
            and all(values.get(k) == v for k, v in clean_env().items())
            and values.get("LC_CTYPE") in (None, "C.UTF-8", "C.utf8")
            and type(value["unexpected_key_count"]) is int and value["unexpected_key_count"] == 0)


class Guard:
    """Inspect Python audit events only. Already-open fd/native bypasses are not isolated."""
    def __init__(self, root, child, sources):
        self.root, self.child = str(root), str(child)
        self.sources = {str(p) for p in sources}
        self.domain_root = str(module_paths(root)["crypto_quant_domain"].parent)
        self.events, self.synthetic = [], False
        self.fd_path = contextvars.ContextVar("offline_pc_fd_path", default=None)
        self.lib_roots = tuple(str(Path(p).resolve()) for p in
            (sys.base_prefix, root / ".venv", Path(__file__).parent))

    def path(self, value, dir_fd=None):
        if isinstance(value, int):
            return os.path.realpath(f"/proc/self/fd/{value}")
        value = os.fsdecode(value)
        if not os.path.isabs(value) and isinstance(dir_fd, int) and dir_fd >= 0:
            value = os.path.join(os.readlink(f"/proc/self/fd/{dir_fd}"), value)
        return os.path.abspath(value)

    @staticmethod
    def inside(path, root):
        return path == root or path.startswith(root + os.sep)

    def check(self, path, write=False):
        real = os.path.realpath(path)
        # pytest capture owns this fixed OS sink; never generalize to /dev/*.
        if path == real == "/dev/null":
            return None
        forbidden = ("/srv", "/home/ygguo/.config/ai-crypt", "/home/ygguo/.pi/agent/auth.json",
                     self.root + "/research/evidence", self.root + "/backtest/evidence")
        if any(self.inside(p, f) for p in (path, real) for f in forbidden) or Path(path).name == "xiaodefa-token":
            return "SOURCE_OR_CREDENTIAL_FORBIDDEN"
        if write:
            return None if self.inside(path, self.child) and self.inside(real, self.child) else "WRITE_OUTSIDE_FIXTURES"
        if self.inside(path, self.child) and self.inside(real, self.child):
            return None
        # Project source is finite, including editable SDKs outside site-packages.
        if ((self.inside(path, self.root) and not self.inside(path, self.root + "/.venv"))
                or self.inside(path, self.domain_root)):
            return None if path in self.sources and real == path else "INPUT_CLOSURE_UNREVIEWED"
        if (any(self.inside(real, p) for p in self.lib_roots) or real.startswith("/usr/share/zoneinfo/")
                or real in ("/etc/localtime", "/etc/timezone", "/etc/os-release")):
            return None
        return "READ_OUTSIDE_INPUTS"

    def audit(self, event, values):
        reason = None
        if event in {"socket.connect", "socket.connect_ex", "socket.sendto", "socket.getaddrinfo"}:
            reason = "NETWORK_FORBIDDEN"
        elif event in {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.fork", "os.forkpty"}:
            reason = "PROCESS_LAUNCH_FORBIDDEN"
        elif event == "sqlite3.connect":
            reason = "DB_FORBIDDEN"
        elif event == "open" and values:
            flags = values[2] if len(values) > 2 and isinstance(values[2], int) else 0
            write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            path = self.fd_path.get() or self.path(values[0])
            # Secure token/source readers walk ancestor directory fds. Opening a
            # directory handle is not permission to read an arbitrary child file.
            directory_handle = (not write and bool(flags & os.O_DIRECTORY)
                and os.path.realpath(path) == path
                and any(self.inside(target, path) or path == os.sep
                        for target in self.sources | {self.child}))
            reason = None if directory_handle else self.check(path, write)
        elif event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.utime", "os.truncate"}:
            index = 2 if event in {"os.mkdir", "os.chmod"} else 3 if event == "os.utime" else 1
            fd = values[index] if len(values) > index else None
            reason = self.check(self.path(values[0], fd), True)
        elif event in {"os.rename", "os.link", "os.symlink"}:
            srcfd = values[2] if len(values) > 2 else None
            dstfd = values[3] if len(values) > 3 else None
            if event != "os.symlink":
                reason = self.check(self.path(values[0], srcfd), True)
            reason = reason or self.check(self.path(values[1], dstfd), True)
        elif event in {"os.listdir", "os.scandir"} and values:
            path = self.path(values[0])
            if any(self.inside(path, p) for p in ("/srv", self.root + "/research/evidence", self.root + "/backtest/evidence")):
                reason = "SOURCE_DIRECTORY_FORBIDDEN"
        if reason:
            self.events.append({"event": event, "reason": reason, "synthetic": self.synthetic})
            raise OSError(reason)

    def install(self):
        original = os.open
        def fd_open(path, flags, mode=0o777, *, dir_fd=None):
            token = self.fd_path.set(self.path(path, dir_fd))
            try:
                return original(path, flags, mode, dir_fd=dir_fd)
            finally:
                self.fd_path.reset(token)
        os.open = fd_open
        sys.addaudithook(self.audit)

    def selftest(self):
        self.synthetic = True
        try:
            for event, values in (("socket.connect", (None, ("synthetic.invalid", 0))),
                                  ("subprocess.Popen", ("synthetic", [], None, None)),
                                  ("open", ("/srv/synthetic-never-opened", "r", 0))):
                try:
                    sys.audit(event, *values)
                except OSError:
                    pass
                else:
                    raise QualificationError("GUARD_SELFTEST_FAILED")
        finally:
            self.synthetic = False
        if len(self.events) != 3:
            raise QualificationError("GUARD_SELFTEST_FAILED")


class CoveragePlugin:
    def __init__(self):
        self.collection = {"nodes": [], "errors": 0, "deselected": 0}
        self.reports = []

    def pytest_collection_finish(self, session):
        self.collection["nodes"] = [item.nodeid for item in session.items]

    def pytest_collectreport(self, report):
        self.collection["errors"] += int(report.failed)

    def pytest_deselected(self, items):
        self.collection["deselected"] += len(items)

    def pytest_runtest_logreport(self, report):
        self.reports.append({"nodeid": report.nodeid, "when": report.when,
                             "outcome": report.outcome, "wasxfail": hasattr(report, "wasxfail")})


def coverage_for(collection, reports):
    if type(collection) is not dict or set(collection) != {"nodes", "errors", "deselected"}:
        raise QualificationError("INVALID_COVERAGE")
    nodes = collection["nodes"]
    if (type(nodes) is not list or len(nodes) != 98 or any(type(n) is not str for n in nodes)
            or len(set(nodes)) != 98 or type(collection["errors"]) is not int or collection["errors"] != 0
            or type(collection["deselected"]) is not int or collection["deselected"] != 0):
        raise QualificationError("INCOMPLETE_COLLECTION")
    if set(n.split("::")[0] for n in nodes) != set(FILES):
        raise QualificationError("UNREVIEWED_COLLECTION")
    phases = {n: [] for n in nodes}
    if type(reports) is not list:
        raise QualificationError("INVALID_REPORTS")
    for row in reports:
        if (type(row) is not dict or set(row) != {"nodeid", "when", "outcome", "wasxfail"}
                or type(row["nodeid"]) is not str or row["nodeid"] not in phases
                or row["when"] not in ("setup", "call", "teardown") or row["outcome"] != "passed"
                or row["wasxfail"] is not False):
            raise QualificationError("INCOMPLETE_PASS_REPORTS")
        phases[row["nodeid"]].append(row["when"])
    if any(sorted(rows) != ["call", "setup", "teardown"] for rows in phases.values()):
        raise QualificationError("INCOMPLETE_PASS_REPORTS")
    for name, expected in (("test_unapproved_endpoint_rejected", 4),
                           ("test_failure_redacted_no_retry_no_failover_no_refund", 4),
                           ("test_capture_retains_exact_safe_bytes_without_pandas_or_second_request", 1)):
        prefix = FILES[0] + "::" + name
        if sum(n == prefix or n.startswith(prefix + "[") for n in nodes) != expected:
            raise QualificationError("SMOKE_GROUP_MISSING")
    return {"covered": list(COVERS), "not_covered": ["document_review", "native_policy"],
            "unique_collected": 98, "all_phases_passed": True, "source_qualified": False,
            "native_authorized": False, "reuse_allowed": False}


def validate_pc(process, report, before, after, expected_argv):
    if process.get("status") != "PASS" or type(process.get("exit_code")) is not int or process["exit_code"] != 0:
        raise QualificationError("CHILD_PROCESS_FAILED")
    if type(report) is not dict or set(report) != REPORT_KEYS:
        raise QualificationError("INVALID_CHILD_REPORT")
    if (type(report["schema_version"]) is not int or report["schema_version"] != 1
            or report["profile"] != "offline-pc" or report["cwd"] != str(ROOT)
            or report["argv"] != expected_argv or process.get("argv") != expected_argv
            or process.get("popen_env") != clean_env() or type(report["pytest_exit"]) is not int
            or report["pytest_exit"] != 0 or report["error"] is not None):
        raise QualificationError("CHILD_EXECUTION_MISMATCH")
    if not valid_env(report["env_before"]) or not valid_env(report["env_after"]) or report["env_before"] != report["env_after"]:
        raise QualificationError("CHILD_ENV_MISMATCH")
    if (report["guard_selftest"] != [{"event": e, "reason": r, "synthetic": True} for e, r in
            [("socket.connect", "NETWORK_FORBIDDEN"), ("subprocess.Popen", "PROCESS_LAUNCH_FORBIDDEN"),
             ("open", "SOURCE_OR_CREDENTIAL_FORBIDDEN")]] or report["unexpected_guard_events"] != []):
        raise QualificationError("GUARD_EVIDENCE_MISMATCH")
    coverage = coverage_for(report["collection"], report["reports"])
    if before is None or before != after or report["before"] != before or report["after"] != before:
        raise QualificationError("INPUT_IDENTITY_CHANGED")
    modules = report["post_only_modules"]
    expected = module_paths(ROOT)
    if type(modules) is not dict or any(n not in expected or info != before["files"].get(str(expected[n].relative_to(ROOT)))
                                       for n, info in modules.items()):
        raise QualificationError("INPUT_CLOSURE_UNREVIEWED")
    return coverage


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise QualificationError("DUPLICATE_REPORT_KEY")
        value[key] = item
    return value


def read_child_report(output):
    reader = Reader()
    path = output / "child/child.json"
    reader.identity(path)
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise QualificationError("REPORT_NOT_REGULAR")
        raw = stream.read(LIMITS["report_bytes"] + 1)
    if len(raw) > LIMITS["report_bytes"]:
        raise QualificationError("REPORT_LIMIT")
    return json.loads(raw, object_pairs_hook=unique_object)


def child_main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--child-output", required=True)
    args = parser.parse_args(argv)
    child = Path(os.path.abspath(args.child_output))
    if (not sys.flags.isolated or not sys.dont_write_bytecode or Path(sys.prefix) != ROOT / ".venv"
            or Path(sys.executable).absolute() != ROOT / ".venv/bin/python" or Path.cwd() != ROOT
            or child == ROOT or ROOT in child.parents or child in ROOT.parents
            or sys.pycache_prefix != str(child / "bytecode")):
        raise QualificationError("CHILD_CONTEXT_MISMATCH")
    for part in (child, *child.parents):
        if part.is_symlink():
            raise QualificationError("OUTPUT_SYMLINK")
    child.mkdir(mode=0o700)
    (child / "fixtures").mkdir(mode=0o700)
    (child / "bytecode").mkdir(mode=0o700)
    tempfile.tempdir = str(child / "fixtures")
    spec = importlib.util.spec_from_file_location("pc_runner", ROOT / "tools/validate_change.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    paths = list(module_paths(ROOT).values()) + [ROOT / p for p in PINS]
    paths += [ROOT / "tools/validate_change.py", ROOT / "tools/validation_offline_pc.py"]
    guard = Guard(ROOT, child, paths)
    guard.install()
    guard.selftest()
    env_before = observed_env()
    before = snapshot_pc(ROOT, runner.environment(ROOT))
    plugin = CoveragePlugin()
    error, code = None, 1
    try:
        import pytest
        code = int(pytest.main(["-c", str(ROOT / "pyproject.toml"),
            "--confcutdir=" + str(ROOT / "tests/research"), "-p", "no:cacheprovider", "-q",
            "--basetemp=" + str(child / "fixtures/pytest"), *FILES], plugins=[plugin]))
    except Exception as exc:
        error = type(exc).__name__
    after = snapshot_pc(ROOT, runner.environment(ROOT))
    reader = Reader()
    modules = {name: reader.identity(getattr(module, "__file__")) for name, module in sorted(sys.modules.items())
        if (name == "experiments" or name.startswith(("experiments.", "crypto_quant_")))
        and getattr(module, "__file__", None)}
    report = {"schema_version": 1, "profile": "offline-pc", "argv": argv_for_pc(ROOT, child.parent),
        "cwd": str(Path.cwd()), "before": before, "after": after, "env_before": env_before,
        "env_after": observed_env(), "guard_selftest": [e for e in guard.events if e["synthetic"]],
        "unexpected_guard_events": [e for e in guard.events if not e["synthetic"]],
        "collection": plugin.collection, "reports": plugin.reports, "pytest_exit": code,
        "post_only_modules": modules, "error": error}
    raw = runner.encoded(report)
    if len(raw) > LIMITS["report_bytes"]:
        raise QualificationError("REPORT_LIMIT")
    with (child / "child.json").open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if (child / "child.json").read_bytes() != raw:
        raise QualificationError("REPORT_READBACK")
    fd = os.open(child, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return 0 if code == 0 and error is None and not report["unexpected_guard_events"] else 1


if __name__ == "__main__":
    try:
        sys.exit(child_main())
    except Exception as exc:
        print("offline-pc child failed: " + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
