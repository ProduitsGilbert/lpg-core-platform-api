"""KPI service for Fastems pallet usage statistics."""

from __future__ import annotations

from typing import List, Optional

from app.domain.kpi.models import Fastems1PalletUsage, Fastems2PalletUsage
from app.integrations.cedule_fastems_pallet_usage_repository import (
    FastemsPalletUsageRepository,
)


class FastemsPalletUsageService:
    """Service layer for Fastems pallet usage views."""

    def __init__(self, repository: Optional[FastemsPalletUsageRepository] = None) -> None:
        self._repository = repository or FastemsPalletUsageRepository()

    @property
    def is_configured(self) -> bool:
        return self._repository.is_configured

    def list_fastems1_usage(self) -> List[Fastems1PalletUsage]:
        return self._repository.list_fastems1_usage()

    def list_fastems2_usage(self) -> List[Fastems2PalletUsage]:
        return self._repository.list_fastems2_usage()
