# Review Packets

Purpose: make dataset review executable without a frontend UI.

This directory contains review packets for benchmark datasets.

## Lifecycle
- `pending/`
  - packets exported by Codex and waiting for review
- `archive/`
  - packets already imported back into the dataset with their review CSV preserved
- `review_queue_summary.json`
  - machine-readable snapshot of the active packet queue and its latest machine-side audits
- `review_queue_summary.md`
  - readable snapshot of the same queue

## Packet Contents
Each packet folder should contain:
- `packet_manifest.json`
- `cases.review.csv`
- `cases.preview.md`
- `cases.source.jsonl`
- `README.md`

## Packet Generators
- `eval/attentional_v2/export_dataset_review_packet.py`
  - export an arbitrary packet from explicit case ids, bucket filters, or unreviewed rows
- `eval/attentional_v2/generate_revision_replacement_packet.py`
  - export the next hardening packet automatically from rows whose current `benchmark_status` is already `needs_revision`, `needs_replacement`, or another explicitly requested status

## Review Workflow
Current operational mode:
- Codex may fill the `review__...` columns automatically through multi-prompt LLM adjudication.

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
