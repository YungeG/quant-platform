#!/usr/bin/env python3
"""Bounded, read-only identity verification for a retained L2 source tar.gz."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import stat
import sys
import tarfile
import zlib
from pathlib import Path, PurePosixPath

MAX_INVENTORY = 2 * 1024 * 1024
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_TAR = 64 * 1024 * 1024
MAX_MEMBERS = 5000
MAX_FILE = 4 * 1024 * 1024
HEX256 = re.compile(r"[0-9a-fA-F]{64}\Z")
HEX40 = re.compile(r"[0-9a-fA-F]{40}\Z")


class VerificationError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise VerificationError(code)


def _read_bounded(path: str | os.PathLike[str], limit: int) -> bytes:
    p = Path(path)
    try:
        # Reject symlinks in the file or any supplied ancestor.
        absolute = p.absolute()
        for part in (absolute, *absolute.parents):
            if part.is_symlink():
                _fail("unsafe_path")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(p, flags)
        with os.fdopen(fd, "rb") as f:
            before = os.fstat(f.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                _fail("input_limit")
            data = f.read(limit + 1)
            after = os.fstat(f.fileno())
            if len(data) > limit or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or len(data) != after.st_size:
                _fail("input_changed_or_limit")
            return data
    except VerificationError:
        raise
    except (OSError, ValueError):
        _fail("input_unavailable")


def _safe_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    try:
        p = PurePosixPath(value)
        return not p.is_absolute() and all(x not in ("", ".", "..") for x in value.split("/")) and str(p) == value
    except (TypeError, ValueError):
        return False


def verify_bundle(inventory_path, archive_path=None, *, expected_inventory_sha256=None) -> dict:
    if expected_inventory_sha256 is not None and (not isinstance(expected_inventory_sha256, str) or not HEX256.fullmatch(expected_inventory_sha256)):
        _fail("invalid_expected_inventory_hash")
    manifest_raw = _read_bounded(inventory_path, MAX_INVENTORY)
    manifest_hash = hashlib.sha256(manifest_raw).hexdigest()
    authenticated = expected_inventory_sha256 is not None
    if authenticated and manifest_hash.lower() != expected_inventory_sha256.lower():
        _fail("inventory_hash_mismatch")
    try:
        manifest = json.loads(manifest_raw)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        _fail("invalid_inventory")
    if not isinstance(manifest, dict):
        _fail("invalid_inventory")
    files = manifest.get("files")
    commit, archive_hash, archive_bytes = manifest.get("source_commit"), manifest.get("archive_sha256"), manifest.get("archive_bytes")
    old = manifest.get("old_worktree_path")
    if (not isinstance(files, list) or not files or len(files) > MAX_MEMBERS or
        not isinstance(commit, str) or not HEX40.fullmatch(commit) or
        not isinstance(archive_hash, str) or not HEX256.fullmatch(archive_hash) or
        type(archive_bytes) is not int or archive_bytes < 0 or archive_bytes > MAX_ARCHIVE or
        not isinstance(old, str) or not old):
        _fail("invalid_inventory")
    prefix = PurePosixPath(old.rstrip("/")).name
    if not _safe_path(prefix) or "/" in prefix:
        _fail("invalid_inventory")
    expected = {}
    for row in files:
        if not isinstance(row, dict):
            _fail("invalid_inventory_entry")
        path, mode, size, sha, blob = (row.get(k) for k in ("path", "mode", "bytes", "sha256", "git_blob"))
        if (not _safe_path(path) or path in expected or mode not in ("100644", "100755") or
            type(size) is not int or size < 0 or size > MAX_FILE or
            not isinstance(sha, str) or not HEX256.fullmatch(sha) or
            not isinstance(blob, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", blob)):
            _fail("invalid_inventory_entry")
        expected[path] = (mode, size, sha.lower(), blob.lower())
    apath = archive_path if archive_path is not None else manifest.get("archive_path")
    if not isinstance(apath, (str, os.PathLike)):
        _fail("archive_unavailable")
    raw = _read_bounded(apath, MAX_ARCHIVE)
    if len(raw) != archive_bytes or hashlib.sha256(raw).hexdigest().lower() != archive_hash.lower():
        _fail("archive_identity_mismatch")
    try:
        with gzip.GzipFile(fileobj=__import__("io").BytesIO(raw), mode="rb") as stream:
            decompressed = stream.read(MAX_TAR + 1)
    except (OSError, EOFError, gzip.BadGzipFile, zlib.error):
        _fail("invalid_archive")
    if len(decompressed) > MAX_TAR:
        _fail("tar_size_limit")
    seen = set()
    member_count = 0
    try:
        import io
        with tarfile.open(fileobj=io.BytesIO(decompressed), mode="r:") as tar:
            for member in tar:
                member_count += 1
                if member_count > MAX_MEMBERS:
                    _fail("member_limit")
                name = member.name
                if not _safe_path(name) or not member.isreg() or name.count("/") < 1:
                    _fail("unsafe_or_nonregular_member")
                member_prefix, rel = name.split("/", 1)
                if member_prefix != prefix or rel not in expected or rel in seen:
                    _fail("unexpected_or_duplicate_member")
                mode, size, sha, blob = expected[rel]
                if member.mode != int(mode[-4:], 8) or member.size != size or member.size > MAX_FILE:
                    _fail("member_metadata_mismatch")
                stream = tar.extractfile(member)
                if stream is None:
                    _fail("invalid_member")
                data = stream.read(MAX_FILE + 1)
                if len(data) != size or len(data) > MAX_FILE:
                    _fail("member_size_mismatch")
                if hashlib.sha256(data).hexdigest() != sha or hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != blob:
                    _fail("member_hash_mismatch")
                seen.add(rel)
    except VerificationError:
        raise
    except (tarfile.TarError, OSError, EOFError):
        _fail("invalid_archive")
    if seen != set(expected):
        _fail("missing_members")
    return {"role": "retained_source_bundle_identity_check_not_financial_validation", "source_commit": commit, "files_verified": len(seen), "archive_sha256": archive_hash.lower(), "inventory_sha256": manifest_hash, "old_worktree_path": old, "old_paths_restored": False, "market_data_read": False, "replay_executed": False, "financial_qualification": False, "manifest_authenticated": authenticated}


class _BoundedArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print("verification rejected: invalid_arguments", file=sys.stderr)
        raise SystemExit(2)


def main(argv=None) -> int:
    parser = _BoundedArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--archive")
    parser.add_argument("--expected-inventory-sha256")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify_bundle(args.inventory, args.archive, expected_inventory_sha256=args.expected_inventory_sha256), sort_keys=True))
        return 0
    except VerificationError as e:
        print("verification rejected: " + e.code, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
