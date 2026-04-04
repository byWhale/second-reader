"""Build the deterministic draft artifacts for accumulation benchmark v1."""

from __future__ import annotations

import argparse
import json

from .accumulation_benchmark_v1 import write_draft_artifacts


def main() -> int:
    _ = argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(write_draft_artifacts(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
