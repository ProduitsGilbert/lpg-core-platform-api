"""Toolkit endpoints that showcase OpenAI integration presets."""

from __future__ import annotations

import logging

import httpx
import logfire
from fastapi import APIRouter, HTTPException, status

from app.domain.toolkit.ai_service import ToolkitAIService
from app.domain.toolkit.models import SampleAIRequest, SampleAIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["Toolkit - AI Samples"])

ai_service = ToolkitAIService()


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
        with logfire.span("toolkit.ai.sample_response_endpoint", preset=request.preset):
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
        status_code = exc.response.status_code if exc.response else status.HTTP_502_BAD_GATEWAY
        logger.error(
            "OpenAI request returned HTTP error",
            extra={"error": str(exc), "preset": request.preset, "status_code": status_code},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "OPENAI_ERROR",
                    "message": "OpenAI upstream call failed",
                    "upstream_status": status_code,
                }
            },
        ) from exc
    except httpx.RequestError as exc:
        logger.error("OpenAI request failed", extra={"error": str(exc), "preset": request.preset})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "OPENAI_ERROR",
                    "message": "OpenAI upstream call failed",
                }
            },
        ) from exc
