# omnisstream-spec

**Spec-only; no production implementation here.**

This repository is the normative specification (“the constitution”) for OmnisStream object manifests, canonical JSON form, and wire schemas.

## What’s in here

- `MANIFEST_SPEC.md` — normative manifest specification (RFC 2119 keywords).
- `CANONICAL_JSON.md` — canonical JSON representation and ordering rules.
- `proto/` — protobuf schema (`proto/omnisstream/v1/manifest.proto`).
- `test-vectors/` — deterministic fixtures (bytes + manifests + expected digests).
- `tools/validator/` — tiny reference validator (`omnisstream-validate`).

## Quick start (validate vectors)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e tools/validator
omnisstream-validate test-vectors/vector-minimal/manifest.pb --base-dir test-vectors/vector-minimal
omnisstream-validate test-vectors/vector-compressed/manifest.pb --base-dir test-vectors/vector-compressed
```

## Status

- Current spec series: `0.1.x`
- Current schema package: `omnisstream.v1`

## License

This repository is licensed under the Apache License, Version 2.0. See LICENSE.
