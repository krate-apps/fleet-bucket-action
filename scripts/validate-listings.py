#!/usr/bin/env python3
"""Validate Fleet bucket listings (bucket.json + bucket/*.json)."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HASH_RE = re.compile(r"^(sha256:)?[a-fA-F0-9]{64}$")
GH_PIN_RE = re.compile(
    r"^https://github\.com/[^/]+/[^/]+/releases/download/[^/]+/[^/]+$"
)


def bucket_root(argv: list[str] | None = None) -> Path:
    env = os.environ.get("FLEET_BUCKET_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    args = list(sys.argv if argv is None else argv)
    if len(args) > 1 and not str(args[1]).startswith("-"):
        return Path(args[1]).resolve()
    return Path.cwd().resolve()


def load_json(path: Path, errors: list[str]):
    try:
        data = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path}: parse error: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path}: expected object")
        return None
    return data


def require(data: dict, path: Path, keys: list[str], errors: list[str]) -> None:
    for key in keys:
        if key not in data or data[key] in (None, ""):
            errors.append(f"{path}: missing '{key}'")


def validate_listings(root: Path) -> list[str]:
    errors: list[str] = []
    root_path = root / "bucket.json"
    bucket = load_json(root_path, errors)
    if bucket:
        require(bucket, root_path, ["schema", "id", "name"], errors)

    app_dir = root / "bucket"
    if not app_dir.is_dir():
        errors.append(f"{app_dir}: missing bucket/ directory")
        return errors

    for path in sorted(app_dir.glob("*.json")):
        if path.name.endswith(".json.template"):
            continue
        data = load_json(path, errors)
        if not data:
            continue
        kind = data.get("kind") or "extension"
        require(data, path, ["schema", "kind", "id", "name", "version"], errors)
        if kind == "extension":
            require(data, path, ["api"], errors)
        elif kind != "theme":
            errors.append(f"{path}: kind must be extension or theme")

        src = data.get("source") or {}
        arch = data.get("architecture") or {}
        rel = (src.get("path") or "").strip()
        urls = [((arch.get(k) or {}).get("url") or "").strip() for k in arch]
        urls = [u for u in urls if u]
        homepage = (data.get("homepage") or "").strip()
        if not rel and not urls and not homepage:
            errors.append(
                f"{path}: need source.path, architecture.*.url, and/or homepage"
            )
        if rel:
            target = (root / rel).resolve()
            if not target.exists():
                errors.append(f"{path}: source.path '{rel}' does not exist")
            elif kind == "extension":
                man = target / "fleet.ext.yaml"
                if not man.is_file():
                    errors.append(f"{path}: missing fleet.ext.yaml under {rel}")
            elif kind == "theme":
                man = target / "fleet.theme.yaml"
                if not man.is_file():
                    errors.append(f"{path}: missing fleet.theme.yaml under {rel}")

        for arch_name, art in arch.items():
            if not isinstance(art, dict):
                errors.append(f"{path}: architecture.{arch_name} must be object")
                continue
            h = (art.get("hash") or "").strip()
            u = (art.get("url") or "").strip()
            if h and not HASH_RE.match(h):
                errors.append(f"{path}: architecture.{arch_name}.hash invalid")
            if u and "github.com" in u and not GH_PIN_RE.match(u):
                errors.append(
                    f"{path}: GitHub URL must be pinned releases/download/... asset"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    root = bucket_root(argv)
    errors = validate_listings(root)
    if errors:
        print("validation failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"bucket listings OK ({root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
