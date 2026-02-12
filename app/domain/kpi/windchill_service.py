"""Service layer for Windchill KPI queries."""

from __future__ import annotations

from typing import List, Optional

from app.domain.kpi.models import (
    WindchillCreatedDrawingsPerUser,
    WindchillModifiedDrawingsPerUser,
)
from app.integrations.windchill_repository import WindchillRepository


class WindchillKpiService:
    """Facade over Windchill KPI repository queries."""

    def __init__(self, repository: Optional[WindchillRepository] = None) -> None:
        self._repository = repository or WindchillRepository()

    @property
    def is_configured(self) -> bool:
        return self._repository.is_configured

    def list_created_drawings_per_user(self) -> List[WindchillCreatedDrawingsPerUser]:
        rows = self._repository.list_created_drawings_per_user()
        return [
            WindchillCreatedDrawingsPerUser(
                count=row.count,
                creation_date=row.creation_date,
                created_by=row.created_by,
            )
            for row in rows
        ]

    def list_modified_drawings_per_user(self) -> List[WindchillModifiedDrawingsPerUser]:
        rows = self._repository.list_modified_drawings_per_user()
        return [
            WindchillModifiedDrawingsPerUser(
                count=row.count,
                last_modified=row.last_modified,
                modified_by=row.modified_by,
            )
            for row in rows
        ]
