import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile

import pytest

from tools.verify_l2_source_bundle import VerificationError, verify_bundle


def fixture(tmp_path, members=None):
    members = members or {"a.py": b"print('ok')\n"}
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:") as tar:
        for path, data in members.items():
            info = tarfile.TarInfo("bundle/" + path)
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    archive = gzip.compress(out.getvalue(), mtime=0)
    ap = tmp_path / "bundle.tar.gz"
    ap.write_bytes(archive)
    rows = []
    for path, data in members.items():
        rows.append({"path": path, "mode": "100644", "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest(),
                     "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()})
    manifest = {"source_commit": "a" * 40, "archive_sha256": hashlib.sha256(archive).hexdigest(),
                "archive_bytes": len(archive), "archive_path": str(ap),
                "old_worktree_path": "/retired/bundle", "files": rows}
    ip = tmp_path / "inventory.json"
    ip.write_text(json.dumps(manifest))
    return ip, ap, manifest


def set_archive(tmp_path, ip, ap, manifest, entries):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:") as tar:
        for name, kind, data in entries:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "target"
                tar.addfile(info)
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
                info.linkname = "bundle/a.py"
                tar.addfile(info)
            elif kind == "dir":
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
    raw = gzip.compress(out.getvalue(), mtime=0)
    ap.write_bytes(raw)
    manifest["archive_sha256"] = hashlib.sha256(raw).hexdigest()
    manifest["archive_bytes"] = len(raw)
    ip.write_text(json.dumps(manifest))


def test_positive_synthetic_and_expected_manifest_hash(tmp_path):
    ip, ap, manifest = fixture(tmp_path)
    result = verify_bundle(ip)
    assert result["files_verified"] == 1
    assert result["financial_qualification"] is False
    assert result["old_paths_restored"] is False
    digest = hashlib.sha256(ip.read_bytes()).hexdigest()
    assert verify_bundle(ip, ap, expected_inventory_sha256=digest)["manifest_authenticated"] is True


def test_rejects_manifest_hash_and_missing_member(tmp_path):
    ip, ap, manifest = fixture(tmp_path)
    with pytest.raises(VerificationError, match="inventory_hash_mismatch"):
        verify_bundle(ip, ap, expected_inventory_sha256="0" * 64)
    manifest["files"].append({"path": "absent", "mode": "100644", "bytes": 0,
                              "sha256": hashlib.sha256(b"").hexdigest(),
                              "git_blob": hashlib.sha1(b"blob 0\0").hexdigest()})
    ip.write_text(json.dumps(manifest))
    with pytest.raises(VerificationError):
        verify_bundle(ip, ap)


def test_fifo_inventory_rejected_without_hanging(tmp_path):
    fifo = tmp_path / "inventory.fifo"
    os.mkfifo(fifo)
    proc = subprocess.run(
        [sys.executable, "tools/verify_l2_source_bundle.py", "--inventory", str(fifo)],
        cwd=os.getcwd(), capture_output=True, text=True, timeout=2,
    )
    assert proc.returncode == 1
    assert "verification rejected" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_relocation_duplicate_unexpected_and_nonregular_members(tmp_path):
    ip, ap, manifest = fixture(tmp_path)
    relocated = tmp_path / "relocated.tar.gz"
    relocated.write_bytes(ap.read_bytes())
    assert verify_bundle(ip, relocated)["files_verified"] == 1
    for extra in (
        ("bundle/a.py", "file", b"print('ok')\n"),
        ("bundle/extra.py", "file", b"x"),
        ("bundle/link", "symlink", b""),
        ("bundle/link", "hardlink", b""),
        ("bundle/folder", "dir", b""),
    ):
        ip, ap, manifest = fixture(tmp_path)
        set_archive(tmp_path, ip, ap, manifest, [("bundle/a.py", "file", b"print('ok')\n"), extra])
        with pytest.raises(VerificationError):
            verify_bundle(ip, ap)


def test_member_hash_gitblob_mode_size_and_boolean_size_rejected(tmp_path):
    for field, value in (("sha256", "0" * 64), ("git_blob", "0" * 40), ("mode", "100755"), ("bytes", 999), ("bytes", True)):
        ip, ap, manifest = fixture(tmp_path)
        manifest["files"][0][field] = value
        ip.write_text(json.dumps(manifest))
        with pytest.raises(VerificationError):
            verify_bundle(ip, ap)


def test_input_symlink_and_cli_argument_error_are_bounded(tmp_path):
    ip, ap, _ = fixture(tmp_path)
    link = tmp_path / "inventory-link"
    link.symlink_to(ip)
    with pytest.raises(VerificationError, match="unsafe_path"):
        verify_bundle(link, ap)
    proc = subprocess.run([sys.executable, "tools/verify_l2_source_bundle.py", "--inventory", "SECRET-PATH", "--bogus", "SECRET-TOKEN"],
                          cwd=os.getcwd(), capture_output=True, text=True, timeout=2)
    assert proc.returncode == 2
    assert "SECRET" not in proc.stderr and "Traceback" not in proc.stderr


def test_small_patched_limits_rejected(tmp_path, monkeypatch):
    import tools.verify_l2_source_bundle as verifier
    ip, ap, manifest = fixture(tmp_path)
    monkeypatch.setattr(verifier, "MAX_INVENTORY", 10)
    with pytest.raises(VerificationError):
        verify_bundle(ip, ap)
    monkeypatch.setattr(verifier, "MAX_INVENTORY", 2 * 1024 * 1024)
    monkeypatch.setattr(verifier, "MAX_ARCHIVE", 1)
    with pytest.raises(VerificationError):
        verify_bundle(ip, ap)
    monkeypatch.setattr(verifier, "MAX_ARCHIVE", 32 * 1024 * 1024)
    monkeypatch.setattr(verifier, "MAX_TAR", 10)
    with pytest.raises(VerificationError, match="tar_size_limit"):
        verify_bundle(ip, ap)
    monkeypatch.setattr(verifier, "MAX_TAR", 64 * 1024 * 1024)
    monkeypatch.setattr(verifier, "MAX_FILE", 1)
    with pytest.raises(VerificationError):
        verify_bundle(ip, ap)
    monkeypatch.setattr(verifier, "MAX_FILE", 4 * 1024 * 1024)
    ip2, ap2, _ = fixture(tmp_path, {"a.py": b"a", "b.py": b"b"})
    monkeypatch.setattr(verifier, "MAX_MEMBERS", 1)
    with pytest.raises(VerificationError):
        verify_bundle(ip2, ap2)


def test_rejects_traversal_and_relocated_archive_mismatch(tmp_path):
    ip, ap, manifest = fixture(tmp_path)
    manifest["files"][0]["path"] = "../escape"
    ip.write_text(json.dumps(manifest))
    with pytest.raises(VerificationError):
        verify_bundle(ip, ap)
    ip, ap, _ = fixture(tmp_path)
    changed = tmp_path / "changed.tar.gz"
    changed.write_bytes(ap.read_bytes() + b"x")
    with pytest.raises(VerificationError, match="archive_identity_mismatch"):
        verify_bundle(ip, changed)
