#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${ROOT_DIR}/proto"
OUT_DIR="${ROOT_DIR}/.protoc-out"

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

protoc \
  -I "${PROTO_DIR}" \
  --include_imports \
  --descriptor_set_out="${OUT_DIR}/omnisstream.desc" \
  "${PROTO_DIR}/omnisstream/v1/manifest.proto"

echo "OK: wrote ${OUT_DIR}/omnisstream.desc"

