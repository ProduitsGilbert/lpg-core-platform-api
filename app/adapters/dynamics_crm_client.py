from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse

import httpx
import logfire

from app.errors import ExternalServiceException
from app.settings import settings


class CRMConfigurationError(ExternalServiceException):
    def __init__(self, detail: str = "Dynamics CRM configuration missing") -> None:
        super().__init__(detail=detail, service="dynamics365")
        self.status_code = 500
        self.error_code = "CRM_CONFIGURATION_ERROR"


class CRMClientError(ExternalServiceException):
    def __init__(self, detail: str, *, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(detail=detail, service="dynamics365")
        self.status_code = 502
        self.error_code = "CRM_CLIENT_ERROR"
        if context:
            self.context = context


class DynamicsCRMClient:
    """Client for Microsoft Dynamics 365 CRM Web API (Dataverse)."""

    def __init__(self) -> None:
        self._base_url = (settings.crm_web_api_endpoint or "").rstrip("/")
        self._tenant_id = (settings.crm_tenant_id or "").strip()
        self._client_id = (settings.crm_client_id or "").strip()
        self._client_secret = (settings.crm_client_secret or "").strip()

        if not self._base_url:
            raise CRMConfigurationError("CRM_WEB_API_ENDPOINT is required")
        if not self._tenant_id:
            raise CRMConfigurationError("CRM_TENANT_ID is required")
        if not self._client_id:
            raise CRMConfigurationError("CRM_CLIENT_ID is required")
        if not self._client_secret:
            raise CRMConfigurationError("CRM_CLIENT_SECRET is required")

        parsed = urlparse(self._base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise CRMConfigurationError("CRM_WEB_API_ENDPOINT must be a valid URL")

        self._resource = f"{parsed.scheme}://{parsed.netloc}"
        self._token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        self._http: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=float(settings.request_timeout))
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def _ensure_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._token and self._token_expires_at and now < self._token_expires_at:
            return self._token

        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "client_credentials",
            "scope": f"{self._resource}/.default",
        }

        try:
            response = await self._client.post(
                self._token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise CRMClientError(
                "Failed to authenticate with Microsoft identity platform",
                context={"status_code": exc.response.status_code if exc.response else None},
            ) from exc
        except httpx.RequestError as exc:
            raise CRMClientError("CRM authentication endpoint unreachable") from exc

        token = payload.get("access_token")
        if not token:
            raise CRMClientError("CRM authentication response did not include access_token")

        expires_in = int(payload.get("expires_in", 3600))
        # Refresh token one minute early.
        self._token = str(token)
        self._token_expires_at = now + timedelta(seconds=max(expires_in - 60, 60))
        return self._token

    async def get_collection(
        self,
        entity_set: str,
        *,
        select: Optional[List[str]] = None,
        filter_expr: Optional[str] = None,
        order_by: Optional[str] = None,
        top: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        token = await self._ensure_token()

        query_params: Dict[str, str] = {}
        if select:
            query_params["$select"] = ",".join(select)
        if filter_expr:
            query_params["$filter"] = filter_expr
        if order_by:
            query_params["$orderby"] = order_by
        if top:
            query_params["$top"] = str(top)

        path = f"{self._base_url}/{entity_set}"
        if query_params:
            encoded = urlencode(query_params, safe=",()$' ")
            path = f"{path}?{encoded}".replace("+", "%20")

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "OData-Version": "4.0",
            "OData-MaxVersion": "4.0",
            "Prefer": 'odata.include-annotations="*"',
        }

        rows: List[Dict[str, Any]] = []
        next_link: Optional[str] = path

        with logfire.span("dynamics_crm.get_collection", entity_set=entity_set):
            while next_link:
                try:
                    response = await self._client.get(next_link, headers=headers)
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPStatusError as exc:
                    response_text = ""
                    if exc.response is not None:
                        try:
                            response_text = (exc.response.text or "")[:1000]
                        except Exception:
                            response_text = ""
                    raise CRMClientError(
                        f"Dynamics CRM request failed for {entity_set}",
                        context={
                            "status_code": exc.response.status_code if exc.response else None,
                            "upstream_body": response_text,
                        },
                    ) from exc
                except httpx.RequestError as exc:
                    raise CRMClientError(f"Dynamics CRM service unreachable for {entity_set}") from exc

                batch = payload.get("value", [])
                if isinstance(batch, list):
                    rows.extend(batch)
                next_link = payload.get("@odata.nextLink") or payload.get("odata.nextLink")

        return rows
