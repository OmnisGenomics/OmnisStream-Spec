# Canonical JSON Form (v0.1.0)

This document defines a canonical JSON representation for the v0.1.0 Object Manifest model described in `MANIFEST_SPEC.md`.

The goal is that two independent implementations produce **byte-for-byte identical** UTF-8 JSON for the same logical manifest.

## 1. Encoding

- The canonical form MUST be encoded as UTF-8.
- The canonical form MUST NOT include a UTF-8 BOM.
- The canonical form MUST NOT include insignificant whitespace (no spaces, tabs, or newlines outside of JSON strings).

## 2. JSON Types

- Strings are UTF-8 strings as defined by JSON.
- Integers MUST be encoded as JSON numbers in base-10 without exponent notation.
- Floating point numbers MUST NOT appear.
- Byte sequences MUST be encoded as base64 strings (see §4).

### 2.1 Integer formatting and range

For all integer fields (`object_length`, `offset`, `length`, `stored_length`, `part_number`):

- Values MUST be non-negative.
- Values MUST be serialized as the shortest base-10 form (no leading zeros, except `0`).
- Values MUST be within the range of unsigned integers for their corresponding schema type:
  - `uint32`: `0` to `4294967295`
  - `uint64`: `0` to `18446744073709551615`

## 3. Object Key Ordering

All JSON objects in canonical form MUST order keys in strictly increasing lexicographic order by **ASCII byte value** of the UTF-8 encoding of the key.

This is well-defined because all keys in the canonical manifest JSON are restricted to ASCII:

- Schema-defined keys are ASCII literals.
- `tags`/`extensions` keys are constrained by `MANIFEST_SPEC.md` (§4.1) to an ASCII subset.

## 4. Bytes and Base64

All byte values MUST be encoded using RFC 4648 “base64” (not base64url):

- The alphabet MUST be `A–Z a–z 0–9 + /`.
- Padding (`=`) MUST be included.
- No line breaks are permitted.

## 5. Enums

Enum values MUST be encoded as lowercase strings:

### 5.1 Hash algorithms

- `crc32c`
- `blake3-256`

### 5.2 Compression

- `none`
- `zstd-seekable`
- `bgzf`

## 6. Canonical JSON Shape

The canonical JSON object for an Object Manifest MUST have the following keys (and MUST NOT include unknown top-level keys):

- `commit` (optional object)
- `extensions` (optional object of base64 strings)
- `manifest_version` (string)
- `object_id` (string)
- `object_length` (integer)
- `parts` (array)
- `tags` (optional object of strings)
- `upload_session` (optional object)

Unknown keys are prohibited in canonical JSON so that canonicalization is fully deterministic. (Wire formats like protobuf MAY carry unknown fields; those are not representable in canonical JSON.)

### 6.1 `parts`

`parts` MUST be an array of objects. Each part object MUST have the following keys (and MUST NOT include unknown keys):

- `compression` (string enum)
- `extensions` (optional object of base64 strings)
- `hashes` (array)
- `length` (integer)
- `offset` (integer)
- `part_number` (integer)
- `relative_path` (optional string)
- `stored_length` (integer)
- `tags` (optional object of strings)

### 6.2 `hashes`

`hashes` MUST be an array of objects with keys:

- `alg` (string enum)
- `digest_b64` (string)

For canonical form, the `hashes` array MUST be sorted by `alg` ascending (ASCII lexicographic).

## 7. Example (canonical)

The following is an example canonical JSON manifest (line breaks added here for readability; canonical output MUST be minified):

```json
{
  "manifest_version":"0.1.0",
  "object_id":"example-object",
  "object_length":12,
  "parts":[
    {
      "compression":"none",
      "hashes":[
        {"alg":"blake3-256","digest_b64":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="},
        {"alg":"crc32c","digest_b64":"AAAAAA=="}
      ],
      "length":5,
      "offset":0,
      "part_number":1,
      "relative_path":"parts/part-0001.bin",
      "stored_length":5
    }
  ]
}
```

