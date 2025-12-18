# Contributing

Thanks for helping improve the OmnisStream specification.

## What belongs in this repo

This repository is **spec-only**. It contains:

- Normative specs (`*.md`) using RFC 2119 keywords.
- Wire schemas (`proto/`) and canonical JSON rules.
- Deterministic test vectors (`test-vectors/`).
- A tiny reference validator (`tools/validator/`).

Production implementations belong in separate repos.

## How to contribute

- File an issue first for any non-trivial change or new feature.
- Keep changes small and focused; avoid drive-by refactors.
- For normative statements, use RFC 2119 keywords (MUST/SHOULD/MAY).
- When changing schemas, preserve protobuf field numbers and document additions.
- When changing vectors, include regeneration steps and update expected digests.

## Validation

Before submitting, ensure:

- `protoc` can compile the protos (see `proto/README.md`).
- `omnisstream-validate` passes on all vectors (see `test-vectors/README.md`).

