"""LLM client adapters for LangChain-based integrations."""

from __future__ import annotations

from typing import Protocol

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


class LLMClient(Protocol):
    """Protocol for agent LLM clients."""

    async def ainvoke(self, prompt: str) -> str:
        """Return model output as plain text."""

    async def generate(self, prompt: str) -> str:
        """Compatibility alias for agents that call generate()."""


class GeminiClient:
    """LangChain adapter for Google Gemini models."""

    def __init__(self, model: str = "gemini-1.5-pro", temperature: float = 0.0):
        self.llm = ChatGoogleGenerativeAI(model=model, temperature=temperature)

    async def ainvoke(self, prompt: str) -> str:
        msg = await self.llm.ainvoke(prompt)
        return msg.content

    async def generate(self, prompt: str) -> str:
        return await self.ainvoke(prompt)


class ClaudeClient:
    """LangChain adapter for Anthropic Claude models."""

    def __init__(self, model: str = "claude-3-5-sonnet-20240620", temperature: float = 0.0):
        self.llm = ChatAnthropic(model=model, temperature=temperature)

    async def ainvoke(self, prompt: str) -> str:
        msg = await self.llm.ainvoke(prompt)
        return msg.content

    async def generate(self, prompt: str) -> str:
        return await self.ainvoke(prompt)


class DeepSeekClient:
    """LangChain adapter for DeepSeek OpenAI-compatible endpoints."""

    def __init__(
        self,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com/v1",
        api_key: str | None = None,
        temperature: float = 0.0,
    ):
        self.llm = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
        )

    async def ainvoke(self, prompt: str) -> str:
        msg = await self.llm.ainvoke(prompt)
        return msg.content

    async def generate(self, prompt: str) -> str:
        return await self.ainvoke(prompt)


class OpenAIClient:
    """LangChain adapter for OpenAI models."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
    ):
        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )

    async def ainvoke(self, prompt: str) -> str:
        msg = await self.llm.ainvoke(prompt)
        return msg.content

    async def generate(self, prompt: str) -> str:
        return await self.ainvoke(prompt)
