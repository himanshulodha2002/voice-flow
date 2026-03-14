"""Tests for TextRewriter — suspicious text detection (no real LLM needed)."""

from __future__ import annotations

from voiceflow.config import RewriterConfig
from voiceflow.rewriter import TextRewriter


def _make_rewriter(**overrides) -> TextRewriter:
    return TextRewriter(RewriterConfig(**overrides))


class TestIsLoaded:
    def test_not_loaded_initially(self):
        r = _make_rewriter()
        assert not r.is_loaded

    def test_loaded_after_setting_model(self):
        r = _make_rewriter()
        r._model = "fake"
        assert r.is_loaded


class TestUnload:
    def test_unload_clears_state(self):
        r = _make_rewriter()
        r._model = "fake"
        r._tokenizer = "fake"
        r._generate = lambda: None
        r.unload()
        assert r._model is None
        assert r._tokenizer is None
        assert r._generate is None
        assert not r.is_loaded


class TestSuspiciousDetection:
    def test_clean_text_not_suspicious(self):
        r = _make_rewriter()
        assert not r._is_suspicious("hello world", "Hello world.")

    def test_injected_command(self):
        r = _make_rewriter()
        assert r._is_suspicious("hello world", "hello world; rm -rf /")

    def test_injected_url(self):
        r = _make_rewriter()
        assert r._is_suspicious("check the site", "check https://evil.com")

    def test_url_in_both_not_suspicious(self):
        r = _make_rewriter()
        assert not r._is_suspicious(
            "visit https://example.com", "Visit https://example.com."
        )

    def test_low_word_overlap(self):
        r = _make_rewriter(min_word_overlap=0.5)
        assert r._is_suspicious(
            "hello world today",
            "completely different sentence entirely"
        )

    def test_high_word_overlap_ok(self):
        r = _make_rewriter(min_word_overlap=0.3)
        assert not r._is_suspicious(
            "the quick brown fox",
            "The quick brown fox."
        )

    def test_script_injection(self):
        r = _make_rewriter()
        assert r._is_suspicious("hello", "hello <script>alert(1)</script>")

    def test_eval_injection(self):
        r = _make_rewriter()
        assert r._is_suspicious("print something", "eval(something)")

    def test_sudo_injection(self):
        r = _make_rewriter()
        assert r._is_suspicious("run update", "sudo apt update")


class TestRewriteGuards:
    """Test the rewrite method's guard logic with a fake generate function."""

    def _make_loaded_rewriter(self, generate_output: str) -> TextRewriter:
        r = _make_rewriter()
        r._model = "fake"
        r._tokenizer = type("T", (), {
            "apply_chat_template": lambda self, *a, **kw: "prompt",
        })()
        r._generate = lambda *a, **kw: generate_output
        return r

    def test_empty_input_returns_empty(self):
        r = self._make_loaded_rewriter("anything")
        assert r.rewrite("") == ""
        assert r.rewrite("   ") == ""

    def test_hallucination_guard_too_long(self):
        r = self._make_loaded_rewriter("x" * 1000)
        result = r.rewrite("short input")
        assert result == "short input"  # falls back to raw

    def test_empty_output_falls_back(self):
        r = self._make_loaded_rewriter("")
        result = r.rewrite("hello world")
        assert result == "hello world"

    def test_clean_output_passes(self):
        r = self._make_loaded_rewriter("Hello world.")
        result = r.rewrite("hello world")
        assert result == "Hello world."
