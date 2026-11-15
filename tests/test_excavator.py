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


exc = load("excavator")


class ExcavatorTest(unittest.TestCase):
    def test_strip_v_and_checkver(self):
        self.assertEqual(exc.strip_v("v1.2.3"), "1.2.3")
        self.assertEqual(exc.strip_v("1.2.3"), "1.2.3")
        self.assertEqual(exc.github_from_checkver({"github": "o/r"}), "o/r")
        self.assertIsNone(exc.github_from_checkver("x"))

    def test_excavate_bumps_with_mocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bucket").mkdir()
            listing = root / "bucket" / "org.fleet.demo.json"
            listing.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "kind": "extension",
                        "id": "org.fleet.demo",
                        "name": "Demo",
                        "version": "1.0.0",
                        "api": ">=1.0.0 <2.0.0",
                        "checkver": {"github": "krate-apps/fleet-ext-demo"},
                        "autoupdate": {
                            "architecture": {
                                "linux-amd64": {
                                    "url": "https://github.com/krate-apps/fleet-ext-demo/releases/download/v$version/org.fleet.demo-linux-amd64.tar.gz"
                                }
                            }
                        },
                    },
                    indent=2,
                )
                + "\n"
            )
            body = b"payload-bytes"
            sha = hashlib.sha256(body).hexdigest()

            def fake_release(_repo: str) -> dict:
                return {
                    "tag_name": "v2.0.0",
                    "assets": [
                        {
                            "name": "org.fleet.demo-linux-amd64.tar.gz",
                            "browser_download_url": "https://example.test/demo.tar.gz",
                        }
                    ],
                }

            n = exc.excavate(
                root,
                dry_run=False,
                fetch_release=fake_release,
                fetch_sha=lambda _url: sha,
            )
            self.assertEqual(n, 1)
            data = json.loads(listing.read_text())
            self.assertEqual(data["version"], "2.0.0")
            self.assertEqual(data["architecture"]["linux-amd64"]["hash"], f"sha256:{sha}")
            self.assertEqual(data["architecture"]["linux-amd64"]["url"], "https://example.test/demo.tar.gz")

            n2 = exc.excavate(
                root,
                dry_run=False,
                fetch_release=fake_release,
                fetch_sha=lambda _url: sha,
            )
            self.assertEqual(n2, 0)

    def test_excavate_fills_missing_architecture_same_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bucket").mkdir()
            listing = root / "bucket" / "org.fleet.demo.json"
            listing.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "kind": "extension",
                        "id": "org.fleet.demo",
                        "name": "Demo",
                        "version": "1.0.0",
                        "api": ">=1.0.0 <2.0.0",
                        "checkver": {"github": "krate-apps/fleet-ext-demo"},
                        "autoupdate": {
                            "architecture": {
                                "linux-amd64": {
                                    "url": "https://github.com/krate-apps/fleet-ext-demo/releases/download/v$version/org.fleet.demo-linux-amd64.tar.gz"
                                }
                            }
                        },
                    },
                    indent=2,
                )
                + "\n"
            )
            body = b"payload-bytes"
            sha = hashlib.sha256(body).hexdigest()

            def fake_release(_repo: str) -> dict:
                return {
                    "tag_name": "v1.0.0",
                    "assets": [
                        {
                            "name": "org.fleet.demo-linux-amd64.tar.gz",
                            "browser_download_url": "https://example.test/demo.tar.gz",
                        }
                    ],
                }

            n = exc.excavate(
                root,
                dry_run=False,
                fetch_release=fake_release,
                fetch_sha=lambda _url: sha,
            )
            self.assertEqual(n, 1)
            data = json.loads(listing.read_text())
            self.assertEqual(data["version"], "1.0.0")
            self.assertEqual(data["architecture"]["linux-amd64"]["url"], "https://example.test/demo.tar.gz")
            self.assertEqual(data["architecture"]["linux-amd64"]["hash"], f"sha256:{sha}")


if __name__ == "__main__":
    unittest.main()
