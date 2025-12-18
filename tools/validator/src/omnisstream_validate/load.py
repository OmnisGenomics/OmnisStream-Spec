from __future__ import annotations

import base64
import json
from pathlib import Path

from omnisstream_validate.model import CommitMeta, HashDigest, ObjectManifest, PartMeta, UploadSession

try:
    from omnisstream.v1 import manifest_pb2  # type: ignore
except Exception:  # pragma: no cover
    manifest_pb2 = None


def _fmt_from_path(path: Path) -> str:
    return "json" if path.suffix.lower() == ".json" else "protobuf"


def _b64_decode(s: str) -> bytes:
    return base64.b64decode(s, validate=True)


def _compression_name_from_proto(value: int) -> str:
    if value == 0:
        return "unspecified"
    if value == getattr(manifest_pb2, "COMPRESSION_ALGORITHM_NONE", 1):
        return "none"
    if value == getattr(manifest_pb2, "COMPRESSION_ALGORITHM_ZSTD_SEEKABLE", 2):
        return "zstd-seekable"
    if value == getattr(manifest_pb2, "COMPRESSION_ALGORITHM_BGZF", 3):
        return "bgzf"
    return f"unknown({value})"


def _hash_alg_name_from_proto(value: int) -> str:
    if value == 0:
        return "unspecified"
    if value == getattr(manifest_pb2, "HASH_ALGORITHM_CRC32C", 1):
        return "crc32c"
    if value == getattr(manifest_pb2, "HASH_ALGORITHM_BLAKE3_256", 2):
        return "blake3-256"
    return f"unknown({value})"


def _session_state_name_from_proto(value: int) -> str:
    if value == 0:
        return "unspecified"
    if value == getattr(manifest_pb2, "UPLOAD_SESSION_STATE_PENDING", 1):
        return "pending"
    if value == getattr(manifest_pb2, "UPLOAD_SESSION_STATE_COMPLETE", 2):
        return "complete"
    if value == getattr(manifest_pb2, "UPLOAD_SESSION_STATE_ABORTED", 3):
        return "aborted"
    return f"unknown({value})"


def _as_str_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in value.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


def _as_bytes_map_b64(value: object) -> dict[str, bytes]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, bytes] = {}
    for k, v in value.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = _b64_decode(v)
    return out


def _from_protobuf(path: Path) -> ObjectManifest:
    if manifest_pb2 is None:
        raise RuntimeError("protobuf module import failed (did you install tools/validator?)")

    msg = manifest_pb2.ObjectManifest()
    msg.ParseFromString(path.read_bytes())

    upload_session: UploadSession | None = None
    if msg.HasField("upload_session"):
        s = msg.upload_session
        upload_session = UploadSession(
            upload_id=str(s.upload_id),
            state=_session_state_name_from_proto(int(s.state)),
            created_unix_ms=int(s.created_unix_ms),
            updated_unix_ms=int(s.updated_unix_ms),
            tags=dict(s.tags),
            extensions=dict(s.extensions),
        )

    commit: CommitMeta | None = None
    if msg.HasField("commit"):
        c = msg.commit
        commit = CommitMeta(commit_id=str(c.commit_id), committed_unix_ms=int(c.committed_unix_ms))

    parts: list[PartMeta] = []
    for p in msg.parts:
        hashes = tuple(HashDigest(alg=_hash_alg_name_from_proto(int(h.alg)), digest=bytes(h.digest)) for h in p.hashes)
        parts.append(
            PartMeta(
                part_number=int(p.part_number),
                offset=int(p.offset),
                length=int(p.length),
                stored_length=int(p.stored_length),
                compression=_compression_name_from_proto(int(p.compression)),
                hashes=hashes,
                relative_path=str(p.relative_path) if p.relative_path else None,
                tags=dict(p.tags),
                extensions=dict(p.extensions),
            )
        )

    return ObjectManifest(
        manifest_version=str(msg.manifest_version),
        object_id=str(msg.object_id),
        object_length=int(msg.object_length),
        parts=tuple(parts),
        upload_session=upload_session,
        commit=commit,
        tags=dict(msg.tags),
        extensions=dict(msg.extensions),
    )


def _from_json(path: Path) -> ObjectManifest:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("top-level JSON value must be an object")

    def req_str(key: str) -> str:
        v = obj.get(key)
        if not isinstance(v, str) or not v:
            raise ValueError(f"{key} must be a non-empty string")
        return v

    def req_int(key: str) -> int:
        v = obj.get(key)
        if not isinstance(v, int) or v < 0:
            raise ValueError(f"{key} must be a non-negative integer")
        return v

    parts_val = obj.get("parts")
    if not isinstance(parts_val, list):
        raise ValueError("parts must be an array")

    parts: list[PartMeta] = []
    for i, p in enumerate(parts_val):
        if not isinstance(p, dict):
            raise ValueError(f"parts[{i}] must be an object")

        hashes_val = p.get("hashes")
        if not isinstance(hashes_val, list):
            raise ValueError(f"parts[{i}].hashes must be an array")
        hashes: list[HashDigest] = []
        for j, h in enumerate(hashes_val):
            if not isinstance(h, dict):
                raise ValueError(f"parts[{i}].hashes[{j}] must be an object")
            alg = h.get("alg")
            digest_b64 = h.get("digest_b64")
            if not isinstance(alg, str) or not isinstance(digest_b64, str):
                raise ValueError(f"parts[{i}].hashes[{j}] must have alg and digest_b64 strings")
            hashes.append(HashDigest(alg=alg, digest=_b64_decode(digest_b64)))

        rel = p.get("relative_path")
        rel_out = rel if isinstance(rel, str) and rel else None

        parts.append(
            PartMeta(
                part_number=int(p.get("part_number") or 0),
                offset=int(p.get("offset") or 0),
                length=int(p.get("length") or 0),
                stored_length=int(p.get("stored_length") or 0),
                compression=str(p.get("compression") or "unspecified"),
                hashes=tuple(hashes),
                relative_path=rel_out,
                tags=_as_str_map(p.get("tags")),
                extensions=_as_bytes_map_b64(p.get("extensions")),
            )
        )

    sess_obj = obj.get("upload_session")
    upload_session: UploadSession | None = None
    if isinstance(sess_obj, dict) and isinstance(sess_obj.get("upload_id"), str) and sess_obj["upload_id"]:
        upload_session = UploadSession(
            upload_id=sess_obj["upload_id"],
            state=str(sess_obj.get("state") or "unspecified"),
            created_unix_ms=int(sess_obj.get("created_unix_ms") or 0),
            updated_unix_ms=int(sess_obj.get("updated_unix_ms") or 0),
            tags=_as_str_map(sess_obj.get("tags")),
            extensions=_as_bytes_map_b64(sess_obj.get("extensions")),
        )

    commit_obj = obj.get("commit")
    commit: CommitMeta | None = None
    if isinstance(commit_obj, dict) and isinstance(commit_obj.get("commit_id"), str) and commit_obj["commit_id"]:
        commit = CommitMeta(
            commit_id=commit_obj["commit_id"],
            committed_unix_ms=int(commit_obj.get("committed_unix_ms") or 0),
        )

    return ObjectManifest(
        manifest_version=req_str("manifest_version"),
        object_id=req_str("object_id"),
        object_length=req_int("object_length"),
        parts=tuple(parts),
        upload_session=upload_session,
        commit=commit,
        tags=_as_str_map(obj.get("tags")),
        extensions=_as_bytes_map_b64(obj.get("extensions")),
    )


def load_manifest(path: Path, fmt: str = "auto") -> ObjectManifest:
    if not path.exists():
        raise FileNotFoundError(str(path))

    resolved = _fmt_from_path(path) if fmt == "auto" else fmt
    if resolved == "protobuf":
        return _from_protobuf(path)
    if resolved == "json":
        return _from_json(path)
    raise ValueError(f"unknown format: {fmt}")

