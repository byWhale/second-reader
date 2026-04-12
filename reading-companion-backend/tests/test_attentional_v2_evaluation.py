"""Tests for attentional_v2 Phase 8 evaluation exports and integrity checks."""

from __future__ import annotations

import json
from pathlib import Path

from src.attentional_v2.runner import _chapter_ref
from src.attentional_v2.evaluation import normalized_eval_bundle_file
from src.attentional_v2.schemas import (
    build_empty_reaction_records,
    build_empty_reconsolidation_records,
    build_empty_reflective_frames,
)
from src.attentional_v2.slow_cycle import build_reaction_record, project_chapter_result_compatibility
from src.attentional_v2.storage import reaction_records_file, reconsolidation_records_file, reflective_frames_file, save_json
from src.reading_core.storage import save_book_document
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_runtime.artifacts import activity_file, runtime_shell_file
from src.reading_runtime.shell_state import load_runtime_shell, save_runtime_shell


def _book_document() -> dict[str, object]:
    return {
        "metadata": {
            "book": "Demo Book",
            "author": "Tester",
            "book_language": "en",
            "output_language": "en",
            "source_file": "demo.epub",
        },
        "chapters": [
            {
                "id": 1,
                "title": "Opening Frame",
                "chapter_number": 1,
                "level": 1,
                "paragraphs": [
                    {
                        "href": "chapter-1.xhtml",
                        "start_cfi": "/6/2[chapter1]!/4/2/2",
                        "end_cfi": "/6/2[chapter1]!/4/2/10",
                        "paragraph_index": 1,
                        "text": "Markets begin as relations among people.",
                        "block_tag": "p",
                        "heading_level": None,
                        "text_role": "body",
                    },
                    {
                        "href": "chapter-1.xhtml",
                        "start_cfi": "/6/2[chapter1]!/4/4/2",
                        "end_cfi": "/6/2[chapter1]!/4/4/12",
                        "paragraph_index": 2,
                        "text": "Later the author narrows what counts as value.",
                        "block_tag": "p",
                        "heading_level": None,
                        "text_role": "body",
                    },
                ],
                "sentences": [
                    {
                        "sentence_id": "c1-s1",
                        "sentence_index": 1,
                        "sentence_in_paragraph": 1,
                        "paragraph_index": 1,
                        "text": "Markets begin as relations among people.",
                        "text_role": "body",
                        "locator": {
                            "href": "chapter-1.xhtml",
                            "start_cfi": "/6/2[chapter1]!/4/2/2",
                            "end_cfi": "/6/2[chapter1]!/4/2/10",
                            "paragraph_index": 1,
                            "paragraph_start": 1,
                            "paragraph_end": 1,
                            "char_start": 0,
                            "char_end": 36,
                        },
                    },
                    {
                        "sentence_id": "c1-s2",
                        "sentence_index": 2,
                        "sentence_in_paragraph": 1,
                        "paragraph_index": 2,
                        "text": "Later the author narrows what counts as value.",
                        "text_role": "body",
                        "locator": {
                            "href": "chapter-1.xhtml",
                            "start_cfi": "/6/2[chapter1]!/4/4/2",
                            "end_cfi": "/6/2[chapter1]!/4/4/12",
                            "paragraph_index": 2,
                            "paragraph_start": 2,
                            "paragraph_end": 2,
                            "char_start": 0,
                            "char_end": 45,
                        },
                    },
                ],
            }
        ],
    }


def test_runner_chapter_ref_uses_shared_user_facing_reference() -> None:
    assert _chapter_ref({"id": 10, "title": "Chapter V. The Reconstruction Period", "chapter_number": 5}) == "Chapter 5"
    assert _chapter_ref({"id": 7, "title": "Visitors"}) == "Visitors"


def _anchor(anchor_id: str, sentence_id: str, quote: str, paragraph_index: int) -> dict[str, object]:
    return {
        "anchor_id": anchor_id,
        "sentence_start_id": sentence_id,
        "sentence_end_id": sentence_id,
        "quote": quote,
        "locator": {
            "href": "chapter-1.xhtml",
            "start_cfi": f"/6/2[chapter1]!/4/{paragraph_index * 2}/2",
            "end_cfi": f"/6/2[chapter1]!/4/{paragraph_index * 2}/12",
            "paragraph_index": paragraph_index,
            "paragraph_start": paragraph_index,
            "paragraph_end": paragraph_index,
            "char_start": 0,
            "char_end": len(quote),
        },
    }


def test_attentional_v2_can_build_and_persist_normalized_eval_bundle(tmp_path):
    """The Phase 8 scaffold should export a normalized eval bundle from persisted artifacts."""

    output_dir = tmp_path / "output" / "demo-book"
    mechanism = AttentionalV2Mechanism()
    mechanism.initialize_artifacts(output_dir)
    save_book_document(output_dir / "public" / "book_document.json", _book_document())

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    shell["status"] = "deep_reading"
    shell["phase"] = "thinking"
    shell["cursor"] = {
        "position_kind": "span",
        "chapter_id": 1,
        "chapter_ref": "Chapter 1",
        "sentence_id": "c1-s2",
        "span_start_sentence_id": "c1-s1",
        "span_end_sentence_id": "c1-s2",
    }
    shell["active_artifact_refs"] = {"reaction_id": "rx:Chapter_1:c1-s1:highlight"}
    shell["resume_available"] = True
    shell["last_checkpoint_at"] = "2026-03-23T08:00:00Z"
    save_runtime_shell(runtime_shell_file(output_dir), shell)

    reaction_records = build_empty_reaction_records()
    reaction_records["records"] = [
        build_reaction_record(
            reaction={
                "type": "highlight",
                "anchor_quote": "Markets begin as relations among people.",
                "content": "The opening sentence frames value as social relation.",
                "related_anchor_quotes": ["Later the author narrows what counts as value."],
                "search_query": "",
                "search_results": [],
            },
            primary_anchor=_anchor("a-1", "c1-s1", "Markets begin as relations among people.", 1),
            related_anchors=[_anchor("a-2", "c1-s2", "Later the author narrows what counts as value.", 2)],
            chapter_id=1,
            chapter_ref="Chapter 1",
            emitted_at_sentence_id="c1-s1",
        )
    ]
    save_json(reaction_records_file(output_dir), reaction_records)

    reflective = build_empty_reflective_frames()
    reflective["chapter_understandings"] = [
        {
            "item_id": "ru-1",
            "statement": "The chapter opens socially and then narrows its claim.",
            "support_anchor_ids": ["a-1", "a-2"],
            "confidence_band": "stable",
            "promoted_from": "chapter_sweep",
            "status": "active",
            "chapter_ref": "Chapter 1",
        }
    ]
    save_json(reflective_frames_file(output_dir), reflective)

    project_chapter_result_compatibility(
        book_id="demo-book",
        chapter={**_book_document()["chapters"][0], "reference": "Chapter 1"},
        reaction_records=reaction_records,
        output_language="en",
        output_dir=output_dir,
        persist=True,
    )

    activity_path = activity_file(output_dir)
    activity_path.parent.mkdir(parents=True, exist_ok=True)
    activity_path.write_text(
        json.dumps(
            {
                "event_id": "evt-1",
                "timestamp": "2026-03-23T08:01:00Z",
                "stream": "mindstream",
                "kind": "thought",
                "message": "The opening line sets the social frame.",
                "chapter_ref": "Chapter 1",
                "segment_ref": "1.1",
                "anchor_quote": "Markets begin as relations among people.",
                "move_type": "bridge",
                "active_reaction_id": "rx:Chapter_1:c1-s1:highlight",
                "reading_locus": {
                    "kind": "span",
                    "chapter_id": 1,
                    "chapter_ref": "Chapter 1",
                    "sentence_start_id": "c1-s1",
                    "sentence_end_id": "c1-s2",
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = mechanism.build_normalized_eval_bundle(output_dir, config_payload={"benchmark": "attentional_v2_local"})

    assert bundle["mechanism_key"] == "attentional_v2"
    assert bundle["run_snapshot"]["current_chapter_ref"] == "Chapter 1"
    assert bundle["run_snapshot"]["current_reading_locus"]["sentence_start_id"] == "c1-s1"
    assert bundle["attention_events"][0]["move_type"] == "bridge"
    assert bundle["reactions"][0]["primary_anchor"]["quote"] == "Markets begin as relations among people."
    assert bundle["reactions"][0]["related_anchors"][0]["sentence_start_id"] == "c1-s2"
    assert bundle["chapters"][0]["visible_reaction_count"] == 1
    assert bundle["memory_summaries"] == ["The chapter opens socially and then narrows its claim."]

    export_path = mechanism.persist_normalized_eval_bundle(output_dir, config_payload={"benchmark": "attentional_v2_local"})
    assert export_path == normalized_eval_bundle_file(output_dir)
    assert export_path.exists()


def test_attentional_v2_integrity_checks_flag_cursor_anchor_and_reconsolidation_drift(tmp_path):
    """The integrity report should surface structural artifact problems as hard failures."""

    output_dir = tmp_path / "output" / "demo-book"
    mechanism = AttentionalV2Mechanism()
    mechanism.initialize_artifacts(output_dir)
    save_book_document(output_dir / "public" / "book_document.json", _book_document())

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    shell["cursor"] = {
        "position_kind": "sentence",
        "chapter_id": 1,
        "chapter_ref": "Chapter 1",
        "sentence_id": "missing-sentence",
    }
    save_runtime_shell(runtime_shell_file(output_dir), shell)

    broken_reactions = build_empty_reaction_records()
    broken_record = build_reaction_record(
        reaction={
            "type": "discern",
            "anchor_quote": "Markets begin as relations among people.",
            "content": "The social framing is unstable.",
            "related_anchor_quotes": [],
            "search_query": "",
            "search_results": [],
        },
        primary_anchor=_anchor("a-1", "c1-s1", "Markets begin as relations among people.", 1),
        chapter_id=1,
        chapter_ref="Chapter 1",
        emitted_at_sentence_id="c1-s1",
    )
    broken_record["primary_anchor"]["sentence_start_id"] = "missing-anchor"
    broken_record["primary_anchor"]["sentence_end_id"] = "missing-anchor"
    broken_record["primary_anchor"]["locator"]["href"] = ""
    broken_reactions["records"] = [broken_record]
    save_json(reaction_records_file(output_dir), broken_reactions)

    reconsolidations = build_empty_reconsolidation_records()
    reconsolidations["records"] = [
        {
            "record_id": "rc-1",
            "prior_reaction_id": broken_record["reaction_id"],
            "new_reaction_id": broken_record["reaction_id"],
            "change_kind": "tightened",
            "what_changed": "The same reaction id was reused incorrectly.",
            "rationale": "Intentional test corruption.",
            "created_at": "2026-03-23T08:02:00Z",
        }
    ]
    save_json(reconsolidation_records_file(output_dir), reconsolidations)

    report = mechanism.run_mechanism_integrity_checks(output_dir)
    by_code = {check["code"]: check for check in report["checks"]}

    assert report["passed"] is False
    assert by_code["runtime_cursor_sentence_ids_resolve"]["status"] == "fail"
    assert by_code["anchors_reference_shared_sentences"]["status"] == "fail"
    assert by_code["anchors_have_usable_locators"]["status"] == "fail"
    assert by_code["reconsolidation_links_are_append_only"]["status"] == "fail"
