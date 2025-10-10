"""Helpers for invoking OpenAI models from the toolkit domain."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx
import logfire

from app.settings import settings
from .models import SampleAIRequest, SampleAIResponse

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class _PresetConfig:
    """Internal mapping between presets and OpenAI request parameters."""

    model: str
    reasoning: dict[str, str] | None


class ToolkitAIService:
    """Wrapper around the OpenAI Responses API providing simple presets."""

    def __init__(self) -> None:
        self._enabled = bool(settings.openai_api_key)
        self._api_key = settings.openai_api_key
        self._base_url = "https://api.openai.com/v1"

    async def create_sample_response(self, request: SampleAIRequest) -> SampleAIResponse:
        """
        Generate a demo response from the configured OpenAI model (or a stub).

        Args:
            request: Normalized request parameters including preset.
        """
        preset_config = self._resolve_preset(request.preset)

        if not self._enabled or not self._api_key:
            logger.info(
                "Returning stubbed OpenAI response",
                extra={"preset": request.preset, "instructions": request.instructions},
            )
            return SampleAIResponse(
                preset=request.preset,
                model=preset_config.model,
                reasoning=preset_config.reasoning,
                instructions=request.instructions,
                input_text=request.input_text,
                output_text=self._build_stub_text(request),
                stubbed=True,
            )

        with logfire.span(
            "toolkit.ai.sample_response",
            preset=request.preset,
            model=preset_config.model,
            reasoning=preset_config.reasoning,
        ):
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": preset_config.model,
                "reasoning": preset_config.reasoning,
                "instructions": request.instructions,
                "input": request.input_text,
            }

            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.post(
                    f"{self._base_url}/responses",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        output_text = self._extract_output_text(data)

        return SampleAIResponse(
            preset=request.preset,
            model=preset_config.model,
            reasoning=preset_config.reasoning,
            instructions=request.instructions,
            input_text=request.input_text,
            output_text=output_text,
            stubbed=False,
        )

    @staticmethod
    def _build_stub_text(request: SampleAIRequest) -> str:
        """Return a lightweight message when OpenAI is not configured."""
        return (
            f"[stub:{request.preset}] Instructions '{request.instructions}' "
            f"applied to input '{request.input_text}'. Configure OPENAI_API_KEY to "
            "receive live responses."
        )

    @staticmethod
    def _resolve_preset(preset: str) -> _PresetConfig:
        """Translate preset identifiers into model + reasoning pairs."""
        presets: dict[str, _PresetConfig] = {
            "small": _PresetConfig(model="gpt-5-nano-2025-08-07", reasoning={"effort": "low"}),
            "large": _PresetConfig(model="gpt-5-2025-08-07", reasoning={"effort": "low"}),
            "reasoning": _PresetConfig(model="gpt-5-2025-08-07", reasoning={"effort": "high"}),
        }
        try:
            return presets[preset]
        except KeyError as exc:
            raise ValueError(f"Unsupported preset '{preset}'") from exc

    @staticmethod
    def _extract_output_text(response: dict[str, object]) -> str:
        """Extract a readable string from the OpenAI Responses API output."""
        if not isinstance(response, dict):
            return json.dumps(response, indent=2, default=str)

        output_text = response.get("output_text")
        if isinstance(output_text, list):
            combined = "\n".join(str(part) for part in output_text if part)
            if combined:
                return combined
        elif isinstance(output_text, str):
            return output_text

        output = response.get("output")
        if isinstance(output, list):
            chunks = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                        text_value = content.get("text")
                        if text_value:
                            chunks.append(str(text_value))
            if chunks:
                return "\n".join(chunks)

        return json.dumps(response, indent=2, default=str)
