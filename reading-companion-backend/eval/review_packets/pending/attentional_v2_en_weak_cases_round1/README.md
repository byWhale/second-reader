# Dataset Review Packet `attentional_v2_en_weak_cases_round1`

This packet is designed for fast human review without a frontend UI.

## Files
- `packet_manifest.json`
  - machine-readable packet metadata
- `cases.review.csv`
  - the file you should edit
- `cases.preview.md`
  - human-readable preview of the cases
- `cases.source.jsonl`
  - exact source rows that were exported into this packet

## What To Edit
Only edit the `review__...` columns in `cases.review.csv`.

Required:
- `review__action`
  - `keep`
  - `revise`
  - `drop`
  - `unclear`

Recommended:
- `review__confidence`
  - `high`
  - `medium`
  - `low`
- `review__problem_types`
  - use `|` between codes if there are several

Optional:
- `review__revised_bucket`
- `review__revised_selection_reason`
- `review__revised_judge_focus`
- `review__notes`

## Return Process
1. Read `cases.preview.md` if you want the cleanest reading view.
2. Open `cases.review.csv` in Numbers, Excel, Google Sheets, or a text editor.
3. Fill in the `review__...` columns.
4. Save the file in place.
5. Tell Codex that packet `attentional_v2_en_weak_cases_round1` is ready.

Codex will then import this packet, archive it, and merge the review metadata back into the dataset.
