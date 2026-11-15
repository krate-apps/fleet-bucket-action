#!/usr/bin/env python3
"""Pin architecture.linux-amd64 url + hash on bucket listings from a SHA256SUMS file."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

GITHUB_REPO_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def bucket_root(argv: list[str] | None = None) -> Path:
    env = os.environ.get("FLEET_BUCKET_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    args = list(sys.argv if argv is None else argv)
    if len(args) > 1 and not str(args[1]).startswith("-"):
        return Path(args[1]).resolve()
    return Path.cwd().resolve()


def resolve_sums_path(raw: str | None = None) -> Path:
    env = (raw if raw is not None else os.environ.get("PIN_SUMS", "")).strip()
    if not env:
        raise ValueError("PIN_SUMS is required (path to SHA256SUMS or a directory containing it)")
    p = Path(env).resolve()
    if p.is_dir():
        p = p / "SHA256SUMS"
    if not p.is_file():
        raise ValueError(f"missing SHA256SUMS: {p}")
    return p


def load_hashes(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            hashes[parts[1]] = parts[0]
    return hashes


def github_owner_repo(data: dict) -> str | None:
    checkver = data.get("checkver")
    if isinstance(checkver, dict):
        g = (checkver.get("github") or "").strip()
        if g and "/" in g:
            return g
    raw = (data.get("homepage") or "").strip()
    m = GITHUB_REPO_RE.match(raw)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    source = data.get("source") or {}
    if isinstance(source, dict):
        raw = (source.get("repository") or "").strip()
        m = GITHUB_REPO_RE.match(raw)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    return None


def release_asset_url(owner_repo: str, tag: str, asset: str) -> str:
    return f"https://github.com/{owner_repo}/releases/download/{tag.strip()}/{asset}"


def pin_listings(
    root: Path,
    sums: Path,
    *,
    tag: str = "",
    dry_run: bool = False,
) -> int:
    hashes = load_hashes(sums)
    bucket_dir = root / "bucket"
    if not bucket_dir.is_dir():
        raise ValueError(f"missing bucket/: {bucket_dir}")

    pinned = 0
    for path in sorted(bucket_dir.glob("*.json")):
        if path.name.endswith(".json.template"):
            continue
        data = json.loads(path.read_text())
        pkg_id = (data.get("id") or "").strip()
        if not pkg_id:
            print(f"skip {path.name}: missing id", file=sys.stderr)
            continue
        asset = f"{pkg_id}-linux-amd64.tar.gz"
        sha = hashes.get(asset)
        if not sha:
            print(f"skip {path.name}: no {asset} in SHA256SUMS")
            continue
        arch = data.setdefault("architecture", {})
        art = arch.setdefault("linux-amd64", {})
        art["hash"] = f"sha256:{sha}"
        if tag:
            owner_repo = github_owner_repo(data)
            if not owner_repo:
                print(
                    f"skip url for {path.name}: need checkver.github or GitHub homepage/source.repository",
                    file=sys.stderr,
                )
            else:
                art["url"] = release_asset_url(owner_repo, tag, asset)
        if dry_run:
            print(f"dry-run {pkg_id}: hash={sha[:12]}… url={art.get('url', '')}")
        else:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            print(f"pinned {pkg_id}: {sha[:12]}…")
            pinned += 1

    print(f"pin done ({pinned} updated) root={root} sums={sums}")
    return pinned


def main(argv: list[str] | None = None) -> int:
    try:
        root = bucket_root(argv)
        sums = resolve_sums_path()
        tag = os.environ.get("PIN_TAG", "").strip()
        dry = env_flag("PIN_DRY_RUN")
        pin_listings(root, sums, tag=tag, dry_run=dry)
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
