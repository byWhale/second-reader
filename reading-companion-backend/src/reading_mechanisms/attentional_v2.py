"""Phase 1-7 adapter scaffold for the attentional_v2 reading mechanism."""

from __future__ import annotations

from pathlib import Path

from src.attentional_v2.storage import (
    ATTENTIONAL_V2_MECHANISM_KEY,
    artifact_map,
    initialize_artifact_tree,
)
from src.attentional_v2.survey import write_book_survey_artifacts
from src.reading_core import BookDocument
from src.reading_core.runtime_contracts import MechanismInfo, ParseRequest, ParseResult, ReadRequest, ReadResult


class AttentionalV2Mechanism:
    """Thin adapter for the in-progress attentional_v2 mechanism."""

    info = MechanismInfo(
        key=ATTENTIONAL_V2_MECHANISM_KEY,
        label="Attentional V2 scaffold (Phase 1-7)",
    )

    @property
    def key(self) -> str:
        """Backwards-compatible access to the mechanism key."""

        return self.info.key

    @property
    def label(self) -> str:
        """Backwards-compatible access to the mechanism label."""

        return self.info.label

    def initialize_artifacts(self, output_dir: Path) -> dict[str, object]:
        """Initialize the mechanism shell and schema-bearing Phase 1 artifacts."""

        return initialize_artifact_tree(output_dir)

    def describe_artifact_map(self, output_dir: Path) -> dict[str, str]:
        """Return the concrete Phase 1 artifact map for one output directory."""

        return artifact_map(output_dir)

    def build_survey_artifacts(
        self,
        output_dir: Path,
        book_document: BookDocument,
        *,
        policy_snapshot: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Persist the orientation-only survey artifacts for one parsed book."""

        return write_book_survey_artifacts(
            output_dir,
            book_document,
            policy_snapshot=policy_snapshot,
        )

    def parse_book(self, request: ParseRequest) -> ParseResult:
        """Attentional V2 parse is not implemented in Phase 1-7."""

        raise NotImplementedError(
            "attentional_v2 Phase 1-7 provides shell, schema, sentence-substrate, survey, intake, interpretive-node, bridge-state, slow-cycle, and resume scaffolding only; "
            "its parse path will land in later phases."
        )

    def read_book(self, request: ReadRequest) -> ReadResult:
        """Attentional V2 reading is not implemented in Phase 1-7."""

        raise NotImplementedError(
            "attentional_v2 Phase 1-7 provides shell, schema, sentence-substrate, survey, intake, interpretive-node, bridge-state, slow-cycle, and resume scaffolding only; "
            "its reading loop will land in later phases."
        )
