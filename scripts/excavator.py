#!/usr/bin/env python3
"""Fleet excavator: bump version/url/hash from GitHub Releases (checkver.github)."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Callable


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


def gh_headers(token: str = "") -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "fleet-bucket-excavator"}
    tok = token or os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def latest_release(owner_repo: str, *, token: str = "") -> dict:
    url = f"https://api.github.com/repos/{owner_repo}/releases/latest"
    req = urllib.request.Request(url, headers=gh_headers(token))
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def download_sha256(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "fleet-bucket-excavator"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return hashlib.sha256(resp.read()).hexdigest()


def strip_v(tag: str) -> str:
    tag = tag.strip()
    if tag.startswith("v") or tag.startswith("V"):
        return tag[1:]
    return tag


def github_from_checkver(checkver) -> str | None:
    if isinstance(checkver, dict):
        g = (checkver.get("github") or "").strip()
        return g or None
    return None


def excavate(
    root: Path,
    *,
    dry_run: bool = False,
    fetch_release: Callable[[str], dict] | None = None,
    fetch_sha: Callable[[str], str] | None = None,
) -> int:
    fetch_release = fetch_release or latest_release
    fetch_sha = fetch_sha or download_sha256
    bucket_dir = root / "bucket"
    if not bucket_dir.is_dir():
        print(f"missing bucket/: {bucket_dir}", file=sys.stderr)
        return 0

    changed = 0
    for path in sorted(bucket_dir.glob("*.json")):
        if path.name.endswith(".json.template"):
            continue
        data = json.loads(path.read_text())
        owner_repo = github_from_checkver(data.get("checkver"))
        if not owner_repo:
            continue
        auto = data.get("autoupdate") or {}
        auto_arch = (auto.get("architecture") or {}).get("linux-amd64") or {}
        tmpl = (auto_arch.get("url") or "").strip()
        if not tmpl or "$version" not in tmpl:
            print(f"skip {path.name}: no autoupdate.architecture.linux-amd64.url with $version")
            continue
        try:
            rel = fetch_release(owner_repo)
        except Exception as exc:  # noqa: BLE001
            print(f"skip {path.name}: release fetch failed: {exc}", file=sys.stderr)
            continue
        version = strip_v(rel.get("tag_name") or "")
        if not version:
            continue
        arch = data.get("architecture") or {}
        art = arch.get("linux-amd64") or {}
        have_url = bool(str(art.get("url") or "").strip())
        have_hash = bool(str(art.get("hash") or "").strip())
        same_version = version == str(data.get("version") or "")
        if same_version and have_url and have_hash:
            print(f"ok {path.name}: already {version}")
            continue
        url = tmpl.replace("$version", version)
        base = url.rsplit("/", 1)[-1]
        asset_url = url
        for asset in rel.get("assets") or []:
            if asset.get("name") == base:
                asset_url = asset.get("browser_download_url") or url
                break
        try:
            sha = fetch_sha(asset_url)
        except Exception as exc:  # noqa: BLE001
            print(f"skip {path.name}: hash download failed: {exc}", file=sys.stderr)
            continue
        data["version"] = version
        arch_out = data.setdefault("architecture", {})
        art_out = arch_out.setdefault("linux-amd64", {})
        art_out["url"] = asset_url
        art_out["hash"] = f"sha256:{sha}"
        if dry_run:
            print(f"dry-run {path.name}: -> {version}")
        else:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            print(f"updated {path.name}: -> {version}")
            changed += 1

    print(f"excavator done ({changed} updated) root={root}")
    return changed


def main(argv: list[str] | None = None) -> int:
    root = bucket_root(argv)
    excavate(root, dry_run=env_flag("EXCAVATOR_DRY_RUN"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
