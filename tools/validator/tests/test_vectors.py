from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from omnisstream_validate.load import load_manifest
from omnisstream_validate.validate import validate_manifest


class TestVectors(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
