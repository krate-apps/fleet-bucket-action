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


pin = load("pin-listings")


class PinListingsTest(unittest.TestCase):
    def test_load_hashes_and_github_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            sums = Path(tmp) / "SHA256SUMS"
            sums.write_text("abc123  org.fleet.demo-linux-amd64.tar.gz\n")
            self.assertEqual(
                pin.load_hashes(sums),
                {"org.fleet.demo-linux-amd64.tar.gz": "abc123"},
            )
        self.assertEqual(
            pin.github_owner_repo({"checkver": {"github": "krate-apps/fleet-ext-demo"}}),
            "krate-apps/fleet-ext-demo",
        )
        self.assertEqual(
            pin.github_owner_repo({"homepage": "https://github.com/acme/ext.git"}),
            "acme/ext",
        )
        self.assertEqual(
            pin.release_asset_url("acme/ext", "v1.0.0", "x.tar.gz"),
            "https://github.com/acme/ext/releases/download/v1.0.0/x.tar.gz",
        )

    def test_pin_writes_hash_and_url(self):
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
                        "version": "0.1.0",
                        "api": ">=1.0.0 <2.0.0",
                        "checkver": {"github": "krate-apps/fleet-ext-demo"},
                    }
                )
            )
            sums = root / "SHA256SUMS"
            sha = "a" * 64
            sums.write_text(f"{sha}  org.fleet.demo-linux-amd64.tar.gz\n")
            n = pin.pin_listings(root, sums, tag="v9.9.9", dry_run=False)
            self.assertEqual(n, 1)
            data = json.loads(listing.read_text())
            self.assertEqual(data["architecture"]["linux-amd64"]["hash"], f"sha256:{sha}")
            self.assertIn(
                "/releases/download/v9.9.9/org.fleet.demo-linux-amd64.tar.gz",
                data["architecture"]["linux-amd64"]["url"],
            )


if __name__ == "__main__":
    unittest.main()
