# Test Vectors

This directory contains deterministic fixtures for validating OmnisStream manifest readers and validators.

Each vector folder contains:

- `parts/` — raw part payload bytes (as stored/transmitted).
- `manifest.pb` — protobuf-encoded `omnisstream.v1.ObjectManifest`.
- `manifest.json` — canonical JSON representation of the same manifest (minified).
- `EXPECTED.txt` — exact digests for each `parts/*` file.

## Verification

Using the reference validator:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e tools/validator
omnisstream-validate test-vectors/vector-minimal/manifest.pb --base-dir test-vectors/vector-minimal
omnisstream-validate test-vectors/vector-compressed/manifest.pb --base-dir test-vectors/vector-compressed
```

## Digest conventions

- All digests are computed over the **stored payload bytes** (the contents of each `parts/*` file).
- CRC32C is represented as the hex of the 4 digest bytes in big-endian order, and as base64 of those same 4 bytes.
- BLAKE3-256 is represented as the hex/base64 of the 32 digest bytes.

## Notes

`vector-compressed` uses placeholder payload bytes with `compression` enums set to exercise schema paths; the payloads are not required to be valid compressed streams yet.
