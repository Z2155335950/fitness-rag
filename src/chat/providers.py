from __future__ import annotations

import os
import threading
from abc import ABC, abstractmethod

from openai import OpenAI


class ModelCallError(RuntimeError):
    pass


class ChatModel(ABC):
    @property
    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> str:
        raise NotImplementedError


class UnavailableChatModel(ChatModel):
    @property
    def available(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return "local"

    def complete(self, messages: list[dict[str, str]]) -> str:
        raise ModelCallError("未配置对话模型")


class OpenAICompatibleChatModel(ChatModel):
    """Works with OpenAI and other Chat Completions compatible providers."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 45.0,
        thinking: str | None = None,
    ):
        self._model = model
        self._usage_local = threading.local()
        self._temperature = float(
            os.getenv("LLM_TEMPERATURE", "0.45")
        )
        normalized_thinking = (thinking or "").strip().lower()
        self._thinking = (
            normalized_thinking
            if normalized_thinking in {"enabled", "disabled"}
            else None
        )
        kwargs = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

    @property
    def available(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return self._model

    @property
    def last_usage(self) -> dict[str, int]:
        return getattr(self._usage_local, "value", {})

    def complete(self, messages: list[dict[str, str]]) -> str:
        self._usage_local.value = {}
        try:
            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": self._temperature,
                "max_tokens": 1000,
            }
            if self._thinking:
                kwargs["extra_body"] = {
                    "thinking": {"type": self._thinking}
                }
            response = self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            usage = getattr(response, "usage", None)
            if usage is not None:
                self._usage_local.value = {
                    "input_tokens": int(
                        getattr(usage, "prompt_tokens", 0) or 0
                    ),
                    "output_tokens": int(
                        getattr(usage, "completion_tokens", 0) or 0
                    ),
                }
            if not content:
                raise ModelCallError("模型返回了空内容")
            return content.strip()
        except Exception as exc:
            raise ModelCallError(str(exc)) from exc


def create_chat_model() -> ChatModel:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    api_key = (
        os.getenv("LLM_API_KEY")
        or deepseek_key
        or os.getenv("OPENAI_API_KEY")
    )
    if not api_key:
        return UnavailableChatModel()
    is_deepseek = provider == "deepseek" or (
        deepseek_key and not os.getenv("LLM_API_KEY")
    )
    model = os.getenv(
        "LLM_MODEL",
        "deepseek-flash" if is_deepseek else "gpt-4.1-mini",
    )
    base_url = (
        os.getenv("LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or (
            "https://api.deepseek.com"
            if is_deepseek
            else None
        )
    )
    timeout = float(os.getenv("LLM_TIMEOUT", "45"))
    thinking = None
    if is_deepseek:
        setting = os.getenv("LLM_THINKING", "enabled").strip().lower()
        thinking = (
            setting if setting in {"enabled", "disabled"} else "enabled"
        )
    return OpenAICompatibleChatModel(
        api_key=api_key,
        model=model,
        base_url=base_url or None,
        timeout=timeout,
        thinking=thinking,
    )
