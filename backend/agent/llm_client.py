"""
Filing Sleuth — Unified LLM Client

Thin, robust wrapper around Anthropic Claude and OpenAI APIs with:
- Structured JSON output validation (via Pydantic)
- Automatic fallback when API keys are not configured (mock/heuristic mode)
- Token usage and latency tracking
- Temperature 0.0 for deterministic financial extraction
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from backend.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Unified LLM client supporting Anthropic, OpenAI, and heuristic mock mode."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.anthropic_client = None
        self.openai_client = None

        if self.settings.anthropic_api_key:
            try:
                import anthropic
                self.anthropic_client = anthropic.AsyncAnthropic(
                    api_key=self.settings.anthropic_api_key,
                )
                logger.info("Initialized Anthropic client with model %s", self.settings.anthropic_model)
            except Exception as e:
                logger.warning("Failed to initialize Anthropic client: %s", e)

        if self.settings.openai_api_key:
            try:
                import openai
                self.openai_client = openai.AsyncOpenAI(
                    api_key=self.settings.openai_api_key,
                )
                logger.info("Initialized OpenAI client with model %s", self.settings.openai_model)
            except Exception as e:
                logger.warning("Failed to initialize OpenAI client: %s", e)

        # Track token usage across sessions
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    @property
    def has_active_provider(self) -> bool:
        return self.anthropic_client is not None or self.openai_client is not None

    async def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        response_model: type[T] | None = None,
        temperature: float = 0.0,
    ) -> str | T:
        """Generate a response, optionally parsed into a Pydantic model.

        Args:
            prompt: User message prompt.
            system: System instructions.
            response_model: Optional Pydantic model class for structured JSON output.
            temperature: Sampling temperature (default 0.0 for deterministic output).

        Returns:
            String response if response_model is None, else an instance of response_model.
        """
        # If no active provider, use mock/fallback generator
        if not self.has_active_provider:
            logger.debug("No LLM API keys configured. Using fallback generator.")
            return self._generate_fallback(prompt, system, response_model)

        # 1. Prefer Anthropic if available
        if self.anthropic_client is not None:
            return await self._generate_anthropic(
                prompt=prompt,
                system=system,
                response_model=response_model,
                temperature=temperature,
            )

        # 2. Use OpenAI if available
        if self.openai_client is not None:
            return await self._generate_openai(
                prompt=prompt,
                system=system,
                response_model=response_model,
                temperature=temperature,
            )

        return self._generate_fallback(prompt, system, response_model)

    async def _generate_anthropic(
        self,
        prompt: str,
        system: str,
        response_model: type[T] | None,
        temperature: float,
    ) -> str | T:
        """Call Anthropic Claude API."""
        if response_model is not None:
            schema_json = json.dumps(response_model.model_json_schema(), indent=2)
            augmented_system = (
                f"{system}\n\n"
                f"You MUST respond ONLY with valid JSON conforming to this JSON schema:\n"
                f"{schema_json}\n"
                f"Do not include any markdown formatting around the JSON (e.g. no ```json ``` fences)."
            )
        else:
            augmented_system = system

        response = await self.anthropic_client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=4096,
            temperature=temperature,
            system=augmented_system,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text if response.content else ""
        if response.usage:
            self.total_prompt_tokens += response.usage.input_tokens
            self.total_completion_tokens += response.usage.output_tokens

        if response_model is not None:
            return self._parse_json_to_model(content, response_model)
        return content

    async def _generate_openai(
        self,
        prompt: str,
        system: str,
        response_model: type[T] | None,
        temperature: float,
    ) -> str | T:
        """Call OpenAI API."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        if response_model is not None:
            completion = await self.openai_client.beta.chat.completions.parse(
                model=self.settings.openai_model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
            )
            if completion.usage:
                self.total_prompt_tokens += completion.usage.prompt_tokens
                self.total_completion_tokens += completion.usage.completion_tokens
            return completion.choices[0].message.parsed
        else:
            completion = await self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                temperature=temperature,
            )
            if completion.usage:
                self.total_prompt_tokens += completion.usage.prompt_tokens
                self.total_completion_tokens += completion.usage.completion_tokens
            return completion.choices[0].message.content or ""

    def _parse_json_to_model(self, raw: str, model_cls: type[T]) -> T:
        """Extract and parse JSON from LLM text output into Pydantic model."""
        cleaned = raw.strip()
        # Remove markdown code fences if present
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Find first '{' and last '}'
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]

        return model_cls.model_validate_json(cleaned)

    def _generate_fallback(
        self,
        prompt: str,
        system: str,
        response_model: type[T] | None,
    ) -> str | T:
        """Deterministic fallback when no LLM API key is present."""
        if response_model is None:
            return "Fallback response: No LLM provider configured."

        # Let the model instantiate with default values or dummy schema
        try:
            return response_model()
        except Exception:
            # Try to build minimal mock dict from model fields
            mock_data = {}
            for field_name, field_info in response_model.model_fields.items():
                annotation = field_info.annotation
                if annotation == str:
                    mock_data[field_name] = "Not provided"
                elif annotation == int:
                    mock_data[field_name] = 0
                elif annotation == float:
                    mock_data[field_name] = 0.0
                elif annotation == bool:
                    mock_data[field_name] = False
                elif getattr(annotation, "__origin__", None) is list:
                    mock_data[field_name] = []
                elif getattr(annotation, "__origin__", None) is dict:
                    mock_data[field_name] = {}
                else:
                    mock_data[field_name] = None
            return response_model.model_validate(mock_data)
