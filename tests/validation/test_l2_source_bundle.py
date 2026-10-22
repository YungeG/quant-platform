import gzip
import hashlib
import io
import json
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
