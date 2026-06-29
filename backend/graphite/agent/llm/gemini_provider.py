"""Gemini 2.5 Flash provider via ``google.generativeai``.

The SDK is imported lazily (inside ``_ensure_genai``) so the rest of the backend
imports cleanly even when the dependency or an API key is absent. The provider
returns the model's raw JSON text; parsing into an :class:`AgentResponse` is the
agent's responsibility (single place for parse + retry logic).
"""

from __future__ import annotations

import asyncio
import re
import time

from ..schemas import Message
from .base import LLMResponse

_RETRY_DELAY_RE = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)

# Gemini accepts only "user" and "model" roles in `contents`; system text goes
# into `system_instruction`.
_ROLE_MAP = {"user": "user", "assistant": "model", "tool": "user"}


class GeminiProvider:
    """LLMProvider backed by Gemini 2.5 Flash via google.generativeai."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash",
                 temperature: float = 0.1, max_retries: int = 2,
                 retry_cap_seconds: float = 65.0):
        if not api_key:
            raise ValueError("GeminiProvider requires a non-empty api_key")
        self._api_key = api_key
        self._model_name = model
        self._temperature = temperature
        self._max_retries = max_retries
        self._retry_cap = retry_cap_seconds
        self._genai = None
        self._configured = False

    def _ensure_genai(self):
        if not self._configured:
            import google.generativeai as genai  # local import by design

            genai.configure(api_key=self._api_key)
            self._genai = genai
            self._configured = True
        return self._genai

    @staticmethod
    def _split_messages(messages: list[Message]) -> tuple[str, list[dict]]:
        """Split into (system_instruction, gemini_contents)."""
        system_parts: list[str] = []
        contents: list[dict] = []
        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
                continue
            role = _ROLE_MAP.get(msg.role, "user")
            contents.append({"role": role, "parts": [msg.content]})
        return "\n\n".join(system_parts), contents

    def _generate(self, system_instruction: str, contents: list[dict]) -> str:
        genai = self._ensure_genai()
        model = genai.GenerativeModel(
            self._model_name,
            system_instruction=system_instruction or None,
            generation_config={
                "temperature": self._temperature,
                "response_mime_type": "application/json",
            },
        )
        attempt = 0
        while True:
            try:
                response = model.generate_content(contents)
                return response.text
            except Exception as exc:
                if self._is_rate_limit(exc) and attempt < self._max_retries:
                    delay = min(self._retry_delay(exc), self._retry_cap)
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise self._translate_error(exc) from exc

    @staticmethod
    def _is_rate_limit(exc: Exception) -> bool:
        text = str(exc)
        return ("429" in text or "quota" in text.lower()
                or "ResourceExhausted" in type(exc).__name__)

    def _retry_delay(self, exc: Exception) -> float:
        match = _RETRY_DELAY_RE.search(str(exc))
        if match:
            return float(match.group(1)) + 1.0  # small cushion
        return 30.0

    def _translate_error(self, exc: Exception) -> Exception:
        text = str(exc)
        if self._is_rate_limit(exc):
            return RuntimeError(
                "Gemini rate limit / quota exceeded. The free tier allows only a few "
                "requests per minute — wait ~60s and try again, or use a key with higher quota."
            )
        if "API key" in text or "API_KEY" in text or "PermissionDenied" in type(exc).__name__:
            return RuntimeError("Gemini API key was rejected — check GEMINI_API_KEY.")
        return exc

    async def complete(
        self,
        messages: list[Message],
        tools: list | None = None,
    ) -> LLMResponse:
        system_instruction, contents = self._split_messages(messages)
        # The SDK call is blocking; run it off the event loop.
        text = await asyncio.to_thread(self._generate, system_instruction, contents)
        return LLMResponse(raw_text=text)
