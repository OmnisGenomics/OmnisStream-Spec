# Protobuf Schemas

## Package naming

All v0.1 schemas live under:

- Protobuf `package`: `omnisstream.v1`
- Files: `proto/omnisstream/v1/*.proto`

## Compiling with `protoc`

This repo intentionally does not require `buf`.

Validate that the protos compile:

```bash
./proto/protoc.sh
```

Generate language bindings (example: Python):

```bash
protoc -I proto --python_out=/tmp/omnisstream-proto-out proto/omnisstream/v1/manifest.proto
```

## Compatibility rules

- Protobuf field numbers are stable and MUST NOT be reused.
- New fields MUST be added with new numbers and MUST be optional/backwards-compatible within a MAJOR version (see `VERSIONING.md`).

