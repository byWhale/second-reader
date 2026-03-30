# Review Packets

Purpose: make dataset review executable without a frontend UI.

This directory contains review packets for benchmark datasets.

## Lifecycle
- `pending/`
  - packets exported by Codex and waiting for review
- `archive/`
  - packets already imported back into the dataset with their review CSV preserved
- `review_queue_summary.json`
  - machine-readable snapshot of the active packet queue and its latest packet-level case audits
- `review_queue_summary.md`
  - readable snapshot of the same queue

Packet-level case-audit runs live under:
- `reading-companion-backend/eval/runs/attentional_v2/case_audits/<packet_id>__<timestamp>/`

Each case-audit run should expose:
- `run_state.json`
  - packet-level status and progress
- `case_states/<case_id>.json`
  - per-case stage state and timing metadata
- `summary/aggregate.partial.json`
- `summary/report.partial.md`
- `summary/aggregate.json`
- `summary/report.md`

Queue/reporting surfaces should distinguish:
- `running`
- `completed`
- `incomplete`

Only completed case-audit runs should be treated as landed evidence for later packet review or import decisions.

## Packet Contents
Each packet folder should contain:
- `packet_manifest.json`
- `cases.review.csv`
- `cases.preview.md`
- `cases.source.jsonl`
- `README.md`
- after LLM adjudication, packet roots may also contain:
  - `llm_review_summary.json`
  - `llm_review_report.md`
  - `llm_review_runs/<run_id>/`

Each adjudication run under `llm_review_runs/<run_id>/` now writes:
- `manifest.json`
- `summary.json`
- `report.md`
- `cases/<case_id>.json`
  - per-case normalized review result
  - source/audit prompt-input fingerprints
  - selected target/tier/provider trace metadata when available

## Packet Generators
- `eval/attentional_v2/export_dataset_review_packet.py`
  - export an arbitrary packet from explicit case ids, bucket filters, or unreviewed rows
- `eval/attentional_v2/generate_revision_replacement_packet.py`
  - export the next hardening packet automatically from rows whose current `benchmark_status` is already `needs_revision`, `needs_replacement`, or another explicitly requested status

## Review Workflow
Current operational mode:
- Codex may fill the `review__...` columns automatically through multi-prompt LLM adjudication.
- Packet-level case audits may use bounded case-level parallelism, but the primary and adversarial review stages remain ordered within each case.

Default mechanical path:
- from the workspace root, run `make dataset-review-pipeline DATASET_REVIEW_PIPELINE_ARGS="--dataset-id <dataset_id> --family <family> --storage-mode <tracked|local-only> [--packet-id <packet_id>]"`
- from the backend directly, run `.venv/bin/python -m eval.attentional_v2.run_dataset_review_pipeline --dataset-id <dataset_id> --family <family> --storage-mode <tracked|local-only>`
- the pipeline stages stay direct:
  - `generate_packet` -> `generate_revision_replacement_packet.py`
  - `audit_packet` -> `run_case_design_audit.py`
  - `adjudicate_packet` -> `auto_review_packet.py`
  - `import_packet` -> `import_dataset_review_packet.py --archive`
  - `refresh_queue_summary` -> `build_review_queue_summary.py`
  - `final_summary` -> write `dataset_review_pipeline_summary.json` and `dataset_review_pipeline_summary.md` into the archived packet dir when available, otherwise the active packet dir
- the pipeline is intentionally mechanical only:
  - it does not reopen benchmark promotion automatically
  - it does not freeze reviewed slices automatically
  - it does not launch durable-trace, re-entry, or runtime-viability follow-up work
  - it stops with the final summary artifact instead of making a decision-bearing next move
- reproducibility helper:
  - `eval/attentional_v2/compare_packet_adjudication_runs.py`
  - compare two packet dirs or adjudication run dirs when we need to inspect whether drift came from:
    - source-row changes
    - regenerated audit-input changes
    - adjudication-output changes
    - routing changes

Optional manual mode:
1. Open `cases.preview.md` for the readable view.
2. Edit only the `review__...` columns in `cases.review.csv`.
3. Save the file in place.
4. Tell Codex the packet is ready.

Codex then runs:
- `eval/attentional_v2/import_dataset_review_packet.py --packet-id <packet_id> --archive`

Imported packets now feed the dataset through:
- `review_status`
  - `builder_curated` -> baseline builder-owned state
  - `llm_reviewed` -> the case has been adjudicated by the current multi-prompt LLM review policy
  - `human_reviewed` -> the case has been reviewed by a human
- `benchmark_status`
  - `reviewed_active` -> safe to include in the reviewed benchmark slice
  - `needs_revision` -> review found the case promising but not ready to freeze yet
  - `needs_replacement` -> drop and replace
  - `needs_adjudication` -> still unclear after review

## Why This Exists
- The current benchmark family still contains builder-curated cases.
- Some benchmark problems are dataset problems rather than mechanism problems.
- A fast packet workflow makes it practical to improve dataset quality before we trust broader evaluations too much.
- The current default is LLM-led packet review; manual human review is optional later escalation rather than the default blocker.
