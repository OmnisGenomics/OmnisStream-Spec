from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HashDigest:
    alg: str
    digest: bytes


@dataclass(frozen=True, slots=True)
class PartMeta:
    part_number: int
    offset: int
    length: int
    stored_length: int
    compression: str
    hashes: tuple[HashDigest, ...]
    relative_path: str | None
    tags: dict[str, str]
    extensions: dict[str, bytes]


@dataclass(frozen=True, slots=True)
class UploadSession:
    upload_id: str
    state: str
    created_unix_ms: int
    updated_unix_ms: int
    tags: dict[str, str]
    extensions: dict[str, bytes]


@dataclass(frozen=True, slots=True)
class CommitMeta:
    commit_id: str
    committed_unix_ms: int


@dataclass(frozen=True, slots=True)
class ObjectManifest:
    manifest_version: str
    object_id: str
    object_length: int
    parts: tuple[PartMeta, ...]
    upload_session: UploadSession | None
    commit: CommitMeta | None
    tags: dict[str, str]
    extensions: dict[str, bytes]

