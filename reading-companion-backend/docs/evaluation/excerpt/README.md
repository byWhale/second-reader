# Excerpt Evaluation Reports

This directory is now historical.

It keeps the superseded chapter-scoped excerpt-surface reports that were active before the note-aligned `user-level selective v1` benchmark replaced `excerpt surface v1.1` as the active local/user-level pointer.

## Conventions
- One formal judged run should land one human interpretation report.
- Report filenames follow `<run_id>_interpretation.md`.
- Machine outputs remain under `reading-companion-backend/eval/runs/.../summary/`.
- This index records the durable entry point for future agent handoff and result review.
- The cross-surface evidence catalog at [../evidence_catalog.md](../evidence_catalog.md) records this surface as superseded historical evidence.

## Reports

| Report title | Run ID | Surface | Compared mechanisms | Status | One-line conclusion | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Excerpt Surface v1.1 正式 judged eval 解读 | `attentional_v2_excerpt_surface_v1_1_judged_20260406` | `excerpt surface v1.1` | `attentional_v2` vs `iterator_v1` | `historical / superseded` | `attentional_v2` 赢下首个完整跑通的 excerpt formal judged eval，优势主要来自更强的章节局部压力跟踪；但这一 surface 已不再是当前活跃的 local/user-level benchmark。 | [aggregate](../../../eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406/summary/aggregate.json) · [report](../../../eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406/summary/report.md) · [interpretation](./attentional_v2_excerpt_surface_v1_1_judged_20260406_interpretation.md) |
