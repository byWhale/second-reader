"""Public runtime entrypoints for pluggable backend reading mechanisms."""

from __future__ import annotations

from src.reading_core.runtime_contracts import ParseRequest, ParseResult, ReadRequest, ReadResult
from src.reading_mechanisms import register_builtin_mechanisms

from .mechanisms import (
    ReadingMechanism,
    available_mechanism_keys,
    default_mechanism_key,
    get_mechanism,
    register_mechanism,
)


register_builtin_mechanisms()


def parse_book(request: ParseRequest) -> ParseResult:
    """Parse one book through the selected backend reading mechanism."""

    return get_mechanism(request.mechanism_key).parse_book(request)


def read_book(request: ReadRequest) -> ReadResult:
    """Read one book through the selected backend reading mechanism."""

    return get_mechanism(request.mechanism_key).read_book(request)


__all__ = [
    "ReadingMechanism",
    "ParseRequest",
    "ParseResult",
    "ReadRequest",
    "ReadResult",
    "available_mechanism_keys",
    "default_mechanism_key",
    "get_mechanism",
    "parse_book",
    "read_book",
    "register_mechanism",
]
