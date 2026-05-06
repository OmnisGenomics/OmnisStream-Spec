from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from omnisstream_validate.load import load_manifest
from omnisstream_validate.validate import validate_manifest


class TestVectors(unittest.TestCase):
    # json-loader bool rejection coverage lives below.
    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    def test_vector_minimal_passes(self) -> None:
        vector_dir = self.repo_root / "test-vectors/vector-minimal"
        manifest = load_manifest(vector_dir / "manifest.pb", fmt="protobuf")
        issues = validate_manifest(manifest, base_dir=vector_dir)
        self.assertEqual(issues, [])

    def test_vector_compressed_passes(self) -> None:
        vector_dir = self.repo_root / "test-vectors/vector-compressed"
        manifest = load_manifest(vector_dir / "manifest.pb", fmt="protobuf")
        issues = validate_manifest(manifest, base_dir=vector_dir)
        self.assertEqual(issues, [])

    def test_corrupt_byte_fails(self) -> None:
        src_dir = self.repo_root / "test-vectors/vector-minimal"

        with tempfile.TemporaryDirectory() as td:
            tmp_dir = Path(td) / "vector-minimal"
            shutil.copytree(src_dir, tmp_dir)

            part = tmp_dir / "parts/part-0001.bin"
            data = bytearray(part.read_bytes())
            data[0] ^= 0x01
            part.write_bytes(bytes(data))

            manifest = load_manifest(tmp_dir / "manifest.pb", fmt="protobuf")
            issues = validate_manifest(manifest, base_dir=tmp_dir)
            self.assertTrue(issues)


def test_rejects_bool_object_length(self) -> None:
    payload = {
        "manifest_version": "1",
        "object_id": "obj-1",
        "object_length": True,
        "parts": [],
    }
    with tempfile.TemporaryDirectory() as td:
        manifest_path = Path(td) / "manifest.json"
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "object_length"):
            load_manifest(manifest_path, fmt="json")

def test_rejects_bool_nested_integer_fields(self) -> None:
    nested_cases = [
        ("parts", {"part_number": True}),
        ("parts", {"offset": True}),
        ("parts", {"length": True}),
        ("parts", {"stored_length": True}),
        ("upload_session", {"upload_id": "u1", "created_unix_ms": True}),
        ("upload_session", {"upload_id": "u1", "updated_unix_ms": True}),
        ("commit", {"commit_id": "c1", "committed_unix_ms": True}),
    ]
    for container, patch in nested_cases:
        with self.subTest(container=container, patch=patch):
            payload = {
                "manifest_version": "1",
                "object_id": "obj-1",
                "object_length": 1,
                "parts": [
                    {
                        "part_number": 1,
                        "offset": 0,
                        "length": 1,
                        "stored_length": 1,
                        "compression": "none",
                        "hashes": [],
                    }
                ],
            }
            if container == "parts":
                payload[container][0].update(patch)
                expected = next(iter(patch))
            else:
                payload[container] = patch
                expected = next(k for k in patch.keys() if k not in {"upload_id", "commit_id"})
            with tempfile.TemporaryDirectory() as td:
                manifest_path = Path(td) / "manifest.json"
                manifest_path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, expected):
                    load_manifest(manifest_path, fmt="json")


if __name__ == "__main__":
    unittest.main()
