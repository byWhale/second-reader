"""Run attentional_v2 structural integrity checks over one persisted output directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.attentional_v2.evaluation import build_normalized_eval_bundle, persist_normalized_eval_bundle, run_mechanism_integrity_checks


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the attentional_v2 integrity runner."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", help="Book output directory that contains _runtime/ and _mechanisms/attentional_v2/")
    parser.add_argument(
        "--persist-normalized-bundle",
        action="store_true",
        help="Persist _mechanisms/attentional_v2/exports/normalized_eval_bundle.json for the evaluated output directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the integrity report and print JSON to stdout."""

    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir).resolve()
    if args.persist_normalized_bundle:
        persist_normalized_eval_bundle(
            output_dir,
            config_payload={"runner": "eval.attentional_v2.run_integrity"},
        )
    else:
        build_normalized_eval_bundle(
            output_dir,
            config_payload={"runner": "eval.attentional_v2.run_integrity"},
        )
    report = run_mechanism_integrity_checks(output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
