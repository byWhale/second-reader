"""Markdown rendering for chapter deep-read output."""

from __future__ import annotations

from .language import markdown_labels
from .models import ReactionPayload, RenderedSegment, StructureChapter
from .storage import chapter_reference, display_segment_id


REACTION_EMOJI = {
    "highlight": "💡",
    "association": "✍️",
    "curious": "🔍",
    "discern": "⚡",
    "connect_back": "🔗",
    "silent": "🤫",
}


def _chapter_heading(chapter: StructureChapter) -> str:
    """Render a chapter heading with reference and original title when available."""
    reference = chapter_reference(chapter).strip()
    title = chapter.get("title", "").strip()

    if title and reference and title.casefold() != reference.casefold():
        return f"{reference}: {title}"
    return title or reference


def _reaction_heading(reaction: ReactionPayload, labels: dict[str, str]) -> str:
    """Render emoji plus a localized reaction type label."""
    reaction_type = reaction.get("type", "association")
    emoji = REACTION_EMOJI.get(reaction_type, "✍️")
    label = labels.get(reaction_type, labels["unknown"])
    return f"{emoji} {label}"


def _reaction_note(reaction: ReactionPayload) -> str:
    """Render the reader's note for one reaction."""
    anchor_quote = reaction.get("anchor_quote", "").strip()
    content = reaction.get("content", "").strip()
    search_query = reaction.get("search_query", "").strip()

    parts = []
    if content:
        parts.append(content)
    elif search_query:
        parts.append(search_query)
    return " ".join(part for part in parts if part).strip()


def _search_links(reaction: ReactionPayload) -> str:
    """Render compact search result links for curious reactions."""
    links = []
    for item in reaction.get("search_results", [])[:3]:
        title = item.get("title", "").strip() or item.get("url", "").strip()
        url = item.get("url", "").strip()
        if not title:
            continue
        if url:
            links.append(f"[{title}]({url})")
        else:
            links.append(title)
    return "; ".join(links)


def render_chapter_markdown(
    chapter: StructureChapter,
    segments: list[RenderedSegment],
    output_language: str,
    chapter_reflection: dict[str, object] | None = None,
) -> str:
    """Render one chapter's deep read markdown."""
    labels = markdown_labels(output_language)
    lines = [f'# {_chapter_heading(chapter)}', ""]

    for segment in segments:
        reactions = [
            reaction
            for reaction in segment.get("reactions", [])
            if reaction.get("type") != "silent"
        ]
        if segment.get("verdict") == "skip" or not reactions:
            continue

        separator = "：" if output_language == "zh" else ": "
        lines.append(
            f'## {labels["section"]} {display_segment_id(chapter, segment["segment_id"])}{separator}{segment["summary"]}'
        )
        lines.append("")

        for reaction in reactions:
            lines.append(_reaction_heading(reaction, labels))

            anchor_quote = reaction.get("anchor_quote", "").strip()
            if anchor_quote:
                lines.append("")
                lines.append(f'> "{anchor_quote}"')

            note = _reaction_note(reaction)
            if note:
                lines.append("")
                lines.append(note)

            if reaction.get("type") == "curious" and reaction.get("search_query"):
                lines.append("")
                lines.append(f'> 🔎 _{labels["search"]}: {reaction.get("search_query", "")}_')
                search_links = _search_links(reaction)
                if search_links:
                    lines.append(f'> {labels["sources"]}: {search_links}')
            lines.append("")

        lines.append("---")
        lines.append("")

    insights = []
    if isinstance(chapter_reflection, dict):
        raw_insights = chapter_reflection.get("chapter_insights", [])
        if isinstance(raw_insights, list):
            for item in raw_insights:
                text = str(item or "").strip()
                if text:
                    insights.append(text)
    if insights:
        heading = "章节回看" if output_language == "zh" else "Chapter Reflection"
        lines.append(f"## {heading}")
        lines.append("")
        for item in insights:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
