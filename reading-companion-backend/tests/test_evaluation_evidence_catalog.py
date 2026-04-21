import json
from pathlib import Path

from scripts.update_evaluation_catalog import (
    build_entry,
    upsert_catalog_entry,
    validate_catalog,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _make_formal_run(tmp_path: Path, run_id: str = "run_a") -> Path:
    run_dir = tmp_path / run_id
    _write_json(
        run_dir / "summary" / "aggregate.json",
        {
            "run_id": run_id,
            "manifest_path": str(tmp_path / "manifest.json"),
            "dataset_dir": str(tmp_path / "dataset"),
            "note_case_count": 2,
            "mechanisms": {
                "attentional_v2": {"note_case_count": 2, "note_recall": 0.5},
                "iterator_v1": {"note_case_count": 2, "note_recall": 0.25},
            },
        },
    )
    (tmp_path / "manifest.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "dataset").mkdir()
    (run_dir / "summary" / "report.md").write_text("# report\n", encoding="utf-8")
    return run_dir


def test_upsert_generates_catalog_and_is_idempotent(tmp_path: Path) -> None:
    run_dir = _make_formal_run(tmp_path)
    catalog_json = tmp_path / "evidence_catalog.json"
    catalog_md = tmp_path / "evidence_catalog.md"

    entry = build_entry(
        run_id="run_a",
        surface="user_level_selective_v1",
        status="current_formal_evidence",
        run_dir=run_dir,
        one_line_conclusion="V2 leads on note recall.",
    )
    upsert_catalog_entry(entry, catalog_json_path=catalog_json, catalog_md_path=catalog_md)
    upsert_catalog_entry(entry, catalog_json_path=catalog_json, catalog_md_path=catalog_md)

    payload = json.loads(catalog_json.read_text(encoding="utf-8"))
    assert len(payload["entries"]) == 1
    stored = payload["entries"][0]
    assert stored["run_id"] == "run_a"
    assert stored["mechanisms"] == ["attentional_v2", "iterator_v1"]
    assert stored["metric_summary"]["mechanisms"]["attentional_v2"]["note_recall"] == 0.5
    assert "V2 leads on note recall." in catalog_md.read_text(encoding="utf-8")
    assert validate_catalog(catalog_json_path=catalog_json) == []


def test_check_rejects_formal_entry_without_complete_summary(tmp_path: Path) -> None:
    run_dir = tmp_path / "incomplete_run"
    run_dir.mkdir()
    catalog_json = tmp_path / "evidence_catalog.json"
    catalog_md = tmp_path / "evidence_catalog.md"

    entry = build_entry(
        run_id="incomplete_run",
        surface="user_level_selective_v1",
        status="current_formal_evidence",
        run_dir=run_dir,
    )
    upsert_catalog_entry(entry, catalog_json_path=catalog_json, catalog_md_path=catalog_md)

    errors = validate_catalog(catalog_json_path=catalog_json)
    assert any("formal evidence requires aggregate path" in item for item in errors)
    assert any("formal evidence requires report path" in item for item in errors)


def test_diagnostic_entry_may_omit_aggregate_and_report(tmp_path: Path) -> None:
    run_dir = tmp_path / "failed_run"
    run_dir.mkdir()
    catalog_json = tmp_path / "evidence_catalog.json"
    catalog_md = tmp_path / "evidence_catalog.md"

    entry = build_entry(
        run_id="failed_run",
        surface="user_level_selective_v1",
        status="failed_diagnostic",
        run_dir=run_dir,
        one_line_conclusion="Retained as failure evidence.",
    )
    upsert_catalog_entry(entry, catalog_json_path=catalog_json, catalog_md_path=catalog_md)

    assert validate_catalog(catalog_json_path=catalog_json) == []
