from __future__ import annotations

import json
from pathlib import Path

from src.iterator_reader.storage import chapter_result_file, structure_file
from src.reading_mechanisms import iterator_v1 as module


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_iterator_output(tmp_path: Path, *, anchor_quote: str, segment_text: str = "Alpha beta gamma") -> Path:
    output_dir = tmp_path / "iterator-output"
    chapter = {
        "id": 1,
        "title": "Full Content",
        "chapter_number": 1,
        "status": "done",
        "segments": [
            {
                "id": "1.1",
                "segment_ref": "Full_Content.1",
                "text": segment_text,
                "locator": {"paragraph_start": 1, "paragraph_end": 1},
                "paragraph_locators": [
                    {
                        "href": "",
                        "start_cfi": None,
                        "end_cfi": None,
                        "paragraph_index": 1,
                        "text": segment_text,
                    }
                ],
            }
        ],
    }
    structure = {
        "book": "Demo",
        "author": "Tester",
        "book_language": "en",
        "output_language": "en",
        "source_file": "demo.txt",
        "output_dir": str(output_dir),
        "chapters": [chapter],
    }
    _write_json(structure_file(output_dir), structure)
    _write_json(
        output_dir / "public" / "book_document.json",
        {
            "book": "Demo",
            "chapters": [
                {
                    "id": 1,
                    "title": "Full Content",
                    "paragraphs": [
                        {
                            "paragraph_index": 1,
                            "text": segment_text,
                        }
                    ],
                }
            ],
        },
    )
    _write_json(
        chapter_result_file(output_dir, chapter),
        {
            "chapter": {"reference": "Full Content"},
            "sections": [
                {
                    "segment_ref": "Full_Content.1",
                    "reactions": [
                        {
                            "reaction_id": "r1",
                            "type": "highlight",
                            "anchor_quote": anchor_quote,
                            "content": "reaction",
                            "target_locator": {
                                "match_text": anchor_quote,
                                "match_mode": "exact",
                            },
                        }
                    ],
                }
            ],
        },
    )
    _write_json(output_dir / "_runtime" / "activity.jsonl", {})
    return output_dir


def test_iterator_v1_normalized_reaction_adds_exact_segment_source_span(tmp_path: Path) -> None:
    output_dir = _write_iterator_output(tmp_path, anchor_quote="beta")
    structure = json.loads(structure_file(output_dir).read_text(encoding="utf-8"))

    bundle = module._normalized_eval_bundle(
        output_dir=output_dir,
        structure=structure,
        config_payload={"test": True},
    )

    locator = bundle["reactions"][0]["target_locator"]
    assert locator["source_span_resolution"] == "exact"
    assert locator["source_span_slices"] == [
        {
            "coordinate_system": "segment_source_v1",
            "paragraph_index": 1,
            "char_start": 6,
            "char_end": 10,
            "text": "beta",
            "source_span_resolution": "exact",
        }
    ]


def test_iterator_v1_normalized_reaction_falls_back_to_segment_span(tmp_path: Path) -> None:
    output_dir = _write_iterator_output(tmp_path, anchor_quote="not present", segment_text="Alpha beta gamma")
    structure = json.loads(structure_file(output_dir).read_text(encoding="utf-8"))

    bundle = module._normalized_eval_bundle(
        output_dir=output_dir,
        structure=structure,
        config_payload={"test": True},
    )

    locator = bundle["reactions"][0]["target_locator"]
    assert locator["source_span_resolution"] == "segment_fallback"
    assert locator["source_span_slices"] == [
        {
            "coordinate_system": "segment_source_v1",
            "paragraph_index": 1,
            "char_start": 0,
            "char_end": len("Alpha beta gamma"),
            "text": "Alpha beta gamma",
            "source_span_resolution": "segment_fallback",
        }
    ]
