"""Bump the pinned LLVM release in llvm-version.txt."""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

API_URL = "https://api.github.com/repos/llvm/llvm-project/releases/latest"
TAG_RE = re.compile(r"llvmorg-(\d+(?:\.\d+)*)")
SHA_RE = re.compile(r"[0-9a-f]{64}")


def version_of(tag: str) -> tuple | None:
    """Return the numeric version of an llvmorg tag. Return None for rc and pre tags."""
    match = TAG_RE.fullmatch(tag)
    if match is None:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer(latest_tag: str, current_tag: str) -> bool:
    new = version_of(latest_tag)
    cur = version_of(current_tag)
    return new is not None and cur is not None and new > cur


def read_version(path: Path) -> tuple[str, str]:
    lines = path.read_text().splitlines()
    if len(lines) != 2:
        raise ValueError(f"{path} needs two lines: tag and sha256")
    tag, sha = lines[0].strip(), lines[1].strip()
    if version_of(tag) is None:
        raise ValueError(f"bad tag {tag!r} in {path}")
    if SHA_RE.fullmatch(sha) is None:
        raise ValueError(f"bad sha256 in {path}")
    return tag, sha


def fetch_url(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "simdref-llvm-mc-bump"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = b""
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for chunk in iter(lambda: resp.read(1 << 20), b""):
            data += chunk
    return data


def fetch_asset(url: str, size: int) -> bytes:
    data = fetch_url(url)
    if len(data) != size:
        raise ValueError(f"asset size {len(data)} != {size} from the API")
    return data


def write_version(path: Path, tag: str, sha: str) -> None:
    path.write_text(f"{tag}\n{sha}\n")


def asset_name(tag: str) -> str:
    return f"llvm-project-{tag.removeprefix('llvmorg-')}.src.tar.xz"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version_file", nargs="?", default="llvm-version.txt")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the planned bump. Download and write nothing.")
    parser.add_argument("--releases-json", metavar="FILE",
                        help="Read this releases JSON file instead of the API.")
    args = parser.parse_args(argv)

    try:
        current_tag, _ = read_version(Path(args.version_file))
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    if args.releases_json:
        release = json.loads(Path(args.releases_json).read_text())
    else:
        release = json.loads(fetch_url(API_URL))

    latest_tag = release["tag_name"]
    if not is_newer(latest_tag, current_tag):
        print("up to date")
        return 0
    if args.dry_run:
        print(f"{latest_tag} is newer than {current_tag}; "
              f"would download the src tarball and rewrite {args.version_file}")
        return 0

    assets = {a["name"]: a for a in release.get("assets", [])}
    name = asset_name(latest_tag)
    if name not in assets:
        print(f"error: asset {name} not in release {latest_tag}", file=sys.stderr)
        return 1
    data = fetch_asset(assets[name]["browser_download_url"], assets[name]["size"])
    sha = hashlib.sha256(data).hexdigest()
    write_version(Path(args.version_file), latest_tag, sha)
    print(latest_tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
