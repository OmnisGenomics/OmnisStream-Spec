from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from omnisstream_validate.load import load_manifest


class TestJsonLoaderIntegers(unittest.TestCase):
    def _load_payload(self, payload: dict[str, object]) -> None:
        with tempfile.TemporaryDirectory() as td:
            manifest_path = Path(td) / "manifest.json"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            load_manifest(manifest_path, fmt="json")

    def _base_payload(self) -> dict[str, object]:
        return {
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

    def test_rejects_out_of_range_object_length(self) -> None:
        payload = self._base_payload()
        payload["object_length"] = 2**64

        with self.assertRaisesRegex(ValueError, "object_length"):
            self._load_payload(payload)

    def test_rejects_out_of_range_nested_integer_fields(self) -> None:
        cases = [
            ("part_number", 2**32),
            ("offset", 2**64),
            ("length", 2**64),
            ("stored_length", 2**64),
        ]

        for field, value in cases:
            with self.subTest(field=field):
                payload = self._base_payload()
                parts = payload["parts"]
                assert isinstance(parts, list)
                part = parts[0]
                assert isinstance(part, dict)
                part[field] = value

                with self.assertRaisesRegex(ValueError, field):
                    self._load_payload(payload)

    def test_rejects_bool_object_length(self) -> None:
        payload = self._base_payload()
        payload["object_length"] = True

        with self.assertRaisesRegex(ValueError, "object_length"):
            self._load_payload(payload)

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
                payload = self._base_payload()
                if container == "parts":
                    parts = payload[container]
                    assert isinstance(parts, list)
                    part = parts[0]
                    assert isinstance(part, dict)
                    part.update(patch)
                    expected = next(iter(patch))
                else:
                    payload[container] = patch
                    expected = next(k for k in patch if k not in {"upload_id", "commit_id"})

                with self.assertRaisesRegex(ValueError, expected):
                    self._load_payload(payload)


if __name__ == "__main__":
    unittest.main()
