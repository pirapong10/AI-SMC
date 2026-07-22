"""
LLM Provider Abstraction Layer
Allows swapping between AI providers (Gemini, OpenAI, Claude, etc.)
by changing only the .env config — no agent code changes needed.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    Agents interact ONLY through this interface.
    """

    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        """Send a prompt and return the raw text response."""
        pass

    def generate_json(self, prompt: str, temperature: float = 0.2) -> dict:
        """
        Send a prompt and parse the JSON response.
        Falls back to partial extraction on truncated responses.
        """
        raw = self.generate(prompt, temperature=temperature)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()

        # 1. Direct parse (best case)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 2. Extract full JSON object via regex
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # 3. Partial field extraction (handles truncated responses)
        result = {}
        for m in re.finditer(r'"(\w+)"\s*:\s*(true|false|null|"[^"]*"|[\d.]+)', raw):
            key, val = m.group(1), m.group(2)
            if val == "true":
                result[key] = True
            elif val == "false":
                result[key] = False
            elif val == "null":
                result[key] = None
            elif val.startswith('"'):
                result[key] = val.strip('"')
            else:
                try:
                    result[key] = float(val) if '.' in val else int(val)
                except ValueError:
                    result[key] = val

        if result:
            logger.info(f"📋 Partial JSON extracted: {list(result.keys())}")
            return result

        logger.warning(f"⚠️ JSON parse failed. Raw: {raw[:200]}")
        return {}

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass


# ─────────────────────────────────────────────────────────
# Gemini Provider
# ─────────────────────────────────────────────────────────

class GeminiProvider(LLMProvider):
    """Google Gemini provider (default)."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(
                model_name=model,
                system_instruction="You are an expert trading analyst. Always respond with valid JSON only."
            )
            self._model_name = model
            logger.info(f"✅ GeminiProvider initialized: {model}")
        except ImportError:
            raise ImportError("Run: pip install google-generativeai")

    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold

        safety = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        resp = self._model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=2048,
            ),
            safety_settings=safety
        )

        # Guard against empty/blocked candidates
        if not resp.candidates or not resp.candidates[0].content.parts:
            raise ValueError(f"Gemini returned empty response. Finish reason: {resp.candidates[0].finish_reason if resp.candidates else 'unknown'}")

        return resp.text

    @property
    def provider_name(self) -> str:
        return f"Gemini ({self._model_name})"


# ─────────────────────────────────────────────────────────
# OpenAI Provider
# ─────────────────────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            self._model_name = model
            logger.info(f"✅ OpenAIProvider initialized: {model}")
        except ImportError:
            raise ImportError("Run: pip install openai")

    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        resp = self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {"role": "system", "content": "You are an expert trading analyst. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=1024
        )
        return resp.choices[0].message.content

    @property
    def provider_name(self) -> str:
        return f"OpenAI ({self._model_name})"


# ─────────────────────────────────────────────────────────
# Claude (Anthropic) Provider
# ─────────────────────────────────────────────────────────

class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            self._model_name = model
            logger.info(f"✅ ClaudeProvider initialized: {model}")
        except ImportError:
            raise ImportError("Run: pip install anthropic")

    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        import anthropic
        msg = self._client.messages.create(
            model=self._model_name,
            max_tokens=1024,
            temperature=temperature,
            system="You are an expert trading analyst. Always respond with valid JSON only.",
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text

    @property
    def provider_name(self) -> str:
        return f"Claude ({self._model_name})"


# ─────────────────────────────────────────────────────────
# DeepSeek Provider
# ─────────────────────────────────────────────────────────

class DeepSeekProvider(LLMProvider):
    """DeepSeek provider via OpenAI-compatible API."""

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            self._model_name = model
            logger.info(f"✅ DeepSeekProvider initialized: {model}")
        except ImportError:
            raise ImportError("Run: pip install openai")

    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        resp = self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {"role": "system", "content": "You are an expert trading analyst. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=1024
        )
        return resp.choices[0].message.content

    @property
    def provider_name(self) -> str:
        return f"DeepSeek ({self._model_name})"


# ─────────────────────────────────────────────────────────
# Factory — create provider from environment config
# ─────────────────────────────────────────────────────────

def create_provider_from_env() -> LLMProvider:
    """
    Create an LLM provider based on LLM_PROVIDER env var.

    .env examples:
        LLM_PROVIDER=gemini    → uses GEMINI_API_KEY
        LLM_PROVIDER=openai    → uses OPENAI_API_KEY
        LLM_PROVIDER=claude    → uses ANTHROPIC_API_KEY
        LLM_PROVIDER=deepseek  → uses DEEPSEEK_API_KEY
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        key = os.getenv("GEMINI_API_KEY", "")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        return GeminiProvider(api_key=key, model=model)

    elif provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return OpenAIProvider(api_key=key, model=model)

    elif provider == "claude":
        key = os.getenv("ANTHROPIC_API_KEY", "")
        model = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022")
        return ClaudeProvider(api_key=key, model=model)

    elif provider == "deepseek":
        key = os.getenv("DEEPSEEK_API_KEY", "")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        return DeepSeekProvider(api_key=key, model=model)

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{provider}'. "
            f"Supported: gemini, openai, claude, deepseek"
        )


def create_provider(provider: str, **kwargs) -> LLMProvider:
    """Create a provider by name with explicit kwargs."""
    providers = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "deepseek": DeepSeekProvider,
    }
    cls = providers.get(provider.lower())
    if not cls:
        raise ValueError(f"Unknown provider: '{provider}'. Supported: {list(providers.keys())}")
    return cls(**kwargs)
