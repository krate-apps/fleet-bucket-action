#!/usr/bin/env python3
"""Download architecture URLs and verify sha256 hashes."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Callable


def bucket_root(argv: list[str] | None = None) -> Path:
    env = os.environ.get("FLEET_BUCKET_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    args = list(sys.argv if argv is None else argv)
    if len(args) > 1 and not str(args[1]).startswith("-"):
        return Path(args[1]).resolve()
    return Path.cwd().resolve()


def normalize_hash(raw: str) -> str:
    h = (raw or "").strip()
    if h.lower().startswith("sha256:"):
        h = h.split(":", 1)[1].strip()
    return h.lower()


def fetch_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read()


def hashcheck_listings(
    root: Path,
    *,
    fetch: Callable[[str], bytes] | None = None,
) -> list[str]:
    fetch = fetch or fetch_bytes
    errors: list[str] = []
    app_dir = root / "bucket"
    if not app_dir.is_dir():
        return [f"missing bucket/: {app_dir}"]

    checked = 0
    for path in sorted(app_dir.glob("*.json")):
        if path.name.endswith(".json.template"):
            continue
        data = json.loads(path.read_text())
        arch = data.get("architecture") or {}
        pairs = [
            (name, art)
            for name, art in arch.items()
            if isinstance(art, dict) and (art.get("url") or "").strip() and (art.get("hash") or "").strip()
        ]
        if not pairs:
            continue
        checked += 1
        for name, art in pairs:
            url = (art.get("url") or "").strip()
            expect = normalize_hash(art.get("hash") or "")
            try:
                body = fetch(url)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{path.name} [{name}]: download failed: {exc}")
                continue
            got = hashlib.sha256(body).hexdigest()
            if got != expect:
                errors.append(f"{path.name} [{name}]: hash mismatch got={got} expect={expect}")
            else:
                print(f"ok {path.name} [{name}]")

    if checked == 0:
        print("hashcheck: no architecture url+hash pairs to verify")
    return errors


def main(argv: list[str] | None = None) -> int:
    root = bucket_root(argv)
    errors = hashcheck_listings(root)
    if errors:
        print("hashcheck failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"hashcheck OK ({root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
