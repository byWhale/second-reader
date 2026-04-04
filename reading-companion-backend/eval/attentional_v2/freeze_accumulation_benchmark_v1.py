"""Freeze the current draft accumulation probes into a frozen-draft dataset."""

from __future__ import annotations

import argparse
import json

from .accumulation_benchmark_v1 import write_frozen_probe_dataset


def main() -> int:
    _ = argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(write_frozen_probe_dataset(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
