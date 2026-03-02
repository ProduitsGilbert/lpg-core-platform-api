"""Typed ElekNet integration errors mapped to API-friendly status codes."""

from __future__ import annotations

from fastapi import status

from app.errors import BaseAPIException


class ElekNetError(BaseAPIException):
    """Base exception for ElekNet integration failures."""

    def __init__(
        self,
        detail: str,
        *,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        error_code: str = "ELEKNET_ERROR",
    ):
        super().__init__(status_code=status_code, detail=detail, error_code=error_code)


class ElekNetConfigurationError(ElekNetError):
    """Raised when required ElekNet settings are missing."""

    def __init__(self, detail: str = "ElekNet configuration is incomplete"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ELEKNET_CONFIGURATION_ERROR",
        )


class ElekNetTimeoutError(ElekNetError):
    """Raised on ElekNet timeout failures."""

    def __init__(self, detail: str = "ElekNet request timed out"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_code="ELEKNET_TIMEOUT",
        )


class ElekNetGatewayError(ElekNetError):
    """Raised on non-timeout network failures."""

    def __init__(self, detail: str = "Failed to reach ElekNet service"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="ELEKNET_GATEWAY_ERROR",
        )


class ElekNetUnauthorizedError(ElekNetError):
    """Raised when ElekNet reports access denied."""

    def __init__(self, detail: str = "ElekNet access denied"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="ELEKNET_UNAUTHORIZED",
        )


class ElekNetUpstreamError(ElekNetError):
    """Raised when ElekNet returns an upstream business/processing error."""

    def __init__(self, detail: str = "ElekNet returned an error"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="ELEKNET_UPSTREAM_ERROR",
        )


class ElekNetInvalidResponseError(ElekNetError):
    """Raised when ElekNet returns malformed or unexpected XML."""

    def __init__(self, detail: str = "Invalid XML response from ElekNet"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="ELEKNET_INVALID_RESPONSE",
        )
