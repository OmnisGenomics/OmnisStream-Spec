# OmnisStream Reference Validator

This is a tiny, boring, reference validator for `omnisstream-spec`.

It is intentionally minimal and is **not** a production implementation.

## Install (recommended: virtualenv)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e tools/validator
```

## Usage

Validate a protobuf manifest against local part payload bytes:

```bash
omnisstream-validate path/to/manifest.pb --base-dir path/to/vector-dir
```

For digest-addressed repositories (where `relative_path` is empty/absent in the manifest), pass the
repository root as `--base-dir`:

```bash
omnisstream-validate repo/objects/my-object/versions/<version>/manifest.pb --base-dir repo
```

The validator also accepts canonical JSON manifests (as produced in `test-vectors/*/manifest.json`):

```bash
omnisstream-validate path/to/manifest.json --base-dir path/to/vector-dir
```

## Exit codes

- `0`: valid
- `1`: invalid (validation or digest mismatch)
- `2`: usage / I/O error

## Tests

```bash
python -m unittest discover -s tools/validator/tests
```
