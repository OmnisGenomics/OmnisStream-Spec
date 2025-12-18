from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnisstream_validate.load import load_manifest
from omnisstream_validate.validate import validate_manifest


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="omnisstream-validate")
    parser.add_argument("manifest", type=Path, help="Path to manifest (.pb or .json)")
    parser.add_argument("--base-dir", type=Path, required=True, help="Base directory for part payload paths")
    parser.add_argument(
        "--format",
        choices=["auto", "protobuf", "json"],
        default="auto",
        help="Manifest encoding (default: auto by file extension)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    try:
        manifest = load_manifest(args.manifest, fmt=args.format)
    except Exception as exc:
        print(f"error: failed to load manifest: {exc}", file=sys.stderr)
        raise SystemExit(2)

    errors = validate_manifest(manifest, base_dir=args.base_dir)
    if errors:
        for err in errors:
            print(f"invalid: {err}", file=sys.stderr)
        raise SystemExit(1)

    raise SystemExit(0)


if __name__ == "__main__":
    main()

