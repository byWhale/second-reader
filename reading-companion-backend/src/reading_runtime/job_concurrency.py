"""Shared default concurrency policy for evaluation and runtime jobs."""

from __future__ import annotations

import contextvars
from concurrent.futures import Executor, Future
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from .llm_gateway import get_llm_profile_stable_concurrency
from .llm_registry import DEFAULT_RUNTIME_PROFILE_ID, get_llm_profile_default_burst_concurrency


T = TypeVar("T")


@dataclass(frozen=True)
class JobConcurrencyPolicy:
    """Resolved worker policy for one job family."""

    job_kind: str
    profile_id: str
    task_count: int
    llm_budget: int
    per_worker_parallelism: int
    worker_count: int


def submit_inherited_context(executor: Executor, fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> Future[T]:
    """Submit work while preserving the caller's contextvars into the worker thread."""

    context = contextvars.copy_context()
    return executor.submit(lambda: context.run(fn, *args, **kwargs))


def resolve_worker_policy(
    *,
    job_kind: str,
    profile_id: str,
    task_count: int,
    per_worker_parallelism: int = 1,
    explicit_max_workers: int | None = None,
) -> JobConcurrencyPolicy:
    """Derive the default worker count for one concurrent job family."""

    normalized_task_count = max(0, int(task_count))
    normalized_parallelism = max(1, int(per_worker_parallelism))
    llm_budget = max(
        1,
        min(
            get_llm_profile_stable_concurrency(profile_id),
            get_llm_profile_default_burst_concurrency(profile_id),
        ),
    )
    if normalized_task_count <= 1:
        worker_count = 1 if normalized_task_count == 1 else 0
    else:
        worker_count = max(1, llm_budget // normalized_parallelism)
        worker_count = min(worker_count, normalized_task_count)
    if explicit_max_workers is not None and explicit_max_workers > 0:
        worker_count = min(worker_count or 0, int(explicit_max_workers))
    if normalized_task_count > 0:
        worker_count = max(1, worker_count)
    return JobConcurrencyPolicy(
        job_kind=job_kind,
        profile_id=profile_id,
        task_count=normalized_task_count,
        llm_budget=llm_budget,
        per_worker_parallelism=normalized_parallelism,
        worker_count=worker_count,
    )


def resolve_runtime_tuning_defaults() -> tuple[int, int, int]:
    """Derive runtime segmentation defaults from the current stable runtime budget."""

    budget = max(1, get_llm_profile_stable_concurrency(DEFAULT_RUNTIME_PROFILE_ID))
    segment_workers = max(1, min(budget, max(1, budget - 2)))
    blocked_workers = max(segment_workers, min(budget, max(2, budget)))
    prefetch_window = max(1, min(blocked_workers, budget))
    return segment_workers, blocked_workers, prefetch_window


__all__ = [
    "JobConcurrencyPolicy",
    "resolve_runtime_tuning_defaults",
    "resolve_worker_policy",
    "submit_inherited_context",
]
