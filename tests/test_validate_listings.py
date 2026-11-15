#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


val = load("validate-listings")


class ValidateListingsTest(unittest.TestCase):
    def test_ok_minimal_bucket(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bucket").mkdir()
            (root / "bucket.json").write_text(
                json.dumps({"schema": 1, "id": "org.example.bucket", "name": "Example"})
            )
            (root / "bucket" / "org.example.app.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "kind": "extension",
                        "id": "org.example.app",
                        "name": "App",
                        "version": "1.0.0",
                        "api": ">=1.0.0 <2.0.0",
                        "homepage": "https://example.com",
                    }
                )
            )
            self.assertEqual(val.validate_listings(root), [])

    def test_rejects_bad_github_url_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bucket").mkdir()
            (root / "bucket.json").write_text(
                json.dumps({"schema": 1, "id": "org.example.bucket", "name": "Example"})
            )
            (root / "bucket" / "org.example.app.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "kind": "extension",
                        "id": "org.example.app",
                        "name": "App",
                        "version": "1.0.0",
                        "api": ">=1.0.0 <2.0.0",
                        "architecture": {
                            "linux-amd64": {
                                "url": "https://github.com/acme/ext/archive/main.tar.gz",
                                "hash": "deadbeef",
                            }
                        },
                    }
                )
            )
            errors = val.validate_listings(root)
            joined = "\n".join(errors)
            self.assertIn("hash invalid", joined)
            self.assertIn("pinned releases/download", joined)


if __name__ == "__main__":
    unittest.main()
