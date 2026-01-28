# OmnisStream Filesystem Repository Profile (v0.1.0)

This document is normative for the “filesystem repository” profile.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in RFC 2119.

## 1. Overview

This profile defines a filesystem layout for an OmnisStream repository that stores:

- **Objects** as manifests under `objects/`.
- **Parts** (stored payload bytes) in a content-addressed **PartStore** under `parts/`.

This profile is intended to make independent tools interoperate on a shared repository directory tree without requiring a database.

This profile does not define a network API. It is a concrete mapping from the manifest model in `MANIFEST_SPEC.md` to filesystem paths.

## 2. Identifiers

### 2.1 Part digest (`part_id`)

A part is identified by its `blake3-256` digest computed over the **stored payload bytes** (see `MANIFEST_SPEC.md` §2.2 and §8.5).

For this filesystem profile:

- The canonical on-disk encoding of a `blake3-256` digest is **lowercase hex**, exactly 64 characters (`[0-9a-f]{64}`).

### 2.2 `object_id`

`ObjectManifest.object_id` is a UTF-8 string in the manifest model.

For this filesystem profile, `object_id` MUST be representable as a safe relative path:

- It MUST NOT be absolute.
- It MUST NOT contain `.` or `..` path segments.

Tools MAY allow multi-segment `object_id` values (e.g., `datasets/run-001/object-a`) and treat them as nested directories under `objects/`.

### 2.3 `object_version`

An object may have multiple versions, each identified by an `object_version` directory name under `objects/<object_id>/versions/`.

For this filesystem profile:

- `object_version` MUST be a single path segment (i.e., it MUST NOT contain any path separators).
- `object_version` SHOULD be a stable, lowercase hex identifier.

Implementations MAY set `commit.commit_id = object_version`, but readers MUST treat `commit_id` as opaque.

## 3. Repository layout

### 3.1 Root

A repository root directory MUST contain:

- `objects/` — object manifests and version pointers.
- `parts/` — content-addressed stored payload bytes.

No other top-level directories are required by this profile.

### 3.2 PartStore layout (`parts/`)

The PartStore root is:

- `<repo_root>/parts/`

The PartStore MUST contain:

- `<repo_root>/parts/_tmp/` — a directory used for temporary files during atomic writes.

The canonical storage path for a part with digest `HH…` (64 hex characters) is:

- `<repo_root>/parts/<HH[0..2]>/<HH[2..4]>/<HH>`

For example, digest `aabbcc…` is stored at:

- `parts/aa/bb/aabbcc…`

Part files MUST be treated as immutable.

### 3.3 Object layout (`objects/`)

The objects root is:

- `<repo_root>/objects/`

For an `object_id`, the object directory is:

- `<repo_root>/objects/<object_id>/`

Within an object directory:

- `versions/` — directory containing one subdirectory per `object_version`.
- `latest` — optional file containing the selected `object_version`.

The canonical manifest path for a specific version is:

- `<repo_root>/objects/<object_id>/versions/<object_version>/manifest.pb`

The `latest` file, if present, MUST contain the selected `object_version` as UTF-8 text.

- Readers MUST trim leading/trailing ASCII whitespace when reading `latest`.
- If `latest` is absent, tools MAY select the lexicographically greatest `object_version` directory name as a best-effort fallback.

## 4. Resolving part bytes from a manifest

For each `PartMeta` in an Object Manifest:

- If `relative_path` is present and non-empty, the stored payload bytes MUST be read from `base_dir/relative_path` (per `MANIFEST_SPEC.md`).
- If `relative_path` is absent or empty, the stored payload bytes MUST be resolved via the PartStore:
  - Locate the `blake3-256` digest in `PartMeta.hashes`.
  - Compute the PartStore path per §3.2.
  - Read exactly `stored_length` bytes from that file.

## 5. Garbage collection (mark-and-sweep)

This profile supports offline garbage collection of unreferenced part files.

A GC implementation SHOULD:

1. **Mark:** scan all `manifest.pb` files under `objects/` and collect referenced `blake3-256` part digests where `relative_path` is absent/empty.
2. **Sweep:** list all part files under `parts/` (excluding `parts/_tmp/`) and delete those not present in the referenced set.

GC deletion is destructive; tools SHOULD default to a dry-run and require an explicit confirmation flag (e.g., `--force`) before deleting any files.

Implementations SHOULD NOT run GC concurrently with writers unless they enforce an exclusive repository lock or equivalent coordination, since a part may be in-flight (written but not yet referenced by any durable manifest).

## 6. Implementation notes (non-normative)

- **Durability barriers:** some implementations fsync per part, while others batch barriers (e.g., via `syncfs(2)` on Linux). Batching can improve throughput on high-latency filesystems but flushes the entire filesystem and is best used on dedicated mounts.
- **Compression trade-offs:** frame-based, seekable compression formats can significantly reduce storage size but may reduce small range-read throughput due to decompression work per frame.

