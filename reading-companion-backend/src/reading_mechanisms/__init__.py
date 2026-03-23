"""Built-in reading mechanism registrations."""

from __future__ import annotations

from src.reading_runtime.mechanisms import register_mechanism

from .attentional_v2 import AttentionalV2Mechanism
from .iterator_v1 import IteratorV1Mechanism


_BUILTINS_REGISTERED = False


def register_builtin_mechanisms() -> None:
    """Register built-in mechanisms exactly once."""

    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED:
        return
    register_mechanism(IteratorV1Mechanism(), default=True)
    _BUILTINS_REGISTERED = True


__all__ = ["register_builtin_mechanisms", "AttentionalV2Mechanism", "IteratorV1Mechanism"]
