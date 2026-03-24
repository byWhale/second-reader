"""Build the first curated excerpt-case packs for attentional_v2 evaluation.

This script freezes an initial human-guided curation pass on top of the current
seed corpora. It creates:
- tracked curated excerpt packs for repo-safe public-domain sources
- local-only curated excerpt packs for manually added local books
- split and local-ref manifests that make the curated layer reproducible
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TRACKED_DATASET_ROOT = ROOT / "eval" / "datasets" / "excerpt_cases"
LOCAL_DATASET_ROOT = ROOT / "state" / "eval_local_datasets" / "excerpt_cases"
MANIFEST_ROOT = ROOT / "eval" / "manifests"


def load_book_document(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_case(spec: dict[str, Any]) -> dict[str, Any]:
    document = load_book_document(spec["book_document"])
    chapter = next(ch for ch in document["chapters"] if int(ch["id"]) == spec["chapter_id"])
    sentences = chapter.get("sentences") or []
    start_index = next(
        index for index, sentence in enumerate(sentences) if sentence["sentence_id"] == spec["start_sentence_id"]
    )
    end_index = next(
        index for index, sentence in enumerate(sentences) if sentence["sentence_id"] == spec["end_sentence_id"]
    )
    excerpt_sentences = sentences[start_index : end_index + 1]
    excerpt_text = "\n".join(sentence.get("text", "") for sentence in excerpt_sentences).strip()
    return {
        "case_id": spec["case_id"],
        "case_title": spec["case_title"],
        "split": "curated_v1",
        "curation_status": "curated_benchmark_candidate_v1",
        "source_policy": spec["source_policy"],
        "source_id": spec["source_id"],
        "book_title": spec["book_title"],
        "author": spec["author"],
        "output_language": spec["output_language"],
        "chapter_id": spec["chapter_id"],
        "chapter_number": chapter.get("chapter_number"),
        "chapter_title": chapter.get("title") or chapter.get("chapter_heading") or f"Chapter {spec['chapter_id']}",
        "start_sentence_id": spec["start_sentence_id"],
        "end_sentence_id": spec["end_sentence_id"],
        "excerpt_text": excerpt_text,
        "question_ids": spec["question_ids"],
        "phenomena": spec["phenomena"],
        "selection_reason": spec["selection_reason"],
        "judge_focus": spec["judge_focus"],
        "notes": "Initial curated benchmark candidate selected from the seed corpus. Still eligible for later expansion or replacement after evaluation review.",
    }


def dataset_manifest(
    *,
    dataset_id: str,
    language_track: str,
    description: str,
    source_manifest_refs: list[str],
    split_refs: list[str],
    storage_mode: str,
) -> dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "family": "excerpt_cases",
        "language_track": language_track,
        "version": "1",
        "description": description,
        "primary_file": "cases.jsonl",
        "question_ids": [
            "EQ-CM-002",
            "EQ-CM-004",
            "EQ-AV2-001",
            "EQ-AV2-002",
            "EQ-AV2-003",
            "EQ-AV2-004",
            "EQ-AV2-005",
            "EQ-AV2-006",
        ],
        "source_manifest_refs": source_manifest_refs,
        "split_refs": split_refs,
        "storage_mode": storage_mode,
    }


TRACKED_EN_SPECS: list[dict[str, Any]] = [
    {
        "case_id": "walden_pond_clarity_curated_v1",
        "case_title": "Walden pond clarity and depth",
        "source_policy": "repo-safe-public-source",
        "source_id": "walden_205_en",
        "book_title": "Walden, and On The Duty Of Civil Disobedience",
        "author": "Henry David Thoreau",
        "output_language": "en",
        "book_document": "output/walden-and-on-the-duty-of-civil-disobedience/public/book_document.json",
        "chapter_id": 13,
        "start_sentence_id": "c13-s55",
        "end_sentence_id": "c13-s60",
        "question_ids": ["EQ-CM-002", "EQ-AV2-005"],
        "phenomena": ["reaction_anchor", "selective_legibility", "descriptive_pressure"],
        "selection_reason": "Keeps a concrete, perceptual passage that should reward text-grounded attention instead of generic interpretation.",
        "judge_focus": "Does the mechanism notice what makes the description distinct without flattening it into bland nature summary?",
    },
    {
        "case_id": "souls_black_belt_decay_curated_v1",
        "case_title": "Black Belt field decay and renter life",
        "source_policy": "repo-safe-public-source",
        "source_id": "souls_of_black_folk_408_en",
        "book_title": "The Souls of Black Folk",
        "author": "W. E. B. Du Bois",
        "output_language": "en",
        "book_document": "output/the-souls-of-black-folk/public/book_document.json",
        "chapter_id": 10,
        "start_sentence_id": "c10-s216",
        "end_sentence_id": "c10-s221",
        "question_ids": ["EQ-CM-002", "EQ-CM-004", "EQ-AV2-005"],
        "phenomena": ["social_observation", "durable_trace_candidate", "anchored_reaction"],
        "selection_reason": "Gives the reader a socially charged observational passage where reaction quality and durable-trace usefulness should differ.",
        "judge_focus": "Does the mechanism stay with the concrete scene while still surfacing the larger human pressure inside it?",
    },
    {
        "case_id": "pride_darcy_conversation_curated_v1",
        "case_title": "Darcy on conversation with strangers",
        "source_policy": "repo-safe-public-source",
        "source_id": "pride_and_prejudice_1342_en",
        "book_title": "Pride and Prejudice",
        "author": "Jane Austen",
        "output_language": "en",
        "book_document": "output/pride-and-prejudice/public/book_document.json",
        "chapter_id": 32,
        "start_sentence_id": "c32-s937",
        "end_sentence_id": "c32-s942",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-005"],
        "phenomena": ["distinction", "character_reveal", "dialogue_pressure"],
        "selection_reason": "Provides a compact dialogue unit where meaning-unit closure and anchored visible reaction quality are easy to judge.",
        "judge_focus": "Does the mechanism see the distinction between social ease, effort, and self-presentation rather than merely paraphrasing the dialogue?",
    },
    {
        "case_id": "moby_spouter_inn_omen_curated_v1",
        "case_title": "Ishmael and the ominous inn sign",
        "source_policy": "repo-safe-public-source",
        "source_id": "moby_dick_2701_en",
        "book_title": "Moby Dick; Or, The Whale",
        "author": "Herman Melville",
        "output_language": "en",
        "book_document": "output/moby-dick-or-the-whale/public/book_document.json",
        "chapter_id": 1,
        "start_sentence_id": "c1-s937",
        "end_sentence_id": "c1-s942",
        "question_ids": ["EQ-CM-002", "EQ-AV2-005"],
        "phenomena": ["voice_shift", "reaction_anchor", "narrative_anticipation"],
        "selection_reason": "Captures a vivid local turn where a good reader should respond to voice, omen, and comic unease without over-explaining.",
        "judge_focus": "Does the mechanism catch the tonal shift and the reason the moment feels live?",
    },
    {
        "case_id": "middlemarch_presence_vs_attributes_curated_v1",
        "case_title": "Presence rather than attributes",
        "source_policy": "repo-safe-public-source",
        "source_id": "middlemarch_145_en",
        "book_title": "Middlemarch",
        "author": "George Eliot",
        "output_language": "en",
        "book_document": "output/middlemarch/public/book_document.json",
        "chapter_id": 52,
        "start_sentence_id": "c52-s105",
        "end_sentence_id": "c52-s110",
        "question_ids": ["EQ-CM-002", "EQ-AV2-003", "EQ-AV2-005"],
        "phenomena": ["reframe_potential", "social_inference", "anchored_reaction"],
        "selection_reason": "Useful for controller-move quality because the passage invites a subtle reframe rather than a literal recap.",
        "judge_focus": "Does the mechanism notice the social inference and conceptual turn inside the exchange?",
    },
]


TRACKED_ZH_SPECS: list[dict[str, Any]] = [
    {
        "case_id": "nahan_cannibal_paranoia_curated_v1",
        "case_title": "吃人 paranoia pressure",
        "source_policy": "repo-safe-public-source",
        "source_id": "nahan_27166_zh",
        "book_title": "吶喊",
        "author": "魯迅",
        "output_language": "zh",
        "book_document": "output/吶喊/public/book_document.json",
        "chapter_id": 1,
        "start_sentence_id": "c1-s381",
        "end_sentence_id": "c1-s386",
        "question_ids": ["EQ-CM-002", "EQ-AV2-005"],
        "phenomena": ["tension_reversal", "reaction_anchor", "voice_pressure"],
        "selection_reason": "Provides a high-pressure local passage where a good reaction should stay anchored to the paranoia and its social logic.",
        "judge_focus": "Does the mechanism respond to the escalating pressure faithfully instead of generalizing it away?",
    },
    {
        "case_id": "nahan_thick_barrier_curated_v1",
        "case_title": "可悲的厚障壁",
        "source_policy": "repo-safe-public-source",
        "source_id": "nahan_27166_zh",
        "book_title": "吶喊",
        "author": "魯迅",
        "output_language": "zh",
        "book_document": "output/吶喊/public/book_document.json",
        "chapter_id": 1,
        "start_sentence_id": "c1-s1099",
        "end_sentence_id": "c1-s1105",
        "question_ids": ["EQ-CM-002", "EQ-CM-004", "EQ-AV2-006"],
        "phenomena": ["reconsolidation_candidate", "durable_trace_candidate", "emotional_turn"],
        "selection_reason": "Good candidate for later reinterpretation and durable-trace judging because the barrier image can return meaningfully on reread.",
        "judge_focus": "Does the mechanism preserve the emotional turn and the barrier image as something worth carrying forward?",
    },
]


LOCAL_EN_SPECS: list[dict[str, Any]] = [
    {
        "case_id": "antifragile_heuristics_vs_theorems_curated_v1",
        "case_title": "Builders before theorems",
        "source_policy": "local-manual-source",
        "source_id": "antifragile_private_en",
        "book_title": "Antifragile",
        "author": "Nassim Nicholas Taleb",
        "output_language": "en",
        "book_document": "output/antifragile/public/book_document.json",
        "chapter_id": 140,
        "start_sentence_id": "c140-s80",
        "end_sentence_id": "c140-s85",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-003"],
        "phenomena": ["distinction", "meaning_unit_closure", "reframe_potential"],
        "selection_reason": "Strong conceptual passage for judging whether the mechanism can close around a distinction instead of scattering into slogans.",
        "judge_focus": "Does the mechanism capture the heuristic-versus-theory contrast and why the examples matter?",
    },
    {
        "case_id": "antifragile_drug_interactions_curated_v1",
        "case_title": "Drug interactions and nonlinear growth",
        "source_policy": "local-manual-source",
        "source_id": "antifragile_private_en",
        "book_title": "Antifragile",
        "author": "Nassim Nicholas Taleb",
        "output_language": "en",
        "book_document": "output/antifragile/public/book_document.json",
        "chapter_id": 140,
        "start_sentence_id": "c140-s265",
        "end_sentence_id": "c140-s270",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-004"],
        "phenomena": ["nonlinearity", "bridge_potential", "conceptual_pressure"],
        "selection_reason": "Useful bridge-worthy passage where the mechanism should notice nonlinear escalation and obliquity without detaching from the text.",
        "judge_focus": "Does the mechanism track the compounding interaction logic faithfully and connect it to the stated point?",
    },
    {
        "case_id": "fooled_two_planets_curated_v1",
        "case_title": "Two planets and hindsight",
        "source_policy": "local-manual-source",
        "source_id": "fooled_by_randomness_private_en",
        "book_title": "Fooled by Randomness",
        "author": "Nassim Nicholas Taleb",
        "output_language": "en",
        "book_document": "output/fooled-by-randomness-the-hidden-role-of-chance-in-life-and-in-the-markets-incerto/public/book_document.json",
        "chapter_id": 4,
        "start_sentence_id": "c4-s22",
        "end_sentence_id": "c4-s27",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-005"],
        "phenomena": ["distinction", "reaction_anchor", "interpretive_pressure"],
        "selection_reason": "Compact and sharp passage for testing whether the mechanism can keep an arresting metaphor tied to its argumentative function.",
        "judge_focus": "Does the mechanism treat the two-planet image as a live distinction rather than a decorative quote?",
    },
    {
        "case_id": "fooled_monte_carlo_curated_v1",
        "case_title": "Monte Carlo where mathematics fails",
        "source_policy": "local-manual-source",
        "source_id": "fooled_by_randomness_private_en",
        "book_title": "Fooled by Randomness",
        "author": "Nassim Nicholas Taleb",
        "output_language": "en",
        "book_document": "output/fooled-by-randomness-the-hidden-role-of-chance-in-life-and-in-the-markets-incerto/public/book_document.json",
        "chapter_id": 18,
        "start_sentence_id": "c18-s95",
        "end_sentence_id": "c18-s100",
        "question_ids": ["EQ-CM-002", "EQ-AV2-004"],
        "phenomena": ["bridge_potential", "method_reframe", "conceptual_pressure"],
        "selection_reason": "Good for evaluating whether bridge/reframe moves remain source-grounded when a passage opens onto method and epistemology.",
        "judge_focus": "Does the mechanism connect the Monte Carlo claim to the critique of inferior mathematics honestly?",
    },
    {
        "case_id": "skin_fatal_cures_curated_v1",
        "case_title": "Fatal cures and regime change",
        "source_policy": "local-manual-source",
        "source_id": "skin_in_the_game_private_en",
        "book_title": "Skin in the Game",
        "author": "Nassim Nicholas Taleb",
        "output_language": "en",
        "book_document": "output/skin-in-the-game-hidden-asymmetries-in-daily-life/public/book_document.json",
        "chapter_id": 5,
        "start_sentence_id": "c5-s26",
        "end_sentence_id": "c5-s31",
        "question_ids": ["EQ-CM-002", "EQ-AV2-003", "EQ-AV2-005"],
        "phenomena": ["tension_reversal", "reaction_anchor", "controller_move_quality"],
        "selection_reason": "Strong local argumentative turn with obvious danger of either weak paraphrase or overblown moralizing.",
        "judge_focus": "Does the mechanism notice the lethal-cure analogy as the core move and stay anchored to it?",
    },
    {
        "case_id": "skin_decentralization_curated_v1",
        "case_title": "Decentralization and macrobullshit",
        "source_policy": "local-manual-source",
        "source_id": "skin_in_the_game_private_en",
        "book_title": "Skin in the Game",
        "author": "Nassim Nicholas Taleb",
        "output_language": "en",
        "book_document": "output/skin-in-the-game-hidden-asymmetries-in-daily-life/public/book_document.json",
        "chapter_id": 5,
        "start_sentence_id": "c5-s89",
        "end_sentence_id": "c5-s94",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-004"],
        "phenomena": ["distinction", "bridge_potential", "anchored_reaction"],
        "selection_reason": "Good for testing whether the mechanism can stay with a rough verbal contrast and still extract the structural claim behind it.",
        "judge_focus": "Does the mechanism capture why decentralization is framed as a defense against hidden asymmetry?",
    },
    {
        "case_id": "value_self_manipulation_curated_v1",
        "case_title": "We manipulated ourselves",
        "source_policy": "local-manual-source",
        "source_id": "value_of_others_private_en",
        "book_title": "The Value of Others",
        "author": "Orion Taraban",
        "output_language": "en",
        "book_document": "output/the-value-of-others-understanding-the-economic-model-of-relationships-to-get-and-keep-more-of-what-you-want-in-the-sexual-marketplace/public/book_document.json",
        "chapter_id": 12,
        "start_sentence_id": "c12-s92",
        "end_sentence_id": "c12-s97",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-005"],
        "phenomena": ["distinction", "meaning_unit_closure", "reaction_anchor"],
        "selection_reason": "Compact conceptual turn where the mechanism should close around a reversal in agency rather than merely summarize emotional manipulation.",
        "judge_focus": "Does the mechanism grasp the shift from 'manipulated by others' to 'manipulated ourselves' with enough specificity?",
    },
    {
        "case_id": "value_rejection_clue_curated_v1",
        "case_title": "Rejection contains a clue",
        "source_policy": "local-manual-source",
        "source_id": "value_of_others_private_en",
        "book_title": "The Value of Others",
        "author": "Orion Taraban",
        "output_language": "en",
        "book_document": "output/the-value-of-others-understanding-the-economic-model-of-relationships-to-get-and-keep-more-of-what-you-want-in-the-sexual-marketplace/public/book_document.json",
        "chapter_id": 12,
        "start_sentence_id": "c12-s304",
        "end_sentence_id": "c12-s309",
        "question_ids": ["EQ-CM-002", "EQ-CM-004", "EQ-AV2-006"],
        "phenomena": ["reconsolidation_candidate", "durable_trace_candidate", "interpretive_pressure"],
        "selection_reason": "Good durable-trace candidate because the clue-in-rejection idea should be worth returning to after the first pass.",
        "judge_focus": "Does the mechanism preserve the relation between rejection, emotion, and discernment in a way that could matter later?",
    },
    {
        "case_id": "inspired_value_viability_curated_v1",
        "case_title": "Value, use, and business viability",
        "source_policy": "local-manual-source",
        "source_id": "inspired_private_en",
        "book_title": "INSPIRED",
        "author": "Marty Cagan et al.",
        "output_language": "en",
        "book_document": "output/inspired/public/book_document.json",
        "chapter_id": 87,
        "start_sentence_id": "c87-s37",
        "end_sentence_id": "c87-s42",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-004"],
        "phenomena": ["expository_distinction", "bridge_potential", "conceptual_pressure"],
        "selection_reason": "Adds modern product-thinking prose where the mechanism has to read a practical conceptual structure instead of a literary cue.",
        "judge_focus": "Does the mechanism distinguish value, usage, and business viability without flattening them together?",
    },
    {
        "case_id": "chance_feelings_and_brother_curated_v1",
        "case_title": "It is what I feel that matters",
        "source_policy": "local-manual-source",
        "source_id": "chance_private_en",
        "book_title": "Chance",
        "author": "Joseph Conrad",
        "output_language": "en",
        "book_document": "output/chance/public/book_document.json",
        "chapter_id": 13,
        "start_sentence_id": "c13-s499",
        "end_sentence_id": "c13-s504",
        "question_ids": ["EQ-CM-002", "EQ-AV2-005"],
        "phenomena": ["narrative_pressure", "reaction_anchor", "character_voice"],
        "selection_reason": "Provides narrative/emotional prose so the local supplement is not only argumentative nonfiction.",
        "judge_focus": "Does the mechanism keep the emotional emphasis and the relational clue alive without overwriting the speaker's voice?",
    },
]


LOCAL_ZH_SPECS: list[dict[str, Any]] = [
    {
        "case_id": "biji_counterintuitive_information_curated_v1",
        "case_title": "什么是反直觉的信息",
        "source_policy": "local-manual-source",
        "source_id": "biji_de_fangfa_private_zh",
        "book_title": "笔记的方法",
        "author": "刘少楠, 刘白光",
        "output_language": "zh",
        "book_document": "output/笔记的方法/public/book_document.json",
        "chapter_id": 8,
        "start_sentence_id": "c8-s361",
        "end_sentence_id": "c8-s366",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002"],
        "phenomena": ["distinction", "meaning_unit_closure", "modern_expository"],
        "selection_reason": "Useful modern Chinese expository passage where the mechanism should close around a practical distinction instead of producing generic productivity talk.",
        "judge_focus": "Does the mechanism preserve the shift from default habits to the value of counterintuitive information?",
    },
    {
        "case_id": "biji_tags_grow_with_work_curated_v1",
        "case_title": "标签不是一次性规划好的",
        "source_policy": "local-manual-source",
        "source_id": "biji_de_fangfa_private_zh",
        "book_title": "笔记的方法",
        "author": "刘少楠, 刘白光",
        "output_language": "zh",
        "book_document": "output/笔记的方法/public/book_document.json",
        "chapter_id": 9,
        "start_sentence_id": "c9-s421",
        "end_sentence_id": "c9-s426",
        "question_ids": ["EQ-CM-002", "EQ-AV2-003"],
        "phenomena": ["reframe_potential", "structure_growth", "modern_expository"],
        "selection_reason": "Good controller-move case because the passage rewards noticing an implicit reframe from static taxonomy to evolving practice.",
        "judge_focus": "Does the mechanism see the organic-growth claim in the tagging example rather than only the surface workflow?",
    },
    {
        "case_id": "suiji_nature_does_not_jump_curated_v1",
        "case_title": "自然不突变并不成立",
        "source_policy": "local-manual-source",
        "source_id": "fooled_by_randomness_private_zh",
        "book_title": "随机漫步的傻瓜",
        "author": "纳西姆·尼古拉斯·塔勒布",
        "output_language": "zh",
        "book_document": "output/随机漫步的傻瓜/public/book_document.json",
        "chapter_id": 12,
        "start_sentence_id": "c12-s1201",
        "end_sentence_id": "c12-s1206",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-004"],
        "phenomena": ["distinction", "reframe_potential", "conceptual_pressure"],
        "selection_reason": "Strong conceptual Chinese passage for testing whether the mechanism can preserve a claim and its reversal without drifting away from the source.",
        "judge_focus": "Does the mechanism track the attack on continuity assumptions with enough specificity?",
    },
    {
        "case_id": "suiji_popper_demarcation_curated_v1",
        "case_title": "波普尔与画界问题",
        "source_policy": "local-manual-source",
        "source_id": "fooled_by_randomness_private_zh",
        "book_title": "随机漫步的傻瓜",
        "author": "纳西姆·尼古拉斯·塔勒布",
        "output_language": "zh",
        "book_document": "output/随机漫步的傻瓜/public/book_document.json",
        "chapter_id": 12,
        "start_sentence_id": "c12-s1601",
        "end_sentence_id": "c12-s1606",
        "question_ids": ["EQ-CM-002", "EQ-AV2-004", "EQ-AV2-005"],
        "phenomena": ["bridge_potential", "definition_distinction", "anchored_reaction"],
        "selection_reason": "Good for bridge judgment because it links Popper, demarcation, statistics, and epistemic caution in one compact unit.",
        "judge_focus": "Does the mechanism bridge among the claims honestly while staying grounded in the actual passage?",
    },
]


def build_rows(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_case(spec) for spec in specs]


def write_package(root: Path, dataset_id: str, manifest: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    package_dir = root / dataset_id
    write_json(package_dir / "manifest.json", manifest)
    write_jsonl(package_dir / "cases.jsonl", rows)


def main() -> None:
    tracked_en_rows = build_rows(TRACKED_EN_SPECS)
    tracked_zh_rows = build_rows(TRACKED_ZH_SPECS)
    local_en_rows = build_rows(LOCAL_EN_SPECS)
    local_zh_rows = build_rows(LOCAL_ZH_SPECS)

    curated_split_manifest = MANIFEST_ROOT / "splits" / "attentional_v2_excerpt_curated_v1.json"
    write_json(
        curated_split_manifest,
        {
            "manifest_id": "attentional_v2_excerpt_curated_v1_splits",
            "description": "Curated excerpt-case package membership for the first attentional_v2 benchmark-quality curation pass.",
            "packages": {
                "attentional_v2_excerpt_en_curated_v1": [row["case_id"] for row in tracked_en_rows],
                "attentional_v2_excerpt_zh_curated_v1": [row["case_id"] for row in tracked_zh_rows],
                "attentional_v2_private_excerpt_en_curated_v1": [row["case_id"] for row in local_en_rows],
                "attentional_v2_private_excerpt_zh_curated_v1": [row["case_id"] for row in local_zh_rows],
            },
        },
    )

    private_curated_local_refs = MANIFEST_ROOT / "local_refs" / "attentional_v2_private_excerpt_curated_v1.json"
    write_json(
        private_curated_local_refs,
        {
            "manifest_id": "attentional_v2_private_excerpt_curated_v1_local_refs",
            "description": "Local package references for the curated private/local attentional_v2 excerpt packs.",
            "local_dataset_packages": [
                {
                    "dataset_id": "attentional_v2_private_excerpt_en_curated_v1",
                    "family": "excerpt_cases",
                    "language_track": "en",
                    "relative_local_path": "state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_en_curated_v1",
                },
                {
                    "dataset_id": "attentional_v2_private_excerpt_zh_curated_v1",
                    "family": "excerpt_cases",
                    "language_track": "zh",
                    "relative_local_path": "state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_zh_curated_v1",
                },
            ],
        },
    )

    tracked_source_refs = [
        "eval/manifests/source_books/attentional_v2_public_domain_seed_v1.json",
        "eval/manifests/local_refs/attentional_v2_public_domain_seed_v1.json",
        "eval/manifests/corpora/attentional_v2_public_domain_seed_bilingual_v1.json",
    ]
    local_source_refs = [
        "eval/manifests/source_books/attentional_v2_private_downloads_screen_v1.json",
        "eval/manifests/local_refs/attentional_v2_private_downloads_seed_v1.json",
        "eval/manifests/corpora/attentional_v2_private_downloads_bilingual_v1.json",
        "eval/manifests/local_refs/attentional_v2_private_excerpt_curated_v1.json",
    ]
    tracked_split_refs = [
        "eval/manifests/splits/attentional_v2_public_domain_seed_bilingual_v1.json",
        "eval/manifests/splits/attentional_v2_excerpt_curated_v1.json",
    ]
    local_split_refs = [
        "eval/manifests/splits/attentional_v2_private_downloads_bilingual_v1.json",
        "eval/manifests/splits/attentional_v2_excerpt_curated_v1.json",
    ]

    write_package(
        TRACKED_DATASET_ROOT,
        "attentional_v2_excerpt_en_curated_v1",
        dataset_manifest(
            dataset_id="attentional_v2_excerpt_en_curated_v1",
            language_track="en",
            description="Curated English excerpt benchmark candidates drawn from repo-safe public-domain attentional_v2 sources.",
            source_manifest_refs=tracked_source_refs,
            split_refs=tracked_split_refs,
            storage_mode="tracked",
        ),
        tracked_en_rows,
    )
    write_package(
        TRACKED_DATASET_ROOT,
        "attentional_v2_excerpt_zh_curated_v1",
        dataset_manifest(
            dataset_id="attentional_v2_excerpt_zh_curated_v1",
            language_track="zh",
            description="Curated Chinese excerpt benchmark candidates drawn from repo-safe public-domain attentional_v2 sources.",
            source_manifest_refs=tracked_source_refs,
            split_refs=tracked_split_refs,
            storage_mode="tracked",
        ),
        tracked_zh_rows,
    )
    write_package(
        LOCAL_DATASET_ROOT,
        "attentional_v2_private_excerpt_en_curated_v1",
        dataset_manifest(
            dataset_id="attentional_v2_private_excerpt_en_curated_v1",
            language_track="en",
            description="Curated English excerpt benchmark candidates drawn from manually added local attentional_v2 sources.",
            source_manifest_refs=local_source_refs,
            split_refs=local_split_refs,
            storage_mode="private-local",
        ),
        local_en_rows,
    )
    write_package(
        LOCAL_DATASET_ROOT,
        "attentional_v2_private_excerpt_zh_curated_v1",
        dataset_manifest(
            dataset_id="attentional_v2_private_excerpt_zh_curated_v1",
            language_track="zh",
            description="Curated Chinese excerpt benchmark candidates drawn from manually added local attentional_v2 sources.",
            source_manifest_refs=local_source_refs,
            split_refs=local_split_refs,
            storage_mode="private-local",
        ),
        local_zh_rows,
    )

    print("Curated excerpt packs built.")
    print(f"Tracked English curated cases: {len(tracked_en_rows)}")
    print(f"Tracked Chinese curated cases: {len(tracked_zh_rows)}")
    print(f"Local English curated cases: {len(local_en_rows)}")
    print(f"Local Chinese curated cases: {len(local_zh_rows)}")


if __name__ == "__main__":
    main()
