"""LLM-based text rewriting with prompt-injection guards."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from voiceflow.config import RewriterConfig
from voiceflow.log import logger


class TextRewriter:
    """Cleans up transcribed text using a small local LLM via mlx-lm."""

    def __init__(self, cfg: RewriterConfig) -> None:
        self._cfg = cfg
        self._model: Any = None
        self._tokenizer: Any = None
        self._generate: Callable[..., str] | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def warmup(self) -> None:
        from mlx_lm import load, generate

        logger.info("Loading rewrite LLM (%s)...", self._cfg.model)
        kwargs: dict = {}
        if self._cfg.revision:
            kwargs["revision"] = self._cfg.revision
        self._model, self._tokenizer = load(self._cfg.model, **kwargs)
        self._generate = generate
        logger.info("Rewrite LLM ready.")

    def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        self._generate = None
        logger.info("Rewrite LLM unloaded.")

    def rewrite(self, raw_text: str) -> str:
        if not raw_text or not raw_text.strip():
            return ""

        messages = [
            {"role": "system", "content": self._cfg.system_prompt},
            {"role": "user", "content": raw_text},
        ]
        prompt = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False,
        )

        output = self._generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=self._cfg.max_tokens,
            verbose=False,
        )
        cleaned = output.strip()

        # Hallucination guard
        if not cleaned or len(cleaned) > len(raw_text) * self._cfg.max_length_ratio:
            return raw_text

        # Prompt-injection guard
        if self._is_suspicious(raw_text, cleaned):
            return raw_text

        return cleaned

    def _is_suspicious(self, raw: str, cleaned: str) -> bool:
        """Lightweight check for prompt-injection / hallucinated output."""
        raw_lower = raw.lower()
        cleaned_lower = cleaned.lower()

        suspicious_patterns = [
            "rm -", "sudo ", "curl ", "wget ", "chmod ", "mkfs",
            "; drop ", "<script", "javascript:", "eval(", "exec(",
            "import os", "import subprocess", "__import__",
            "http://", "https://", "ftp://", "file://", "data:",
        ]
        for pat in suspicious_patterns:
            if pat in cleaned_lower and pat not in raw_lower:
                return True

        raw_words = set(raw_lower.split())
        cleaned_words = set(cleaned_lower.split())
        if raw_words and cleaned_words:
            overlap = len(raw_words & cleaned_words) / max(len(raw_words), len(cleaned_words))
            if overlap < self._cfg.min_word_overlap:
                return True

        return False
