"""Thin Claude wrapper: structured output via tool-forcing, retries with
backoff, and token/cost accounting. One place owns every model call so the
tracer can see them all."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from pydantic import BaseModel

# Claude 4.x pricing (USD per token) — Sonnet 4.6 defaults; override as needed.
_PRICE = {"in": 3.0 / 1_000_000, "out": 15.0 / 1_000_000}

DEFAULT_MODEL = "claude-sonnet-4-6"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost(self) -> float:
        return self.input_tokens * _PRICE["in"] + self.output_tokens * _PRICE["out"]

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens


@dataclass
class LLM:
    """Wraps the Anthropic async client. Lazily imported so the report
    generator and tests run without the SDK installed."""

    model: str = DEFAULT_MODEL
    max_retries: int = 3
    usage: Usage = field(default_factory=Usage)
    _client: object | None = None

    def _ensure(self):
        if self._client is None:
            from anthropic import AsyncAnthropic  # lazy

            self._client = AsyncAnthropic()
        return self._client

    async def structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        max_tokens: int = 1500,
    ) -> BaseModel:
        """Force the model to return an instance of `schema` via tool-use."""
        client = self._ensure()
        tool = {
            "name": schema.__name__,
            "description": (schema.__doc__ or schema.__name__).strip(),
            "input_schema": schema.model_json_schema(),
        }
        last: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                msg = await client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system or "You are a precise research agent. Be faithful to sources.",
                    tools=[tool],
                    tool_choice={"type": "tool", "name": schema.__name__},
                    messages=[{"role": "user", "content": prompt}],
                )
                self.usage.add(
                    Usage(msg.usage.input_tokens, msg.usage.output_tokens)
                )
                block = next(b for b in msg.content if b.type == "tool_use")
                return schema.model_validate(block.input)
            except Exception as e:  # noqa: BLE001 — retry on transient failures
                last = e
                await asyncio.sleep(0.5 * (2**attempt))
        raise RuntimeError(f"LLM call failed after {self.max_retries} tries: {last}")
