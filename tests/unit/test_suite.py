"""Unit tests for packages/benchmarks/suite.py."""

import pytest
from packages.benchmarks.suite import (
    BenchmarkCase,
    BenchmarkSuiteConfig,
    expand_suite,
    synthetic_prompt,
)


# ── synthetic_prompt ──────────────────────────────────────────────────────────

class TestSyntheticPrompt:
    def test_non_empty(self):
        assert len(synthetic_prompt(100)) > 0

    def test_rough_token_length(self):
        # 1 token ≈ 4 chars; allow ±50% tolerance
        for target in [50, 200, 500]:
            prompt = synthetic_prompt(target)
            chars = len(prompt)
            approx_tokens = chars / 4
            assert approx_tokens >= target * 0.5, f"too short for target={target}"
            assert approx_tokens <= target * 2.5, f"too long for target={target}"

    def test_returns_string(self):
        assert isinstance(synthetic_prompt(100), str)

    def test_minimum_target(self):
        # Even target=1 should produce something non-empty
        assert len(synthetic_prompt(1)) > 0


# ── BenchmarkCase.name ─────────────────────────────────────────────────────────

class TestBenchmarkCaseName:
    def make_case(self, concurrency=1, prompt=100, output=50, streaming=False):
        return BenchmarkCase(
            suite_name="my_suite",
            model="gpt-4o-mini",
            concurrency=concurrency,
            prompt_length=prompt,
            output_length=output,
            streaming=streaming,
            runs_per_case=5,
            temperature=0.0,
        )

    def test_name_contains_suite(self):
        assert "my_suite" in self.make_case().name

    def test_name_contains_concurrency(self):
        assert "c5" in self.make_case(concurrency=5).name

    def test_name_contains_prompt_length(self):
        assert "p200" in self.make_case(prompt=200).name

    def test_name_contains_output_length(self):
        assert "o150" in self.make_case(output=150).name

    def test_name_sync_mode(self):
        assert "sync" in self.make_case(streaming=False).name

    def test_name_stream_mode(self):
        assert "stream" in self.make_case(streaming=True).name

    def test_names_are_unique_across_cases(self):
        cfg = BenchmarkSuiteConfig(
            name="s",
            model="m",
            concurrency_levels=[1, 5],
            prompt_lengths=[100, 500],
            output_lengths=[50],
            streaming=[False],
            runs_per_case=1,
        )
        cases = expand_suite(cfg)
        names = [c.name for c in cases]
        assert len(names) == len(set(names)), "case names are not unique"


# ── expand_suite ──────────────────────────────────────────────────────────────

class TestExpandSuite:
    def test_cross_product_count(self):
        cfg = BenchmarkSuiteConfig(
            name="test",
            model="gpt-4o-mini",
            concurrency_levels=[1, 5, 10],
            prompt_lengths=[100, 500],
            output_lengths=[50, 200],
            streaming=[False, True],
            runs_per_case=3,
        )
        cases = expand_suite(cfg)
        expected = 3 * 2 * 2 * 2  # concurrency × prompt × output × streaming
        assert len(cases) == expected

    def test_single_combination(self):
        cfg = BenchmarkSuiteConfig(
            name="smoke",
            model="gpt-4o-mini",
            concurrency_levels=[1],
            prompt_lengths=[100],
            output_lengths=[50],
            streaming=[False],
            runs_per_case=5,
        )
        cases = expand_suite(cfg)
        assert len(cases) == 1
        c = cases[0]
        assert c.concurrency == 1
        assert c.prompt_length == 100
        assert c.output_length == 50
        assert c.streaming is False
        assert c.runs_per_case == 5

    def test_all_cases_inherit_model(self):
        cfg = BenchmarkSuiteConfig(
            name="t", model="gpt-4o",
            concurrency_levels=[1, 2],
            prompt_lengths=[100],
            output_lengths=[50],
            streaming=[False],
            runs_per_case=1,
        )
        cases = expand_suite(cfg)
        assert all(c.model == "gpt-4o" for c in cases)

    def test_all_cases_inherit_suite_name(self):
        cfg = BenchmarkSuiteConfig(
            name="my_suite", model="m",
            concurrency_levels=[1],
            prompt_lengths=[100],
            output_lengths=[50],
            streaming=[False],
            runs_per_case=1,
        )
        cases = expand_suite(cfg)
        assert all(c.suite_name == "my_suite" for c in cases)

    def test_streaming_values_present(self):
        cfg = BenchmarkSuiteConfig(
            name="t", model="m",
            concurrency_levels=[1],
            prompt_lengths=[100],
            output_lengths=[50],
            streaming=[False, True],
            runs_per_case=1,
        )
        cases = expand_suite(cfg)
        streaming_flags = {c.streaming for c in cases}
        assert streaming_flags == {True, False}


# ── BenchmarkSuiteConfig validation ──────────────────────────────────────────

class TestBenchmarkSuiteConfig:
    def test_defaults(self):
        cfg = BenchmarkSuiteConfig(name="x", model="m")
        assert cfg.runs_per_case >= 1
        assert cfg.temperature == 0.0

    def test_runs_per_case_min(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BenchmarkSuiteConfig(name="x", model="m", runs_per_case=0)

    def test_temperature_bounds(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BenchmarkSuiteConfig(name="x", model="m", temperature=3.0)
        with pytest.raises(ValidationError):
            BenchmarkSuiteConfig(name="x", model="m", temperature=-0.1)
