"""Helpers for invoking OpenAI models from the toolkit domain."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import httpx
import logfire

from app.settings import settings
from .models import (
    DeepReasoningRequest,
    DeepReasoningResponse,
    SampleAIRequest,
    SampleAIResponse,
    StandardAIRequest,
    StandardAIResponse,
    StreamingAIRequest,
    TypingSuggestionRequest,
    TypingSuggestionResponse,
    OpenRouterRequest,
    OpenRouterResponse,
)

logger = logging.getLogger(__name__)

OPENROUTER_MODEL_ORDER: List[Tuple[str, str]] = [
    ("Grok Code Fast 1", "x-ai/grok-code-fast-1"),
    ("Claude Sonnet 4.5", "anthropic/claude-sonnet-4.5"),
    ("Gemini 2.5 Flash", "google/gemini-2.5-flash"),
    ("MiniMax M2 (free)", "minimax/minimax-m2:free"),
    ("Gemini 2.5 Pro", "google/gemini-2.5-pro"),
    ("Grok 4 Fast", "x-ai/grok-4-fast"),
    ("Gemini 2.0 Flash", "google/gemini-2.0-flash-001"),
    ("Claude Sonnet 4", "anthropic/claude-sonnet-4"),
    ("Gemini 2.5 Flash Lite", "google/gemini-2.5-flash-lite"),
]

OPENROUTER_MODEL_LOOKUP: Dict[str, Tuple[str, str]] = {}
for display_name, slug in OPENROUTER_MODEL_ORDER:
    OPENROUTER_MODEL_LOOKUP[display_name.lower()] = (display_name, slug)
    OPENROUTER_MODEL_LOOKUP[slug.lower()] = (display_name, slug)

MODELS_WITHOUT_TEMPERATURE: Tuple[str, ...] = (
    "gpt-5-nano-2025-08-07",
    "gpt-5-mini-2025-08-07",
)

@dataclass(slots=True, frozen=True)
class _PresetConfig:
    """Internal mapping between presets and OpenAI request parameters."""

    model: str
    reasoning: dict[str, str] | None


class AIService:
    """Wrapper around the OpenAI Responses API providing curated presets."""

    def __init__(self) -> None:
        self._enabled = bool(settings.openai_api_key)
        self._api_key = settings.openai_api_key
        self._base_url = "https://api.openai.com/v1"
        self._openrouter_key = settings.openrouter_api_key
        self._openrouter_enabled = bool(self._openrouter_key)
        self._openrouter_base_url = "https://openrouter.ai/api/v1"

    async def generate_typing_suggestion(
        self, request: TypingSuggestionRequest
    ) -> TypingSuggestionResponse:
        """
        Produce a fast autocomplete-style suggestion.

        Uses the ultra-low-latency nano model for quick feedback.
        """
        model = "gpt-5-nano-2025-08-07"
        instructions = request.instructions or (
            "You are an expert pair programmer. Suggest the next few tokens that seamlessly "
            "continue the user's work. Keep the suggestion concise and avoid repeating the "
            "existing suffix."
        )
        prompt = self._compose_typing_prompt(request)

        if not self._enabled or not self._api_key:
            return TypingSuggestionResponse(
                model=model,
                suggestion=self._build_typing_stub(request),
                stubbed=True,
            )

        suggestion = await self._request_openai(
            span_name="ai.typing_suggestion",
            model=model,
            instructions=instructions,
            input_text=prompt,
            temperature=request.temperature,
            span_attributes={
                "language": request.language,
                "prefix_chars": len(request.prefix),
                "suffix_chars": len(request.suffix),
            },
        )

        return TypingSuggestionResponse(
            model=model,
            suggestion=suggestion.strip(),
            stubbed=False,
        )

    async def solve_complex_problem(
        self, request: DeepReasoningRequest
    ) -> DeepReasoningResponse:
        """
        Handle complex problem-solving with high reasoning effort.
        """
        model = "gpt-5-2025-08-07"
        default_instructions = (
            "You are an expert problem solver. Provide a thorough, step-by-step answer. "
            "Show your reasoning clearly before summarizing the final response."
        )

        prompt = self._compose_reasoning_prompt(request)

        if not self._enabled or not self._api_key:
            return DeepReasoningResponse(
                model=model,
                answer=self._build_reasoning_stub(request),
                stubbed=True,
            )

        answer = await self._request_openai(
            span_name="ai.deep_reasoning",
            model=model,
            instructions=default_instructions,
            input_text=prompt,
            reasoning={"effort": "high"},
            span_attributes={"has_context": bool(request.context)},
        )

        return DeepReasoningResponse(
            model=model,
            answer=answer.strip(),
            stubbed=False,
        )

    async def generate_standard_response(
        self, request: StandardAIRequest
    ) -> StandardAIResponse:
        """
        Provide a standard assistant-style reply.
        """
        model = "gpt-5-mini-2025-08-07"
        instructions = request.instructions or (
            "You are a helpful assistant. Provide a clear, direct answer."
        )

        if not self._enabled or not self._api_key:
            return StandardAIResponse(
                model=model,
                output=self._build_standard_stub(request),
                stubbed=True,
            )

        output = await self._request_openai(
            span_name="ai.standard_response",
            model=model,
            instructions=instructions,
            input_text=request.prompt,
            temperature=request.temperature,
        )

        return StandardAIResponse(
            model=model,
            output=output.strip(),
            stubbed=False,
        )

    async def stream_standard_response(
        self, request: StreamingAIRequest
    ) -> AsyncGenerator[str, None]:
        """
        Stream a standard assistant-style reply chunk-by-chunk.
        """
        model = "gpt-5-mini-2025-08-07"
        instructions = request.instructions or (
            "You are a helpful assistant. Stream your answer as it is generated."
        )

        if not self._enabled or not self._api_key:
            yield self._build_streaming_stub(request)
            return

        async for chunk in self._request_openai_stream(
            span_name="ai.streaming_response",
            model=model,
            instructions=instructions,
            input_text=request.prompt,
            temperature=request.temperature,
        ):
            yield chunk

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

        output_text = await self._request_openai(
            span_name="ai.sample_response",
            model=preset_config.model,
            instructions=request.instructions,
            input_text=request.input_text,
            reasoning=preset_config.reasoning,
            span_attributes={"preset": request.preset},
        )

        return SampleAIResponse(
            preset=request.preset,
            model=preset_config.model,
            reasoning=preset_config.reasoning,
            instructions=request.instructions,
            input_text=request.input_text,
            output_text=output_text,
            stubbed=False,
        )

    async def generate_openrouter_response(
        self, request: OpenRouterRequest
    ) -> OpenRouterResponse:
        """
        Invoke OpenRouter with the allowed leaderboard models.
        """
        slugs, display_names = self._resolve_openrouter_models(request.models)
        default_instructions = request.instructions or "You are a helpful assistant."

        if not self._openrouter_enabled or not self._openrouter_key:
            return OpenRouterResponse(
                requested_models=display_names,
                selected_model=display_names[0] if display_names else None,
                output=self._build_openrouter_stub(request, display_names),
                stubbed=True,
            )

        headers = {
            "Authorization": f"Bearer {self._openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lpg-core-platform.local",
            "X-Title": settings.app_name,
        }

        messages = []
        if default_instructions:
            messages.append({"role": "system", "content": default_instructions})
        messages.append({"role": "user", "content": request.prompt})

        primary_model = slugs[0] if slugs else "openrouter/auto"
        payload: dict[str, object] = {
            "model": primary_model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if len(slugs) > 1:
            payload["models"] = slugs

        with logfire.span(
            "ai.openrouter_response",
            models=slugs,
            temperature=request.temperature,
        ):
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.post(
                    f"{self._openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        output = self._extract_openrouter_text(data).strip()
        selected_model = None
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            selected_model = choices[0].get("model")
        if not selected_model:
            selected_model = data.get("model")

        return OpenRouterResponse(
            requested_models=display_names,
            selected_model=selected_model,
            output=output,
            stubbed=False,
        )

    def _resolve_openrouter_models(
        self, models: Optional[List[str]]
    ) -> Tuple[List[str], List[str]]:
        """Validate and resolve requested OpenRouter models."""
        if models:
            resolved_slugs: List[str] = []
            display_names: List[str] = []
            seen = set()
            for name in models:
                key = (name or "").strip().lower()
                match = OPENROUTER_MODEL_LOOKUP.get(key)
                if not match:
                    raise ValueError(
                        f"Unsupported OpenRouter model '{name}'. "
                        "Refer to the documented leaderboard model list."
                    )
                display, slug = match
                if slug in seen:
                    continue
                seen.add(slug)
                display_names.append(display)
                resolved_slugs.append(slug)
            return resolved_slugs, display_names

        # Default ordering from the leaderboard list
        display_names = [display for display, _ in OPENROUTER_MODEL_ORDER]
        slugs = [slug for _, slug in OPENROUTER_MODEL_ORDER]
        return slugs, display_names

    async def _request_openai(
        self,
        *,
        span_name: str,
        model: str,
        instructions: str | None,
        input_text: str,
        reasoning: dict[str, str] | None = None,
        temperature: float | None = None,
        extra_payload: dict[str, object] | None = None,
        span_attributes: dict[str, object] | None = None,
    ) -> str:
        """Send a request to the OpenAI Responses API and return the output text."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, object] = {
            "model": model,
            "input": input_text,
        }
        if instructions:
            payload["instructions"] = instructions
        if reasoning:
            payload["reasoning"] = reasoning
        if temperature is not None and model not in MODELS_WITHOUT_TEMPERATURE:
            payload["temperature"] = temperature
        if extra_payload:
            payload.update(extra_payload)

        span_kwargs = span_attributes.copy() if span_attributes else {}
        span_kwargs.setdefault("model", model)

        with logfire.span(span_name, **span_kwargs):
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.post(
                    f"{self._base_url}/responses",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        return self._extract_output_text(data)

    async def _request_openai_stream(
        self,
        *,
        span_name: str,
        model: str,
        instructions: Optional[str],
        input_text: str,
        reasoning: Optional[dict[str, str]] = None,
        temperature: Optional[float] = None,
        extra_payload: Optional[dict[str, object]] = None,
        span_attributes: Optional[dict[str, object]] = None,
    ) -> AsyncGenerator[str, None]:
        """Send a streaming request to the OpenAI Responses API."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, object] = {
            "model": model,
            "input": input_text,
            "stream": True,
        }
        if instructions:
            payload["instructions"] = instructions
        if reasoning:
            payload["reasoning"] = reasoning
        if temperature is not None and model not in MODELS_WITHOUT_TEMPERATURE:
            payload["temperature"] = temperature
        if extra_payload:
            payload.update(extra_payload)

        span_kwargs = span_attributes.copy() if span_attributes else {}
        span_kwargs.setdefault("model", model)

        with logfire.span(span_name, **span_kwargs):
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/responses",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith(":"):
                            # Comments in SSE stream
                            continue
                        if line.startswith("data:"):
                            data_str = line.removeprefix("data:").strip()
                            if not data_str or data_str == "[DONE]":
                                if data_str == "[DONE]":
                                    break
                                continue
                            try:
                                event = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                            chunk = self._extract_stream_chunk(event)
                            if chunk:
                                yield chunk

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
    def _compose_typing_prompt(request: TypingSuggestionRequest) -> str:
        """Create a compact prompt describing the current editor state."""
        language_line = f"Language: {request.language}" if request.language else "Language: unspecified"
        return (
            f"{language_line}\n"
            "The user is editing a document. Continue from the prefix without duplicating the suffix.\n"
            "---\n"
            f"Prefix:\n{request.prefix}\n"
            "---\n"
            f"Suffix:\n{request.suffix or '[empty]'}\n"
            "---\n"
            "Suggestion:"
        )

    @staticmethod
    def _build_typing_stub(request: TypingSuggestionRequest) -> str:
        """Return a deterministic stub suggestion."""
        language_hint = (request.language or "text").lower()
        return f"[stub suggestion for {language_hint}]"

    @staticmethod
    def _compose_reasoning_prompt(request: DeepReasoningRequest) -> str:
        """Compose a prompt for complex reasoning tasks."""
        sections = [f"Question:\n{request.question}"]
        if request.context:
            sections.append(f"Context:\n{request.context}")
        if request.expected_format:
            sections.append(f"Desired output format:\n{request.expected_format}")
        sections.append("Provide a detailed, structured answer.")
        return "\n\n".join(sections)

    @staticmethod
    def _build_reasoning_stub(request: DeepReasoningRequest) -> str:
        """Return a deterministic stub reasoning answer."""
        summary = request.question[:120]
        return (
            f"[stub answer] Provide structured reasoning for: '{summary}'..."
            " Configure OPENAI_API_KEY for live responses."
        )

    @staticmethod
    def _build_standard_stub(request: StandardAIRequest) -> str:
        """Return a deterministic stub standard reply."""
        prompt_excerpt = request.prompt[:120]
        return (
            f"[stub response] '{prompt_excerpt}' "
            "Configure OPENAI_API_KEY to receive real completions."
        )

    @staticmethod
    def _build_streaming_stub(request: StreamingAIRequest) -> str:
        """Return a deterministic stub for streaming responses."""
        prompt_excerpt = request.prompt[:120]
        return (
            f"[stub stream] '{prompt_excerpt}' "
            "Configure OPENAI_API_KEY to enable streaming responses."
        )

    @staticmethod
    def _build_openrouter_stub(
        request: OpenRouterRequest, display_names: List[str]
    ) -> str:
        """Return a deterministic stub when OpenRouter integration is disabled."""
        models_str = ", ".join(display_names)
        prompt_excerpt = request.prompt[:120]
        return (
            f"[stub openrouter] Requested models: {models_str}. Prompt: '{prompt_excerpt}'. "
            "Configure OPENROUTER_API_KEY for live responses."
        )

    @staticmethod
    def _extract_stream_chunk(event: dict[str, object]) -> str:
        """Extract incremental text from a streaming SSE event."""
        chunks: List[str] = []

        output = event.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []):
                    if not isinstance(content, dict):
                        continue
                    delta = content.get("delta")
                    if isinstance(delta, dict):
                        text = delta.get("text")
                        if text:
                            chunks.append(str(text))
                    elif isinstance(delta, str):
                        chunks.append(delta)
                    else:
                        text = content.get("text")
                        if text:
                            chunks.append(str(text))

        if not chunks:
            output_text = event.get("output_text")
            if isinstance(output_text, str):
                chunks.append(output_text)

        if not chunks:
            delta = event.get("delta")
            if isinstance(delta, str):
                chunks.append(delta)
            elif isinstance(delta, dict):
                text = delta.get("text")
                if isinstance(text, str):
                    chunks.append(text)

        if not chunks:
            part = event.get("part")
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)

        return "".join(chunks)

    @staticmethod
    def _extract_openrouter_text(response: dict[str, object]) -> str:
        """Extract text content from an OpenRouter chat completion response."""
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: List[str] = []
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text")
                        if text:
                            parts.append(str(text))
                if parts:
                    return "".join(parts)
            if "text" in message and isinstance(message["text"], str):
                return message["text"]
        return json.dumps(response, indent=2, default=str)

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


# Backwards compatibility export for legacy imports
ToolkitAIService = AIService
