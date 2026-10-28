"""Unit tests for scripts/bump_llvm.py."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import bump_llvm

PAYLOAD = b"llvm-project src " * 128
SEED = "llvmorg-23.1.3\n" + "0" * 64 + "\n"


def make_release(tag: str, payload: bytes, size: int | None = None) -> dict:
    return {
        "tag_name": tag,
        "assets": [
            {
                "name": f"llvm-project-{tag.removeprefix('llvmorg-')}.src.tar.xz",
                "size": len(payload) if size is None else size,
                "browser_download_url": f"https://example.invalid/{tag}/src.tar.xz",
            }
        ],
    }


def no_download(url: str, timeout: int = 120) -> bytes:
    raise AssertionError("fetch_url must not run here")


def test_newer_tag_rewrites_both_lines(tmp_path, monkeypatch):
    vfile = tmp_path / "llvm-version.txt"
    vfile.write_text(SEED)
    rj = tmp_path / "releases.json"
    rj.write_text(json.dumps(make_release("llvmorg-23.1.4", PAYLOAD)))
    monkeypatch.setattr(bump_llvm, "fetch_url", lambda url, timeout=120: PAYLOAD)
    rc = bump_llvm.main([str(vfile), "--releases-json", str(rj)])
    assert rc == 0
    want = "llvmorg-23.1.4\n" + hashlib.sha256(PAYLOAD).hexdigest() + "\n"
    assert vfile.read_text() == want


def test_same_tag_is_noop(tmp_path, monkeypatch):
    vfile = tmp_path / "llvm-version.txt"
    vfile.write_text(SEED)
    rj = tmp_path / "releases.json"
    rj.write_text(json.dumps(make_release("llvmorg-23.1.3", PAYLOAD)))
    monkeypatch.setattr(bump_llvm, "fetch_url", no_download)
    rc = bump_llvm.main([str(vfile), "--releases-json", str(rj)])
    assert rc == 0
    assert vfile.read_bytes() == SEED.encode()


def test_rc_tag_is_ignored(tmp_path, monkeypatch):
    vfile = tmp_path / "llvm-version.txt"
    vfile.write_text(SEED)
    rj = tmp_path / "releases.json"
    rj.write_text(json.dumps(make_release("llvmorg-24.0.0-rc1", PAYLOAD)))
    monkeypatch.setattr(bump_llvm, "fetch_url", no_download)
    rc = bump_llvm.main([str(vfile), "--releases-json", str(rj)])
    assert rc == 0
    assert vfile.read_bytes() == SEED.encode()


def test_size_mismatch_raises_and_writes_nothing(tmp_path, monkeypatch):
    vfile = tmp_path / "llvm-version.txt"
    vfile.write_text(SEED)
    rj = tmp_path / "releases.json"
    rj.write_text(json.dumps(make_release("llvmorg-23.1.4", PAYLOAD,
                                          size=len(PAYLOAD) + 8)))
    monkeypatch.setattr(bump_llvm, "fetch_url", lambda url, timeout=120: PAYLOAD)
    with pytest.raises(ValueError, match="size"):
        bump_llvm.main([str(vfile), "--releases-json", str(rj)])
    assert vfile.read_bytes() == SEED.encode()
