from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from omnisstream_validate.hashes import blake3_256, crc32c_be
from omnisstream_validate.model import HashDigest, ObjectManifest


_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_EXT_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


def _is_safe_relative_path(rel: str) -> bool:
    p = PurePosixPath(rel)
    if p.is_absolute():
        return False
    if rel == "":
        return False
    for part in p.parts:
        if part in {"..", "."}:
            return False
    return True


def _resolve_under_base(base_dir: Path, rel: str) -> Path:
    base = base_dir.resolve()
    target = (base / rel).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"relative_path escapes base-dir: {rel}")
    return target


def _digest_map(hashes: tuple[HashDigest, ...]) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for h in hashes:
        out.setdefault(h.alg, h.digest)
    return out


def validate_manifest(manifest: ObjectManifest, base_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not base_dir.exists() or not base_dir.is_dir():
        issues.append(ValidationIssue(f"base-dir is not a directory: {base_dir}"))
        return issues

    if not _SEMVER_RE.match(manifest.manifest_version or ""):
        issues.append(ValidationIssue("manifest_version must be SemVer MAJOR.MINOR.PATCH"))

    if not manifest.object_id:
        issues.append(ValidationIssue("object_id must be non-empty"))

    # Validate tags/extensions key constraints (best-effort).
    for k in manifest.tags.keys():
        if not _EXT_KEY_RE.match(k):
            issues.append(ValidationIssue(f"invalid tag key: {k}"))
    for k in manifest.extensions.keys():
        if not _EXT_KEY_RE.match(k):
            issues.append(ValidationIssue(f"invalid extension key: {k}"))

    if not manifest.parts:
        issues.append(ValidationIssue("parts must be non-empty"))
        return issues

    required_algs = {"crc32c", "blake3-256"}
    seen_part_numbers: set[int] = set()
    expected_offset = 0

    for idx, part in enumerate(manifest.parts):
        if part.part_number <= 0:
            issues.append(ValidationIssue(f"parts[{idx}].part_number must be > 0"))
        elif part.part_number in seen_part_numbers:
            issues.append(ValidationIssue(f"duplicate part_number: {part.part_number}"))
        else:
            seen_part_numbers.add(part.part_number)

        if part.length <= 0:
            issues.append(ValidationIssue(f"parts[{idx}].length must be > 0"))
        if part.stored_length <= 0:
            issues.append(ValidationIssue(f"parts[{idx}].stored_length must be > 0"))

        if part.compression == "unspecified":
            issues.append(ValidationIssue(f"parts[{idx}].compression must not be unspecified"))

        if part.offset != expected_offset:
            issues.append(
                ValidationIssue(
                    f"parts[{idx}].offset must be contiguous; expected {expected_offset}, got {part.offset}"
                )
            )
        expected_offset = part.offset + (part.length if part.length > 0 else 0)

        if part.compression == "none" and part.stored_length != part.length:
            issues.append(
                ValidationIssue(
                    f"parts[{idx}] compression=none requires stored_length==length (got {part.stored_length} vs {part.length})"
                )
            )

        for k in part.tags.keys():
            if not _EXT_KEY_RE.match(k):
                issues.append(ValidationIssue(f"parts[{idx}] invalid tag key: {k}"))
        for k in part.extensions.keys():
            if not _EXT_KEY_RE.match(k):
                issues.append(ValidationIssue(f"parts[{idx}] invalid extension key: {k}"))

        digest_map = _digest_map(part.hashes)
        missing = [a for a in sorted(required_algs) if a not in digest_map]
        if missing:
            issues.append(ValidationIssue(f"parts[{idx}] missing required hashes: {', '.join(missing)}"))

        for alg in required_algs:
            count = sum(1 for h in part.hashes if h.alg == alg)
            if count > 1:
                issues.append(ValidationIssue(f"parts[{idx}] duplicate hash entries for alg={alg}"))

        if "crc32c" in digest_map and len(digest_map["crc32c"]) != 4:
            issues.append(ValidationIssue(f"parts[{idx}] crc32c digest must be 4 bytes"))
        if "blake3-256" in digest_map and len(digest_map["blake3-256"]) != 32:
            issues.append(ValidationIssue(f"parts[{idx}] blake3-256 digest must be 32 bytes"))

        payload_path: Path | None = None
        if part.relative_path is not None:
            if not _is_safe_relative_path(part.relative_path):
                issues.append(
                    ValidationIssue(
                        f"parts[{idx}] relative_path is not a safe relative path: {part.relative_path}"
                    )
                )
                continue

            try:
                payload_path = _resolve_under_base(base_dir, part.relative_path)
            except Exception as exc:
                issues.append(ValidationIssue(f"parts[{idx}] invalid relative_path: {exc}"))
                continue
        else:
            # Digest-addressed PartStore resolution (filesystem repository profile).
            b3 = digest_map.get("blake3-256")
            if b3 is None or len(b3) != 32:
                continue

            hex_digest = b3.hex()
            payload_path = (
                base_dir
                / "parts"
                / hex_digest[0:2]
                / hex_digest[2:4]
                / hex_digest
            )
        if not payload_path.exists():
            if part.relative_path is not None:
                issues.append(
                    ValidationIssue(f"parts[{idx}] payload missing: {part.relative_path}")
                )
            else:
                issues.append(
                    ValidationIssue(
                        f"parts[{idx}] partstore payload missing: {payload_path.relative_to(base_dir)}"
                    )
                )
            continue

        payload = payload_path.read_bytes()
        if len(payload) != part.stored_length:
            issues.append(
                ValidationIssue(
                    f"parts[{idx}] stored_length mismatch: manifest={part.stored_length} actual={len(payload)}"
                )
            )
            continue

        computed_crc = crc32c_be(payload)
        computed_b3 = blake3_256(payload)
        if "crc32c" in digest_map and digest_map["crc32c"] != computed_crc:
            issues.append(ValidationIssue(f"parts[{idx}] crc32c mismatch"))
        if "blake3-256" in digest_map and digest_map["blake3-256"] != computed_b3:
            issues.append(ValidationIssue(f"parts[{idx}] blake3-256 mismatch"))

    if manifest.object_length != expected_offset:
        issues.append(ValidationIssue(f"object_length mismatch: manifest={manifest.object_length} expected={expected_offset}"))

    return issues
