from __future__ import annotations

import asyncio
import logging

from app.domain.tooling.usage_history_cache import tooling_usage_history_cache
from app.domain.tooling.usage_history_service import ToolingUsageHistoryService
from app.settings import settings

logger = logging.getLogger(__name__)


def _parse_default_work_centers(value: str | None) -> list[str]:
    if not value:
        return []
    return [token.strip() for token in value.split(",") if token.strip()]


def _parse_default_machine_centers(value: str | None) -> list[str]:
    if not value:
        return []
    return [token.strip() for token in value.split(",") if token.strip()]


async def refresh_tooling_usage_history_cache() -> None:
    """Daily refresh for tooling usage-history snapshots."""
    service = ToolingUsageHistoryService()
    pairs = set(tooling_usage_history_cache.list_registered_pairs())
    default_work_centers = _parse_default_work_centers(settings.tooling_usage_history_default_work_centers)
    default_machine_centers = _parse_default_machine_centers(settings.tooling_usage_history_default_machine_centers)
    if not default_machine_centers:
        default_machine_centers = ["DMC100"]

    for work_center_no in default_work_centers:
        for machine_center in default_machine_centers:
            pairs.add((work_center_no, machine_center))
    if not pairs:
        return

    semaphore = asyncio.Semaphore(2)

    async def _refresh_one(work_center_no: str, machine_center: str) -> None:
        async with semaphore:
            try:
                await service.get_usage_history(
                    work_center_no=work_center_no,
                    machine_center=machine_center,
                    months=12,
                    refresh=True,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to refresh tooling usage-history cache",
                    extra={
                        "work_center_no": work_center_no,
                        "machine_center": machine_center,
                        "error": str(exc),
                    },
                )

    await asyncio.gather(*[_refresh_one(wc, mc) for wc, mc in sorted(pairs)])
