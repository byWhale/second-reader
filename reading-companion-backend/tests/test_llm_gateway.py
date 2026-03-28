"""Tests for the shared backend LLM gateway and registry."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from src.iterator_reader import llm_utils
from src.reading_runtime import artifacts as runtime_artifacts
from src.reading_runtime.llm_gateway import (
    CONTRACT_ADAPTERS,
    JsonlTraceSink,
    ReaderLLMError,
    clear_llm_gateway_runtime_state,
    eval_trace_context,
    get_llm_profile_stable_concurrency,
    get_llm_provider_stable_concurrency,
    invoke_json,
    llm_invocation_scope,
    runtime_trace_context,
)
from src.reading_runtime.llm_registry import (
    DEFAULT_DATASET_REVIEW_PROFILE_ID,
    DEFAULT_EVAL_JUDGE_PROFILE_ID,
    DEFAULT_RUNTIME_PROFILE_ID,
    LLMRegistryError,
    clear_llm_registry_cache,
    get_llm_profile,
    get_llm_registry,
)


@dataclass
class _FakeResponse:
    content: str


class _RecordingAdapter:
    def __init__(self, behavior: dict[str, str] | None = None, *, response_content: str | None = None):
        self.behavior = behavior or {}
        self.response_content = response_content or '{"ok": true}'
        self.calls: list[dict[str, Any]] = []

    def invoke(
        self,
        messages: list[Any],
        *,
        provider: Any,
        profile: Any,
        api_key: str,
        timeout_seconds: int,
    ) -> Any:
        self.calls.append(
            {
                "provider_id": provider.provider_id,
                "contract": provider.contract,
                "model": profile.model,
                "api_key": api_key,
                "timeout_seconds": timeout_seconds,
                "message_count": len(messages),
            }
        )
        action = self.behavior.get(api_key, "ok")
        if action == "auth_error":
            raise RuntimeError("invalid api key")
        if action == "timeout":
            raise RuntimeError("timed out")
        payload = self.response_content.replace("__API_KEY__", api_key)
        return _FakeResponse(payload)


class _SleepingRecordingAdapter(_RecordingAdapter):
    def __init__(self, delay_seconds: float):
        super().__init__()
        self.delay_seconds = delay_seconds
        self._lock = threading.Lock()
        self.active_calls = 0
        self.max_active_calls = 0

    def invoke(
        self,
        messages: list[Any],
        *,
        provider: Any,
        profile: Any,
        api_key: str,
        timeout_seconds: int,
    ) -> Any:
        with self._lock:
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            time.sleep(self.delay_seconds)
            return super().invoke(
                messages,
                provider=provider,
                profile=profile,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
            )
        finally:
            with self._lock:
                self.active_calls -= 1


@pytest.fixture(autouse=True)
def _clear_registry_and_env(monkeypatch: pytest.MonkeyPatch):
    for key in [
        "LLM_REGISTRY_JSON",
        "LLM_REGISTRY_PATH",
        "LLM_PROVIDER_CONTRACT",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "LLM_DATASET_REVIEW_MODEL",
        "LLM_EVAL_JUDGE_MODEL",
        "PRIMARY_KEY",
        "POOL_A",
        "POOL_B",
        "ANTHROPIC_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)
    clear_llm_gateway_runtime_state()
    clear_llm_registry_cache()
    yield
    clear_llm_gateway_runtime_state()
    clear_llm_registry_cache()


def _set_registry(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]) -> None:
    monkeypatch.setenv("LLM_REGISTRY_JSON", json.dumps(payload))
    clear_llm_registry_cache()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_registry_parses_structured_profiles_and_env_keys(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRIMARY_KEY", "secret-a")
    _set_registry(
        monkeypatch,
        {
            "providers": [
                {
                    "provider_id": "anthropic_primary",
                    "contract": "anthropic",
                    "api_key_env": "PRIMARY_KEY",
                    "supported_models": ["claude-opus-4-6"],
                    "timeout_seconds": 90,
                    "retry_attempts": 2,
                    "max_concurrency": 3,
                }
            ],
            "profiles": [
                {
                    "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
                {
                    "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "max_concurrency": 1,
                },
                {
                    "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "timeout_seconds": 120,
                },
            ],
        },
    )

    registry = get_llm_registry()
    provider = registry.get_provider("anthropic_primary")
    runtime_profile = get_llm_profile(DEFAULT_RUNTIME_PROFILE_ID)

    assert registry.source == "env:LLM_REGISTRY_JSON"
    assert provider.resolved_key_pool() == [{"slot_id": "PRIMARY_KEY", "api_key": "secret-a"}]
    assert runtime_profile.model == "claude-opus-4-6"
    assert runtime_profile.provider_id == "anthropic_primary"


def test_registry_rejects_missing_required_profiles(monkeypatch: pytest.MonkeyPatch):
    _set_registry(
        monkeypatch,
        {
            "providers": [
                {
                    "provider_id": "anthropic_primary",
                    "contract": "anthropic",
                    "api_key_env": "PRIMARY_KEY",
                    "supported_models": ["claude-opus-4-6"],
                }
            ],
            "profiles": [
                {
                    "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                }
            ],
        },
    )

    with pytest.raises(LLMRegistryError, match="missing required profile"):
        get_llm_registry()


def test_same_model_key_failover_succeeds_and_emits_runtime_trace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POOL_A", "bad-key")
    monkeypatch.setenv("POOL_B", "good-key")
    _set_registry(
        monkeypatch,
        {
            "providers": [
                {
                    "provider_id": "anthropic_primary",
                    "contract": "anthropic",
                    "key_pool_envs": ["POOL_A", "POOL_B"],
                    "supported_models": ["claude-opus-4-6"],
                    "retry_attempts": 1,
                    "max_concurrency": 2,
                }
            ],
            "profiles": [
                {
                    "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "retry_attempts": 1,
                },
                {
                    "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "retry_attempts": 1,
                },
                {
                    "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "retry_attempts": 1,
                },
            ],
        },
    )
    adapter = _RecordingAdapter(
        {"bad-key": "auth_error", "good-key": "ok"},
        response_content='{"ok": true, "api_key": "__API_KEY__"}',
    )
    monkeypatch.setitem(CONTRACT_ADAPTERS, "anthropic", adapter)

    output_dir = tmp_path / "output" / "demo"
    with llm_invocation_scope(
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        trace_context=runtime_trace_context(
            output_dir,
            mechanism_key="iterator_v1",
            debug_enabled=True,
            stage="read",
            node="think",
        ),
    ):
        payload = invoke_json("system", "user", {})

    standard_rows = _read_jsonl(runtime_artifacts.llm_standard_trace_file(output_dir))
    debug_rows = _read_jsonl(runtime_artifacts.llm_debug_trace_file(output_dir, "iterator_v1"))

    assert payload == {"ok": True, "api_key": "good-key"}
    assert [call["api_key"] for call in adapter.calls] == ["bad-key", "good-key"]
    assert standard_rows[-1]["status"] == "ok"
    assert standard_rows[-1]["fallback"]["used_failover"] is True
    assert standard_rows[-1]["fallback"]["key_slots_tried"] == ["POOL_A", "POOL_B"]
    assert debug_rows[-1]["response_excerpt"]


def test_cross_model_fallback_is_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POOL_A", "good-key")
    monkeypatch.setenv("POOL_B", "other-key")
    _set_registry(
        monkeypatch,
        {
            "providers": [
                {
                    "provider_id": "anthropic_primary",
                    "contract": "anthropic",
                    "key_pool_envs": ["POOL_A"],
                    "supported_models": ["claude-opus-4-6"],
                },
                {
                    "provider_id": "gemini_backup",
                    "contract": "google_genai",
                    "key_pool_envs": ["POOL_B"],
                    "supported_models": ["gemini-3.1-pro"],
                },
            ],
            "profiles": [
                {
                    "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "fallback_provider_ids": ["gemini_backup"],
                    "allow_cross_provider_failover": True,
                    "model": "claude-opus-4-6",
                },
                {
                    "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
                {
                    "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
            ],
        },
    )
    monkeypatch.setitem(CONTRACT_ADAPTERS, "anthropic", _RecordingAdapter())
    monkeypatch.setitem(CONTRACT_ADAPTERS, "google_genai", _RecordingAdapter())

    with llm_invocation_scope(profile_id=DEFAULT_RUNTIME_PROFILE_ID):
        with pytest.raises(LLMRegistryError, match="cannot use fallback provider"):
            invoke_json("system", "user", {})


def test_eval_trace_context_writes_eval_run_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRIMARY_KEY", "judge-key")
    _set_registry(
        monkeypatch,
        {
            "providers": [
                {
                    "provider_id": "anthropic_primary",
                    "contract": "anthropic",
                    "api_key_env": "PRIMARY_KEY",
                    "supported_models": ["claude-opus-4-6"],
                }
            ],
            "profiles": [
                {
                    "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
                {
                    "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
                {
                    "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
            ],
        },
    )
    adapter = _RecordingAdapter()
    monkeypatch.setitem(CONTRACT_ADAPTERS, "anthropic", adapter)

    run_dir = tmp_path / "eval-run"
    with llm_invocation_scope(
        profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
        trace_context=eval_trace_context(
            run_dir,
            eval_target="packet_review:demo",
            stage="adjudication",
            node="final",
        ),
    ):
        payload = invoke_json("system", "user", {})

    standard_rows = _read_jsonl(run_dir / "llm_traces" / "standard.jsonl")
    assert payload["ok"] is True
    assert adapter.calls[0]["api_key"] == "judge-key"
    assert standard_rows[-1]["eval_target"] == "packet_review:demo"
    assert standard_rows[-1]["stage"] == "adjudication"
    assert standard_rows[-1]["node"] == "final"


def test_legacy_wrapper_uses_shared_gateway(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_PROVIDER_CONTRACT", "anthropic")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("LLM_API_KEY", "legacy-key")
    monkeypatch.setenv("LLM_MODEL", "claude-opus-4-6")
    clear_llm_registry_cache()
    adapter = _RecordingAdapter()
    monkeypatch.setitem(CONTRACT_ADAPTERS, "anthropic", adapter)

    payload = llm_utils.invoke_json("system", "user", {})

    assert payload["ok"] is True
    assert adapter.calls[0]["api_key"] == "legacy-key"
    assert adapter.calls[0]["model"] == "claude-opus-4-6"


def test_attentional_node_uses_shared_runtime_trace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.attentional_v2.nodes import zoom_read
    from src.attentional_v2.schemas import (
        build_default_reader_policy,
        build_empty_anchor_memory,
        build_empty_knowledge_activations,
        build_empty_working_pressure,
    )

    monkeypatch.setenv("PRIMARY_KEY", "runtime-key")
    _set_registry(
        monkeypatch,
        {
            "providers": [
                {
                    "provider_id": "anthropic_primary",
                    "contract": "anthropic",
                    "api_key_env": "PRIMARY_KEY",
                    "supported_models": ["claude-opus-4-6"],
                }
            ],
            "profiles": [
                {
                    "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
                {
                    "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
                {
                    "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
            ],
        },
    )
    adapter = _RecordingAdapter(response_content='{"local_interpretation": "Focused on the hinge."}')
    monkeypatch.setitem(CONTRACT_ADAPTERS, "anthropic", adapter)

    output_dir = tmp_path / "output" / "attn-demo"
    with llm_invocation_scope(
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        trace_context=runtime_trace_context(output_dir, mechanism_key="attentional_v2"),
    ):
        result = zoom_read(
            focal_sentence={"sentence_id": "s1", "text": "Alpha hinge line.", "text_role": "body"},
            local_context_sentences=[],
            working_pressure=build_empty_working_pressure(),
            anchor_memory=build_empty_anchor_memory(),
            knowledge_activations=build_empty_knowledge_activations(),
            reader_policy=build_default_reader_policy(),
            output_language="en",
            output_dir=output_dir,
        )

    standard_rows = _read_jsonl(runtime_artifacts.llm_standard_trace_file(output_dir))
    assert result["local_interpretation"] == "Focused on the hinge."
    assert standard_rows[-1]["mechanism_key"] == "attentional_v2"
    assert standard_rows[-1]["stage"] == "phase4"
    assert standard_rows[-1]["node"] == "zoom_read"


def test_iterator_parse_node_uses_shared_runtime_trace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.iterator_reader.parse import segment_chapter_semantically

    monkeypatch.setenv("PRIMARY_KEY", "runtime-key")
    _set_registry(
        monkeypatch,
        {
            "providers": [
                {
                    "provider_id": "anthropic_primary",
                    "contract": "anthropic",
                    "api_key_env": "PRIMARY_KEY",
                    "supported_models": ["claude-opus-4-6"],
                }
            ],
            "profiles": [
                {
                    "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
                {
                    "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
                {
                    "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                },
            ],
        },
    )
    adapter = _RecordingAdapter(
        response_content=json.dumps(
            {
                "segments": [
                    {
                        "paragraph_start": 1,
                        "paragraph_end": 2,
                        "summary": "Keeps the two short paragraphs together.",
                    }
                ]
            }
        )
    )
    monkeypatch.setitem(CONTRACT_ADAPTERS, "anthropic", adapter)

    output_dir = tmp_path / "output" / "iterator-demo"
    with llm_invocation_scope(
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        trace_context=runtime_trace_context(output_dir, mechanism_key="iterator_v1"),
    ):
        segments = segment_chapter_semantically(
            1,
            "Chapter 1",
            "Alpha.\n\nBeta.",
            "en",
            paragraphs=["Alpha.", "Beta."],
        )

    standard_rows = _read_jsonl(runtime_artifacts.llm_standard_trace_file(output_dir))
    assert len(segments) == 1
    assert standard_rows[-1]["mechanism_key"] == "iterator_v1"
    assert standard_rows[-1]["stage"] == "parse"
    assert standard_rows[-1]["node"] == "semantic_segmentation"


def test_same_key_parallelism_allows_multiple_inflight_calls(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRIMARY_KEY", "same-key")
    _set_registry(
        monkeypatch,
        {
            "providers": [
                {
                    "provider_id": "anthropic_primary",
                    "contract": "anthropic",
                    "api_key_env": "PRIMARY_KEY",
                    "supported_models": ["claude-opus-4-6"],
                    "retry_attempts": 1,
                    "max_concurrency": 12,
                    "initial_max_concurrency": 6,
                    "probe_max_concurrency": 12,
                }
            ],
            "profiles": [
                {
                    "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "retry_attempts": 1,
                    "max_concurrency": 12,
                    "default_burst_concurrency": 12,
                },
                {
                    "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "retry_attempts": 1,
                    "max_concurrency": 12,
                    "default_burst_concurrency": 12,
                },
                {
                    "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "retry_attempts": 1,
                    "max_concurrency": 12,
                    "default_burst_concurrency": 12,
                },
            ],
        },
    )
    adapter = _SleepingRecordingAdapter(delay_seconds=0.1)
    monkeypatch.setitem(CONTRACT_ADAPTERS, "anthropic", adapter)

    results: list[dict[str, Any]] = []

    def _invoke() -> None:
        with llm_invocation_scope(profile_id=DEFAULT_RUNTIME_PROFILE_ID):
            results.append(invoke_json("system", "user", {}))

    first = threading.Thread(target=_invoke)
    second = threading.Thread(target=_invoke)
    first.start()
    second.start()
    first.join()
    second.join()

    assert len(results) == 2
    assert adapter.max_active_calls >= 2


def test_provider_backoff_reduces_stable_limit_after_timeout_pressure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRIMARY_KEY", "timing-key")
    _set_registry(
        monkeypatch,
        {
            "providers": [
                {
                    "provider_id": "anthropic_primary",
                    "contract": "anthropic",
                    "api_key_env": "PRIMARY_KEY",
                    "supported_models": ["claude-opus-4-6"],
                    "retry_attempts": 1,
                    "max_concurrency": 12,
                    "initial_max_concurrency": 6,
                    "probe_max_concurrency": 12,
                    "min_stable_concurrency": 2,
                    "backoff_window_seconds": 30,
                    "recover_window_seconds": 30,
                }
            ],
            "profiles": [
                {
                    "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "retry_attempts": 1,
                    "max_concurrency": 12,
                    "default_burst_concurrency": 12,
                },
                {
                    "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "retry_attempts": 1,
                    "max_concurrency": 12,
                    "default_burst_concurrency": 12,
                },
                {
                    "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                    "provider_id": "anthropic_primary",
                    "model": "claude-opus-4-6",
                    "retry_attempts": 1,
                    "max_concurrency": 12,
                    "default_burst_concurrency": 12,
                },
            ],
        },
    )
    adapter = _RecordingAdapter({"timing-key": "timeout"})
    monkeypatch.setitem(CONTRACT_ADAPTERS, "anthropic", adapter)

    with llm_invocation_scope(profile_id=DEFAULT_RUNTIME_PROFILE_ID):
        with pytest.raises(ReaderLLMError):
            invoke_json("system", "user", {})
        with pytest.raises(ReaderLLMError):
            invoke_json("system", "user", {})

    assert get_llm_provider_stable_concurrency("anthropic_primary") == 5
    assert get_llm_profile_stable_concurrency(DEFAULT_RUNTIME_PROFILE_ID) == 5
