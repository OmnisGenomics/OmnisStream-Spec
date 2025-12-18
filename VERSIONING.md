# Versioning

The OmnisStream specification uses Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`.

## Spec versions

- **MAJOR** increments for incompatible changes in either the manifest semantics or wire formats.
- **MINOR** increments for backwards-compatible additions (new optional fields, new enum values, new validation rules that only reject previously-invalid manifests).
- **PATCH** increments for clarifications, errata, and non-normative improvements that do not change the set of valid manifests.

## Reader compatibility rule (required)

Readers and validators **MUST** support all **MINOR** versions within a supported **MAJOR** version.

To make this possible, a MINOR release MUST NOT:

- Add new required fields that make previously-valid manifests invalid.
- Change the meaning of existing fields.
- Remove or repurpose protobuf field numbers.

In practice, readers implement this by:

- Accepting unknown protobuf fields and preserving them when re-serializing.
- Treating unknown enum values as “unknown” and either rejecting only when the value is required for correctness, or validating using defaults per the spec.

## Manifest version field

`ObjectManifest.manifest_version` declares the manifest’s spec version.

- Producers MUST set a concrete `MAJOR.MINOR.PATCH` string (e.g. `0.1.0`).
- Readers MUST accept any manifest whose `MAJOR` matches, and MUST apply the rules for that `MAJOR` regardless of `MINOR/PATCH` (within the compatibility constraints above).

