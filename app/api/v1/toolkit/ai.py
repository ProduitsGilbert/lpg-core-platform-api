"""AI endpoints offering typing suggestions and reasoning helpers."""

from __future__ import annotations

import logging

import httpx
import logfire
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from httpx import ResponseNotRead

from app.domain.toolkit.ai_service import AIService, OPENROUTER_MODEL_ORDER
from app.domain.toolkit.models import (
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

router = APIRouter(prefix="/ai", tags=["AI"])

ai_service = AIService()

ALLOWED_OPENROUTER_NAMES = [name for name, _ in OPENROUTER_MODEL_ORDER]


def _map_http_error(exc: httpx.HTTPStatusError, action: str) -> HTTPException:
    status_code = exc.response.status_code if exc.response else status.HTTP_502_BAD_GATEWAY
    detail = ""
    if exc.response:
        try:
            detail = exc.response.text
        except ResponseNotRead:
            detail = "<streaming response not consumed>"
    logger.error(
        "OpenAI request returned HTTP error",
        extra={"action": action, "status_code": status_code, "detail": detail[:500]},
    )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "error": {
                "code": "OPENAI_ERROR",
                "message": f"OpenAI upstream call failed while attempting to {action}",
                "upstream_status": status_code,
            }
        },
    )


def _map_request_error(exc: httpx.RequestError, action: str) -> HTTPException:
    logger.error(
        "OpenAI request failed",
        extra={"action": action, "error": str(exc)},
    )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "error": {
                "code": "OPENAI_ERROR",
                "message": f"OpenAI upstream call failed while attempting to {action}",
            }
        },
    )


def _extract_error_message(exc: HTTPException) -> str:
    """Extract a human-readable error message from an HTTPException."""
    detail = exc.detail
    if isinstance(detail, dict):
        error = detail.get("error") or {}
        message = error.get("message")
        if message:
            return str(message)
    return str(detail)


@router.post(
    "/typing-suggestions",
    response_model=TypingSuggestionResponse,
    responses={
        status.HTTP_200_OK: {"description": "Typing suggestion generated successfully"},
        status.HTTP_502_BAD_GATEWAY: {"description": "OpenAI upstream failure"},
    },
    summary="Generate typing suggestion",
    description=(
        "Use the ultra-low-latency `gpt-5-nano-2025-08-07` model to produce autocomplete-style "
        "suggestions for the provided prefix/suffix context."
    ),
)
async def create_typing_suggestion(
    request: TypingSuggestionRequest,
) -> TypingSuggestionResponse:
    """Return a fast typing suggestion."""
    try:
        return await ai_service.generate_typing_suggestion(request)
    except httpx.HTTPStatusError as exc:
        raise _map_http_error(exc, "generate a typing suggestion") from exc
    except httpx.RequestError as exc:
        raise _map_request_error(exc, "generate a typing suggestion") from exc


@router.post(
    "/deep-reasoning",
    response_model=DeepReasoningResponse,
    responses={
        status.HTTP_200_OK: {"description": "Reasoned answer generated successfully"},
        status.HTTP_502_BAD_GATEWAY: {"description": "OpenAI upstream failure"},
    },
    summary="Solve complex problems",
    description=(
        "Use the `gpt-5-2025-08-07` model with high reasoning effort to tackle complex questions. "
        "This endpoint is optimized for thoughtful, multi-step answers."
    ),
)
async def create_deep_reasoning_response(
    request: DeepReasoningRequest,
) -> DeepReasoningResponse:
    """Return a structured answer for complex prompts."""
    try:
        return await ai_service.solve_complex_problem(request)
    except httpx.HTTPStatusError as exc:
        raise _map_http_error(exc, "solve a complex problem") from exc
    except httpx.RequestError as exc:
        raise _map_request_error(exc, "solve a complex problem") from exc


@router.post(
    "/standard-response",
    response_model=StandardAIResponse,
    responses={
        status.HTTP_200_OK: {"description": "Assistant response generated successfully"},
        status.HTTP_502_BAD_GATEWAY: {"description": "OpenAI upstream failure"},
    },
    summary="Generate standard assistant response",
    description=(
        "Use the balanced `gpt-5-mini-2025-08-07` model for everyday assistant use cases."
    ),
)
async def create_standard_response(
    request: StandardAIRequest,
) -> StandardAIResponse:
    """Return a standard assistant-style response."""
    try:
        return await ai_service.generate_standard_response(request)
    except httpx.HTTPStatusError as exc:
        raise _map_http_error(exc, "generate a standard response") from exc
    except httpx.RequestError as exc:
        raise _map_request_error(exc, "generate a standard response") from exc


@router.post(
    "/streaming-response",
    responses={
        status.HTTP_200_OK: {"description": "Streaming response initiated successfully"},
        status.HTTP_502_BAD_GATEWAY: {"description": "OpenAI upstream failure"},
    },
    summary="Stream assistant response",
    description="Stream tokens from the `gpt-5-mini-2025-08-07` model as they are generated.",
)
async def stream_standard_response(
    request: StreamingAIRequest,
) -> StreamingResponse:
    """Stream a standard assistant response using server-sent events."""

    async def event_generator():
        try:
            async for chunk in ai_service.stream_standard_response(request):
                yield f"data: {chunk}\n\n"
        except httpx.HTTPStatusError as exc:
            error = _map_http_error(exc, "stream a response")
            yield f"data: [ERROR] {_extract_error_message(error)}\n\n"
        except httpx.RequestError as exc:
            error = _map_request_error(exc, "stream a response")
            yield f"data: [ERROR] {_extract_error_message(error)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post(
    "/openrouter-response",
    response_model=OpenRouterResponse,
    responses={
        status.HTTP_200_OK: {"description": "OpenRouter response generated successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Unsupported model selection"},
        status.HTTP_502_BAD_GATEWAY: {"description": "OpenRouter upstream failure"},
    },
    summary="Generate response via OpenRouter",
    description=(
        "Invoke OpenRouter using a prioritized list of leaderboard models. "
        "Allowed models: "
        + ", ".join(ALLOWED_OPENROUTER_NAMES)
        + "."
    ),
)
async def create_openrouter_response(
    request: OpenRouterRequest,
) -> OpenRouterResponse:
    """Return a response generated via OpenRouter."""
    try:
        return await ai_service.generate_openrouter_response(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_MODEL",
                    "message": str(exc),
                }
            },
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise _map_http_error(exc, "generate an OpenRouter response") from exc
    except httpx.RequestError as exc:
        raise _map_request_error(exc, "generate an OpenRouter response") from exc


@router.post(
    "/sample-response",
    response_model=SampleAIResponse,
    responses={
        status.HTTP_200_OK: {"description": "Generated sample response successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid preset supplied"},
        status.HTTP_502_BAD_GATEWAY: {"description": "OpenAI upstream failure"},
    },
    summary="Generate sample OpenAI response",
    description=(
        "Trigger a sample OpenAI Responses API call using predefined presets for nano, large, "
        "and reasoning-heavy models."
    ),
)
async def create_sample_ai_response(request: SampleAIRequest) -> SampleAIResponse:
    """Return a sample OpenAI response using the desired preset."""
    try:
        with logfire.span("ai.sample_response_endpoint", preset=request.preset):
            return await ai_service.create_sample_response(request)
    except ValueError as exc:
        logger.warning("Unsupported AI preset requested", extra={"preset": request.preset})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_PRESET",
                    "message": str(exc),
                }
            },
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise _map_http_error(exc, "generate a sample response") from exc
    except httpx.RequestError as exc:
        raise _map_request_error(exc, "generate a sample response") from exc
