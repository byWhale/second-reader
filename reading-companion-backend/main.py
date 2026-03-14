"""CLI entry point for the Iterator-Reader architecture.

Usage:
  python main.py parse "book.epub"
  python main.py read "book.epub"
  python main.py read "book.epub" --chapter 3
  python main.py read "book.epub" --continue
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.iterator_reader import parse_book, read_book
from src.iterator_reader.language import language_name
from src.iterator_reader.storage import chapter_reference, structure_file, structure_markdown_file


def _require_book_path(book_file: str) -> Path:
    """Resolve and validate the input book path."""
    book_path = Path(book_file)
    if not book_path.exists():
        print(f"Error: File not found: {book_path}")
        sys.exit(1)
    return book_path


def _print_structure_overview(book_path: Path, structure: dict, output_dir: Path) -> None:
    """Print a readable summary after the outline parse completes."""
    print("=" * 60)
    print(f'书籍: {structure.get("book", book_path.stem)}')
    print(f'作者: {structure.get("author", "Unknown")}')
    print(f'书籍语言: {structure.get("book_language", "unknown")}')
    print(f'输出语言: {structure.get("output_language", "unknown")} ({language_name(structure.get("output_language", "en"))})')
    print(f'章节数: {len(structure.get("chapters", []))}')
    print(f"结构文件: {structure_file(output_dir)}")
    print(f"结构概览: {structure_markdown_file(output_dir)}")
    print("=" * 60)
    print("")
    print("结构概览：")
    for chapter in structure.get("chapters", []):
        segment_count = len(chapter.get("segments", []))
        suffix = f" ({segment_count} 个语义单元)" if segment_count > 0 else ""
        print(f'  {chapter_reference(chapter)} / {chapter.get("title")}{suffix}')
    print("")
    print("下一步：")
    print(f'  python main.py read "{book_path}"')
    print(f'  python main.py read "{book_path}" --continue')
    print(f'  python main.py read "{book_path}" --chapter 3')


def cmd_parse(args: argparse.Namespace) -> int:
    """Run the parse stage and persist structure.json."""
    book_path = _require_book_path(args.book_file)
    print(f"正在解析书籍结构: {book_path}")
    try:
        structure, output_dir = parse_book(book_path, language_mode=args.language, continue_mode=args.continue_mode)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    _print_structure_overview(book_path, structure, output_dir)
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    """Run the iterator-driven deep read stage."""
    book_path = _require_book_path(args.book_file)
    try:
        budget_policy = {
            "max_search_queries_per_segment": args.max_search_per_segment,
            "max_search_queries_per_chapter": args.max_search_per_chapter,
            "segment_timeout_seconds": args.segment_timeout,
            "max_revisions": args.max_revisions,
            "token_budget_ratio": args.token_budget_ratio,
            "slice_target_tokens": args.slice_target_tokens,
            "slice_max_tokens": args.slice_max_tokens,
            "slice_max_subsegments": args.slice_max_subsegments,
        }
        analysis_policy = {
            "deep_target_ratio": args.analysis_deep_target_ratio,
            "min_deep_per_chapter": args.analysis_min_deep_per_chapter,
            "max_core_claims": args.analysis_max_core_claims,
            "max_web_queries": args.analysis_max_web_queries,
            "max_queries_per_claim": args.analysis_max_queries_per_claim,
            "reuse_existing_notes": bool(args.analysis_reuse_existing_notes),
        }
        structure, output_dir, created = read_book(
            book_path,
            chapter_number=args.chapter,
            continue_mode=args.continue_mode,
            user_intent=args.intent,
            language_mode=args.language,
            read_mode=args.mode,
            skill_profile=args.skill_profile,
            budget_policy=budget_policy,
            analysis_policy=analysis_policy,
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    if created:
        print("")
        print(f"未发现已有结构，已自动生成: {structure_file(output_dir)}")
    print("")
    print(f"深读输出目录: {output_dir}")
    print(f'已完成章节: {sum(1 for ch in structure.get("chapters", []) if ch.get("status") == "done")}/{len(structure.get("chapters", []))}')
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Reading Companion - 阅读伴侣")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_parser = subparsers.add_parser("parse", help="解析书籍结构并生成 structure.json")
    parse_parser.add_argument("book_file", help="Path to the book file")
    parse_parser.add_argument(
        "--language",
        choices=["auto", "zh", "en"],
        default="auto",
        help="Output language for segmentation summaries (default: match the book language)",
    )
    parse_parser.add_argument(
        "--continue",
        dest="continue_mode",
        action="store_true",
        help="Resume structure parsing from the latest checkpoint when available",
    )
    parse_parser.set_defaults(func=cmd_parse)

    read_parser = subparsers.add_parser("read", help="按 Iterator-Reader 架构深读书籍")
    read_parser.add_argument("book_file", help="Path to the book file")
    read_parser.add_argument("--chapter", type=int, metavar="N", help="Only deep-read chapter N")
    read_parser.add_argument(
        "--continue",
        dest="continue_mode",
        action="store_true",
        help="Continue from pending/in-progress chapters and skip finished ones",
    )
    read_parser.add_argument(
        "--intent",
        help="Optional reading intent to steer the co-reader",
    )
    read_parser.add_argument(
        "--language",
        choices=["auto", "zh", "en"],
        default="auto",
        help="Output language for notes (default: match the book language)",
    )
    read_parser.add_argument(
        "--mode",
        choices=["sequential", "book_analysis"],
        default="sequential",
        help="Reader orchestration mode (default: sequential)",
    )
    read_parser.add_argument(
        "--skill-profile",
        choices=["balanced", "analytical", "curious", "quiet"],
        default="balanced",
        help="Pluggable reading skill profile (default: balanced)",
    )
    read_parser.add_argument(
        "--max-search-per-segment",
        type=int,
        default=2,
        metavar="N",
        help="Max curiosity tool calls per segment",
    )
    read_parser.add_argument(
        "--max-search-per-chapter",
        type=int,
        default=12,
        metavar="N",
        help="Max curiosity tool calls per chapter",
    )
    read_parser.add_argument(
        "--segment-timeout",
        type=int,
        default=120,
        metavar="SECONDS",
        help="Segment-level timeout budget in seconds",
    )
    read_parser.add_argument(
        "--max-revisions",
        type=int,
        default=2,
        metavar="N",
        help="Max reflection-driven revise loops per segment",
    )
    read_parser.add_argument(
        "--token-budget-ratio",
        type=float,
        default=1.5,
        metavar="RATIO",
        help="Token-driven depth ratio (higher = deeper per-segment processing)",
    )
    read_parser.add_argument(
        "--slice-target-tokens",
        type=int,
        default=420,
        metavar="N",
        help="Target token size for dynamic sub-segment slicing",
    )
    read_parser.add_argument(
        "--slice-max-tokens",
        type=int,
        default=700,
        metavar="N",
        help="Trigger slicing when a segment exceeds this token estimate",
    )
    read_parser.add_argument(
        "--slice-max-subsegments",
        type=int,
        default=4,
        metavar="N",
        help="Maximum dynamic sub-segments produced from one semantic segment",
    )
    read_parser.add_argument(
        "--analysis-deep-target-ratio",
        type=float,
        default=0.30,
        metavar="RATIO",
        help="Share of segments selected for deep-read during book_analysis mode",
    )
    read_parser.add_argument(
        "--analysis-min-deep-per-chapter",
        type=int,
        default=1,
        metavar="N",
        help="Minimum deep-read targets per non-low-value chapter in book_analysis mode",
    )
    read_parser.add_argument(
        "--analysis-max-core-claims",
        type=int,
        default=20,
        metavar="N",
        help="Maximum number of core claims in the final book analysis report",
    )
    read_parser.add_argument(
        "--analysis-max-web-queries",
        type=int,
        default=18,
        metavar="N",
        help="Maximum number of web verification queries in book_analysis mode",
    )
    read_parser.add_argument(
        "--analysis-max-queries-per-claim",
        type=int,
        default=2,
        metavar="N",
        help="Maximum number of verification queries per claim",
    )
    read_parser.add_argument(
        "--analysis-reuse-existing-notes",
        type=int,
        choices=[0, 1],
        default=1,
        metavar="0|1",
        help="Reuse existing chapter deep-read notes when possible (1=yes, 0=no)",
    )
    read_parser.set_defaults(func=cmd_read)

    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
