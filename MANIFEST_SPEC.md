# OmnisStream Manifest Specification (v0.1.0)

This document is normative.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in RFC 2119.

## 1. Overview

An **Object Manifest** describes a single object as an ordered sequence of **Parts**, including integrity metadata required to validate and resume uploads safely.

This spec defines:

- Terms and invariants for objects/parts and upload sessions.
- Required hash algorithms and their encodings.
- Crash-safe, atomic “finalize” semantics for writing manifests.
- Resume semantics for idempotent part upload and commit replay.

The canonical wire schema for this spec is `proto/omnisstream/v1/manifest.proto`.

## 2. Terms

### 2.1 Object

An **Object** is an ordered byte sequence of length `object_length` bytes.

An object is identified by `object_id`, which MUST be a non-empty UTF-8 string. Producers SHOULD treat it as an opaque identifier.

### 2.2 Part

A **Part** is a contiguous slice of the Object’s byte sequence.

Each part is described by:

- `offset`: the starting byte offset in the object.
- `length`: the number of logical bytes in the object covered by the part.
- `stored_length`: the number of bytes in the stored payload for this part.
- `compression`: a declared encoding of the stored payload bytes.
- `hashes`: integrity digests of the stored payload bytes.

Unless otherwise specified, hashes in this spec are computed over the **stored payload bytes** (i.e., the exact bytes written/transmitted for the part).

### 2.3 Upload Session

An **Upload Session** groups a set of part uploads for a single object under an `upload_id`.

An upload session has a `state` in `{PENDING, COMPLETE, ABORTED}` (see §7).

### 2.4 Commit

A **Commit** is the operation that transitions an upload session from `PENDING` to `COMPLETE` by durably recording an Object Manifest.

Commits MUST be atomic with respect to readers: a reader MUST observe either the previous complete state (no manifest or an older manifest) or the new complete manifest, never a partially-written manifest.

## 3. Data Model

### 3.1 ObjectManifest

An Object Manifest has these fields:

- `manifest_version` (string, REQUIRED): SemVer `MAJOR.MINOR.PATCH` identifying the manifest spec version.
- `object_id` (string, REQUIRED): object identifier.
- `object_length` (uint64, REQUIRED): total logical length in bytes.
- `parts` (array of `PartMeta`, REQUIRED): ordered part metadata.
- `upload_session` (object, OPTIONAL): upload session metadata.
- `commit` (object, OPTIONAL): commit metadata.
- `tags` (map<string,string>, OPTIONAL): human-readable metadata.
- `extensions` (map<string,bytes>, OPTIONAL): uninterpreted extension payloads.

### 3.2 PartMeta

Each `PartMeta` has these fields:

- `part_number` (uint32, REQUIRED): stable identifier used for idempotency and replay safety.
- `offset` (uint64, REQUIRED): starting logical offset in the object.
- `length` (uint64, REQUIRED): logical length of this part in bytes.
- `stored_length` (uint64, REQUIRED): number of bytes in the stored payload.
- `compression` (enum, REQUIRED): compression/encoding of the stored payload.
- `hashes` (array of `HashDigest`, REQUIRED): integrity digests of the stored payload bytes.
- `relative_path` (string, OPTIONAL): path to the stored payload bytes, relative to a base directory.
  - If `relative_path` is present and non-empty, the stored payload bytes for this part are located at `base_dir/relative_path`.
  - If `relative_path` is absent or empty, the stored payload bytes MUST be resolved out-of-band (e.g., via a content-addressed PartStore keyed by the part’s `blake3-256` hash; see `REPOSITORY_SPEC.md`).
- `tags` (map<string,string>, OPTIONAL)
- `extensions` (map<string,bytes>, OPTIONAL)

### 3.3 HashDigest

Each `HashDigest` has:

- `alg` (enum, REQUIRED): hash algorithm identifier.
- `digest` (bytes, REQUIRED): raw digest bytes whose length depends on the algorithm.

Recognized `alg` values in v0.1.0:

- `crc32c` — CRC-32C (Castagnoli), digest length MUST be 4 bytes.
- `blake3-256` — BLAKE3 unkeyed hash, digest length MUST be 32 bytes.

For `crc32c`, the 4 digest bytes MUST be encoded in big-endian (network) order (most significant byte first).

### 3.4 Compression

Recognized `compression` values in v0.1.0:

- `none` — stored payload bytes equal the object bytes for this part.
- `zstd-seekable` — stored payload bytes are Zstandard in a seekable framing format.
- `bgzf` — stored payload bytes are BGZF (Blocked GNU Zip Format).

This spec names these codecs; it does not require a specific library.
Readers MAY encounter unknown compression identifiers in future minor versions; unknown identifiers MUST be treated as opaque encodings (i.e., only `none` has special validation semantics in v0.1.0).

## 4. Extension Mechanism

Both `ObjectManifest` and `PartMeta` support:

- `tags: map<string,string>` for small, human-readable metadata.
- `extensions: map<string,bytes>` for uninterpreted binary payloads.

### 4.1 Key constraints

Extension keys and tag keys:

- MUST be non-empty UTF-8 strings.
- MUST match the regex `^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$` (ASCII subset for stable canonical ordering).

### 4.2 Processing rules

- Producers MAY add any keys not defined by this spec.
- Readers/validators MUST ignore unknown `tags` and unknown `extensions` keys for the purposes of validation, unless a higher-level profile explicitly requires them.
- Readers/validators SHOULD preserve unknown keys when translating between encodings (e.g., protobuf ↔ canonical JSON).

## 5. Atomic Finalize Semantics (Durable Manifest Write)

When writing a manifest to a filesystem path `final_path`, an implementation MUST make the write crash-safe and atomic.

If `final_path` is on a POSIX filesystem that supports atomic rename, a compliant implementation MUST:

1. Serialize the manifest bytes to a temporary file `tmp_path` in the **same directory** as `final_path`.
2. `fsync(tmp_path)` (or equivalent) to ensure file content is durable.
3. `fsync(parent_dir(final_path))` after creating `tmp_path` if the platform requires it for durable directory entries.
4. Atomically rename `tmp_path` to `final_path` (e.g., `rename(2)`).
5. `fsync(parent_dir(final_path))` after the rename to ensure the rename is durable.

Implementations MUST NOT write directly to `final_path` in-place.

If the platform does not provide the primitives required for atomic rename durability, the implementation MUST document its durability limitations and SHOULD offer an equivalent best-effort mechanism.

## 6. Resume Semantics

Resume semantics are defined in terms of three abstract operations:

- `BeginUpload(object_id) -> upload_id`
- `PutPart(upload_id, part_number, offset, payload_bytes, metadata...)`
- `Commit(upload_id, manifest)`

### 6.1 `upload_id`

- `upload_id` MUST be globally unique within the server’s retention window.
- `upload_id` MUST be treated as an opaque string by clients.

### 6.2 Idempotent `PutPart`

For a fixed tuple `(upload_id, part_number)`, the server MUST enforce idempotency:

- Repeating the same `PutPart` with identical `offset`, `length`, `stored_length`, `compression`, and identical payload bytes MUST succeed and MUST NOT create duplicate stored state.
- If a repeated `PutPart` for the same `(upload_id, part_number)` differs in any of those properties, the server MUST reject it (conflict).

Servers MAY additionally enforce idempotency over `(upload_id, offset)` but MUST at minimum enforce it over `(upload_id, part_number)`.

### 6.3 Replay rules

Clients MAY re-upload any subset of parts during retry/resume.

Servers MUST:

- Reject conflicting replays (see §6.2).
- Allow safe “at least once” retry behavior.

### 6.4 Idempotent `Commit`

For a fixed `upload_id`:

- If `Commit` is repeated with a manifest byte-for-byte identical to a previously successful commit, the server MUST return success.
- If `Commit` is repeated with a different manifest, the server MUST reject it (conflict) or return an explicit “already committed” response that includes the committed manifest identity.

## 7. Crash/Recovery State Machine

Upload sessions have three states:

- `PENDING`: parts MAY be uploaded; manifest is not finalized.
- `COMPLETE`: manifest has been finalized and is durable; the object is readable.
- `ABORTED`: session is permanently closed; no further parts or commits are accepted.

### 7.1 State transitions

- `BeginUpload` creates a session in `PENDING`.
- `Commit` transitions `PENDING -> COMPLETE` if and only if the manifest is valid (see §8) and the finalize procedure succeeds (§5).
- `Abort` transitions `PENDING -> ABORTED`.
- `Abort` MUST be idempotent.
- `Commit` against an `ABORTED` session MUST fail.

### 7.2 Crash recovery rules

On recovery after a crash, implementations MUST determine session state from durable artifacts:

- If the finalized manifest at `final_path` exists and is valid (§8), the session MUST be treated as `COMPLETE`.
- If only `tmp_path` exists (no finalized manifest), the session MUST be treated as `PENDING` and `tmp_path` MAY be deleted.
- If neither exists, the session MUST be treated as `PENDING` (unless the server separately recorded `ABORTED`).

## 8. Validation Rules (Manifest Validity)

A manifest is **valid** if and only if all rules in this section are satisfied.

### 8.1 Versioning

- `manifest_version` MUST be a valid SemVer string of the form `MAJOR.MINOR.PATCH` where each component is a non-negative integer with no leading `+` sign.
- For this document, producers SHOULD emit `manifest_version = "0.1.0"`.
- Readers MUST accept any manifest whose `MAJOR` matches a supported major version (see `VERSIONING.md`).

### 8.2 Required fields and basic constraints

- `object_id` MUST be present and non-empty.
- `object_length` MUST be present and MAY be zero only if `parts` is empty (v0.1.0 RECOMMENDS `parts` be non-empty; see §8.3).
- If `parts` is present, it MUST contain at least one element in v0.1.0.

For every `PartMeta`:

- `part_number` MUST be present and MUST be > 0.
- `offset` MUST be present.
- `length` MUST be present and MUST be > 0.
- `stored_length` MUST be present and MUST be > 0.
- `compression` MUST NOT be `unspecified`.
- Producers SHOULD use one of the recognized values (§3.4).
- Readers/validators MAY accept unknown (non-`unspecified`) compression identifiers.
- `relative_path`, if present and non-empty, MUST be a relative path (it MUST NOT be absolute and MUST NOT contain `..` path segments).

### 8.3 Part ordering and coverage invariants

Let `parts` be the manifest’s part list in order.

- `parts` MUST be sorted by strictly increasing `offset`.
- `parts[0].offset` MUST equal 0.
- Parts MUST NOT overlap: for all adjacent pairs `(p_i, p_{i+1})`, `p_i.offset + p_i.length` MUST be <= `p_{i+1}.offset`.
- In v0.1.0, parts MUST be contiguous (no gaps): for all adjacent pairs `(p_i, p_{i+1})`, `p_i.offset + p_i.length` MUST equal `p_{i+1}.offset`.
- `object_length` MUST equal `parts[last].offset + parts[last].length`.

### 8.4 Compression invariants

For each part:

- If `compression == none`, then `stored_length` MUST equal `length`.
- If `compression != none`, then `stored_length` MAY differ from `length`.

### 8.5 Hash requirements

For each part:

- `hashes` MUST include exactly one `crc32c` digest and exactly one `blake3-256` digest.
- Additional hash entries MAY be present. Readers/validators MUST ignore unknown hash algorithms for the purposes of v0.1.0 validity (but SHOULD preserve them when translating encodings).
- `crc32c.digest` MUST be exactly 4 bytes.
- `blake3-256.digest` MUST be exactly 32 bytes.
- Hash digests MUST be computed over the stored payload bytes for the part.

### 8.6 Extensions and tags

- Keys MUST follow §4.1.
- Duplicate keys are not representable in maps and MUST NOT appear.

### 8.7 Numeric ranges

All numeric fields are non-negative.

Implementations SHOULD reject values that do not fit within unsigned 64-bit integers for `offset/length/stored_length/object_length`, and unsigned 32-bit for `part_number`.
