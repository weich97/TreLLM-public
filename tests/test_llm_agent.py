import json
from pathlib import Path

import pytest

from tradearena.agents.llm import DeepSeekLLMAnalyst
from tradearena.core.domain import Bar, MarketSnapshot, PortfolioState
from tradearena.factory import build_default_system


def test_deepseek_llm_analyst_replays_cache_without_key(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    cache = tmp_path / "cache.jsonl"
    analyst = DeepSeekLLMAnalyst(cache_path=str(cache), model="test-model")
    snapshot = MarketSnapshot(
        timestamp=__import__("datetime").datetime(2026, 1, 1),
        bars={
            "BTC-USD": Bar(
                symbol="BTC-USD",
                timestamp=__import__("datetime").datetime(2026, 1, 1),
                open=100.0,
                high=105.0,
                low=98.0,
                close=104.0,
                volume=1000.0,
            )
        },
    )
    prompt = analyst._prompt(snapshot, PortfolioState(cash=100000.0), memory=None)
    prompt_hash = __import__("hashlib").sha256(prompt.encode("utf-8")).hexdigest()
    cache.write_text(
        json.dumps(
            {
                "cache_key": f"test-model:{prompt_hash}",
                "model": "test-model",
                "prompt_hash": prompt_hash,
                "prompt": prompt,
                "response_text": json.dumps(
                    {
                        "signals": [
                            {
                                "symbol": "BTC-USD",
                                "score": 0.25,
                                "confidence": 0.7,
                                "horizon": "1w",
                                "rationale": "cached response",
                                "risk_notes": "moderate volatility",
                            }
                        ]
                    }
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    signals = analyst.analyze(snapshot, PortfolioState(cash=100000.0), memory=None)

    assert len(signals) == 1
    assert signals[0].symbol == "BTC-USD"
    assert signals[0].score == 0.25
    assert signals[0].metadata["llm_call"] is True
    assert "response_text" not in signals[0].metadata
    assert isinstance(signals[0].metadata["response_hash"], str)
    assert analyst._call_trace == [
        {
            "prompt_hash": prompt_hash,
            "response_hash": signals[0].metadata["response_hash"],
            "sample_index": 0,
            "cache_hit": True,
        }
    ]


def test_sample_index_uses_distinct_cache_keys(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    cache = tmp_path / "cache.jsonl"
    snapshot = MarketSnapshot(
        timestamp=__import__("datetime").datetime(2026, 1, 1),
        bars={
            "BTC-USD": Bar(
                symbol="BTC-USD",
                timestamp=__import__("datetime").datetime(2026, 1, 1),
                open=100.0,
                high=105.0,
                low=98.0,
                close=104.0,
                volume=1000.0,
            )
        },
    )
    base = DeepSeekLLMAnalyst(cache_path=str(cache), model="test-model")
    prompt = base._prompt(snapshot, PortfolioState(cash=100000.0), memory=None)
    prompt_hash = __import__("hashlib").sha256(prompt.encode("utf-8")).hexdigest()

    def entry(cache_key: str, score: float) -> str:
        return json.dumps(
            {
                "cache_key": cache_key,
                "model": "test-model",
                "prompt_hash": prompt_hash,
                "prompt": prompt,
                "response_text": json.dumps(
                    {
                        "signals": [
                            {"symbol": "BTC-USD", "score": score, "confidence": 0.7, "horizon": "1w"}
                        ]
                    }
                ),
            }
        )

    cache.write_text(
        entry(f"deepseek:test-model:{prompt_hash}", 0.25)
        + "\n"
        + entry(f"deepseek:test-model:{prompt_hash}:s1", -0.4)
        + "\n",
        encoding="utf-8",
    )

    sample_zero = DeepSeekLLMAnalyst(cache_path=str(cache), model="test-model", sample_index=0)
    sample_one = DeepSeekLLMAnalyst(cache_path=str(cache), model="test-model", sample_index=1)

    signals_zero = sample_zero.analyze(snapshot, PortfolioState(cash=100000.0), memory=None)
    signals_one = sample_one.analyze(snapshot, PortfolioState(cash=100000.0), memory=None)

    # sample_index=0 keeps the legacy key format; sample_index>0 maps to a distinct entry.
    assert signals_zero[0].score == 0.25
    assert signals_one[0].score == -0.4
    assert signals_zero[0].metadata["sample_index"] == 0
    assert signals_one[0].metadata["sample_index"] == 1


def test_anonymize_symbols_masks_prompt_and_maps_response_back(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    cache = tmp_path / "cache.jsonl"
    snapshot = MarketSnapshot(
        timestamp=__import__("datetime").datetime(2026, 1, 1),
        bars={
            "BTC-USD": Bar(
                symbol="BTC-USD",
                timestamp=__import__("datetime").datetime(2026, 1, 1),
                open=100.0,
                high=105.0,
                low=98.0,
                close=104.0,
                volume=1000.0,
            ),
            "GSPC": Bar(
                symbol="GSPC",
                timestamp=__import__("datetime").datetime(2026, 1, 1),
                open=50.0,
                high=51.0,
                low=49.0,
                close=50.5,
                volume=2000.0,
            ),
        },
    )
    analyst = DeepSeekLLMAnalyst(cache_path=str(cache), model="test-model", anonymize_symbols=True)

    aliases = analyst._symbol_aliases(snapshot)
    assert aliases == {"BTC-USD": "ASSET_01", "GSPC": "ASSET_02"}

    from tradearena.agents.llm import _replace_quoted_symbols

    prompt = _replace_quoted_symbols(
        analyst._prompt(snapshot, PortfolioState(cash=100000.0), memory=None), aliases
    )
    assert "BTC-USD" not in prompt
    assert "GSPC" not in prompt
    assert '"ASSET_01"' in prompt and '"ASSET_02"' in prompt

    prompt_hash = __import__("hashlib").sha256(prompt.encode("utf-8")).hexdigest()
    cache.write_text(
        json.dumps(
            {
                "cache_key": f"deepseek:test-model:{prompt_hash}",
                "model": "test-model",
                "prompt_hash": prompt_hash,
                "prompt": prompt,
                "response_text": json.dumps(
                    {
                        "signals": [
                            {"symbol": "ASSET_01", "score": 0.3, "confidence": 0.6, "horizon": "1w"},
                            {"symbol": "ASSET_02", "score": -0.2, "confidence": 0.5, "horizon": "1w"},
                        ]
                    }
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    signals = analyst.analyze(snapshot, PortfolioState(cash=100000.0), memory=None)

    assert {signal.symbol for signal in signals} == {"BTC-USD", "GSPC"}
    assert all(signal.metadata["symbols_anonymized"] is True for signal in signals)


def test_llm_cache_is_lazy_loaded_until_file_changes(tmp_path: Path):
    cache = tmp_path / "cache.jsonl"
    cache.write_text(
        json.dumps(
            {
                "cache_key": "provider:model:prompt",
                "provider": "provider",
                "model": "model",
                "prompt_hash": "prompt",
                "response_text": "{}",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    analyst = DeepSeekLLMAnalyst(cache_path=str(cache), model="model", provider="provider")

    first = analyst._cache()
    second = analyst._cache()

    assert first is second
    analyst._append_cache(
        {
            "cache_key": "provider:model:prompt-2",
            "provider": "provider",
            "model": "model",
            "prompt_hash": "prompt-2",
            "response_text": "{}",
        }
    )
    assert "provider:model:prompt-2" in analyst._cache()


def test_placebo_risk_feedback_keeps_prompt_shape():
    analyst = DeepSeekLLMAnalyst(model="test-model", risk_feedback_mode="placebo")
    snapshot = MarketSnapshot(
        timestamp=__import__("datetime").datetime(2026, 1, 1),
        bars={
            "BTC-USD": Bar(
                symbol="BTC-USD",
                timestamp=__import__("datetime").datetime(2026, 1, 1),
                open=100.0,
                high=105.0,
                low=98.0,
                close=104.0,
                volume=1000.0,
            )
        },
    )
    memory = type(
        "Memory",
        (),
        {
            "events": [
                {
                    "payload": {
                        "risk_report": {"clipped_count": 2, "blocked_count": 1},
                        "execution_report": {"rejected_orders": 1, "pending_orders": 0, "total_slippage": 3.4},
                        "risk_violations": ["max_position"],
                        "equity": 100000.0,
                    }
                }
            ]
        },
    )()

    prompt = json.loads(analyst._prompt(snapshot, PortfolioState(cash=100000.0), memory=memory))

    assert "recent_risk_feedback" in prompt
    assert "long_term_risk_memory" in prompt
    assert prompt["recent_risk_feedback"][0]["clipped_count"] == 0
    assert prompt["long_term_risk_memory"]["risk_gate_rate"] == 0.0


def test_weights_only_mode_replays_target_weights_without_rationale(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    cache = tmp_path / "cache.jsonl"
    analyst = DeepSeekLLMAnalyst(cache_path=str(cache), model="test-model", output_mode="weights_only")
    timestamp = __import__("datetime").datetime(2026, 1, 1)
    snapshot = MarketSnapshot(
        timestamp=timestamp,
        bars={
            "BTC-USD": Bar("BTC-USD", timestamp, open=100.0, high=105.0, low=98.0, close=104.0, volume=1000.0)
        },
    )
    prompt = analyst._prompt(snapshot, PortfolioState(cash=100000.0), memory=None)
    prompt_hash = __import__("hashlib").sha256(prompt.encode("utf-8")).hexdigest()
    cache.write_text(
        json.dumps(
            {
                "cache_key": f"deepseek:test-model:{prompt_hash}",
                "model": "test-model",
                "provider": "deepseek",
                "prompt_hash": prompt_hash,
                "prompt": prompt,
                "response_text": json.dumps(
                    {"weights": [{"symbol": "BTC-USD", "target_weight": 0.35, "confidence": 0.9, "horizon": "1w"}]}
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    signals = analyst.analyze(snapshot, PortfolioState(cash=100000.0), memory=None)

    assert len(signals) == 1
    assert abs(signals[0].score - 0.07) < 1e-12
    assert signals[0].rationale == ""
    assert signals[0].metadata["llm_output_mode"] == "weights_only"


def test_contrarian_feedback_injects_severe_audit_report():
    analyst = DeepSeekLLMAnalyst(model="test-model", risk_feedback_mode="contrarian")
    timestamp = __import__("datetime").datetime(2026, 1, 1)
    snapshot = MarketSnapshot(
        timestamp=timestamp,
        bars={
            "BTC-USD": Bar("BTC-USD", timestamp, open=100.0, high=105.0, low=98.0, close=104.0, volume=1000.0)
        },
    )

    prompt = json.loads(analyst._prompt(snapshot, PortfolioState(cash=100000.0), memory=None))

    assert prompt["recent_risk_feedback"][0]["clipped_count"] >= 6
    assert prompt["long_term_risk_memory"]["risk_gate_rate"] == 0.92


def test_masked_timestamp_prompt_uses_relative_step():
    analyst = DeepSeekLLMAnalyst(model="test-model", mask_timestamps=True)
    timestamp = __import__("datetime").datetime(2022, 3, 8)
    snapshot = MarketSnapshot(
        timestamp=timestamp,
        bars={
            "BTC-USD": Bar("BTC-USD", timestamp, open=100.0, high=105.0, low=98.0, close=104.0, volume=1000.0)
        },
    )
    memory = type("Memory", (), {"events": [{"payload": {}}, {"payload": {}}]})()

    prompt = json.loads(analyst._prompt(snapshot, PortfolioState(cash=100000.0), memory=memory))

    assert prompt["timestamp"] == "T+2"
    assert "2022" not in json.dumps(prompt)


def test_poe_provider_requires_key_or_cache_without_cached_response(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TRADEARENA_TEST_POE_KEY", raising=False)
    cache = tmp_path / "empty.jsonl"
    analyst = DeepSeekLLMAnalyst(
        model="gpt-5.5",
        api_model="gpt-5.5",
        provider="poe",
        api_key_env="TRADEARENA_TEST_POE_KEY",
        api_base_url="https://api.poe.com/v1",
        api_protocol="openai_chat_completions",
        use_response_format=False,
        cache_path=str(cache),
    )
    timestamp = __import__("datetime").datetime(2026, 1, 1)
    snapshot = MarketSnapshot(
        timestamp=timestamp,
        bars={
            "BTC-USD": Bar("BTC-USD", timestamp, open=100.0, high=105.0, low=98.0, close=104.0, volume=1000.0)
        },
    )

    with pytest.raises(RuntimeError, match="TRADEARENA_TEST_POE_KEY is not set"):
        analyst.analyze(snapshot, PortfolioState(cash=100000.0), memory=None)


def test_ollama_analyst_uses_local_openai_compatible_endpoint_without_key(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TRADEARENA_OLLAMA_API_KEY", raising=False)
    monkeypatch.setenv("TRADEARENA_OLLAMA_BASE_URL", "http://localhost:11434/v1")

    system = build_default_system(
        analyst_names=("ollama-llm",),
        llm_model="llama3.2",
        llm_cache_path=str(tmp_path / "ollama.jsonl"),
        periods=3,
    )

    analyst = system.analysts[0]
    assert isinstance(analyst, DeepSeekLLMAnalyst)
    assert analyst.provider == "ollama"
    assert analyst.api_base_url == "http://localhost:11434/v1"
    assert analyst.require_api_key is False
