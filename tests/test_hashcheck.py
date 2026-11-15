#!/usr/bin/env python3
from __future__ import annotations

import hashlib
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


hc = load("hashcheck")


class HashcheckTest(unittest.TestCase):
    def test_normalize_hash(self):
        self.assertEqual(hc.normalize_hash("SHA256:" + "A" * 64), "a" * 64)

    def test_hashcheck_ok_and_mismatch(self):
        body = b"hello-fleet"
        sha = hashlib.sha256(body).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bucket").mkdir()
            (root / "bucket" / "ok.json").write_text(
                json.dumps(
                    {
                        "id": "org.example.ok",
                        "architecture": {
                            "linux-amd64": {
                                "url": "https://example.test/ok.tar.gz",
                                "hash": f"sha256:{sha}",
                            }
                        },
                    }
                )
            )
            (root / "bucket" / "bad.json").write_text(
                json.dumps(
                    {
                        "id": "org.example.bad",
                        "architecture": {
                            "linux-amd64": {
                                "url": "https://example.test/bad.tar.gz",
                                "hash": f"sha256:{'b' * 64}",
                            }
                        },
                    }
                )
            )
            errors = hc.hashcheck_listings(root, fetch=lambda _url: body)
            self.assertEqual(len(errors), 1)
            self.assertIn("bad.json", errors[0])
            self.assertIn("hash mismatch", errors[0])


if __name__ == "__main__":
    unittest.main()
