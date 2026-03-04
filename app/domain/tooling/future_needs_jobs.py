from __future__ import annotations

import asyncio
import logging

from app.domain.tooling.future_needs_cache import tooling_future_needs_cache
from app.domain.tooling.future_needs_service import FutureToolingNeedService
from app.settings import settings

logger = logging.getLogger(__name__)


def _parse_default_work_centers(value: str | None) -> list[str]:
    if not value:
        return []
    return [token.strip() for token in value.split(",") if token.strip()]


async def refresh_tooling_future_needs_cache() -> None:
    """Daily refresh for registered tooling future-needs work centers."""
    service = FutureToolingNeedService()
    registered = tooling_future_needs_cache.list_registered_work_centers()
    defaults = _parse_default_work_centers(settings.tooling_future_needs_default_work_centers)
    work_centers = sorted(set(registered) | set(defaults))
    if not work_centers:
        return

    semaphore = asyncio.Semaphore(4)

    async def _refresh_one(work_center_no: str) -> None:
        async with semaphore:
            try:
                await service.get_future_needs(work_center_no=work_center_no, refresh=True)
            except Exception as exc:
                logger.warning(
                    "Failed to refresh tooling future-needs cache",
                    extra={"work_center_no": work_center_no, "error": str(exc)},
                )

    await asyncio.gather(*[_refresh_one(work_center_no) for work_center_no in work_centers])
