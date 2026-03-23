#!/usr/bin/env python3
"""Validate that the current default mechanism doc appendix matches backend constants."""

from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT_DIR / "docs" / "backend-reading-mechanisms" / "iterator_v1.md"
BACKEND_DIR = ROOT_DIR / "reading-companion-backend"


def _normalized_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _load_doc_spec() -> dict:
    text = DOC_PATH.read_text(encoding="utf-8")
    heading = "## Machine-Readable Appendix"
    if heading not in text:
        raise RuntimeError(f"Missing '{heading}' in {DOC_PATH}.")

    appendix_text = text.split(heading, 1)[1]
    match = re.search(r"```json\s*(\{.*?\})\s*```", appendix_text, flags=re.DOTALL)
    if not match:
        raise RuntimeError(f"Could not find a fenced JSON appendix in {DOC_PATH}.")
    return json.loads(match.group(1))


def _load_backend_spec() -> dict:
    sys.path.insert(0, str(BACKEND_DIR))
    from src.iterator_reader.mechanism_spec import READER_MECHANISM_SPEC  # pylint: disable=import-error

    return json.loads(json.dumps(READER_MECHANISM_SPEC))


def _assert_same(label: str, left: dict, right: dict) -> None:
    if left == right:
        return
    diff = "\n".join(
        difflib.unified_diff(
            _normalized_json(left).splitlines(),
            _normalized_json(right).splitlines(),
            fromfile=f"{label}-left",
            tofile=f"{label}-right",
            lineterm="",
        )
    )
    raise RuntimeError(f"{label} drift detected.\n{diff}")


def main() -> int:
    doc_spec = _load_doc_spec()
    backend_spec = _load_backend_spec()

    _assert_same("doc-vs-backend", doc_spec, backend_spec)
    print("Reading mechanism document appendix matches backend mechanism constants.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
