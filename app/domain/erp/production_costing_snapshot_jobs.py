from __future__ import annotations

import logging

from app.domain.erp.production_costing_snapshot_service import ProductionCostingSnapshotService

logger = logging.getLogger(__name__)


async def refresh_production_costing_snapshot() -> None:
    """Daily delta refresh for production costing snapshots."""
    service = ProductionCostingSnapshotService()
    if not service.is_configured:
        logger.warning("Cedule database not configured; skipping production costing snapshot refresh")
        return

    try:
        result = await service.run_scan(full_refresh=False, trigger_source="scheduler")
        logger.info(
            "Production costing refresh completed",
            extra={
                "status": result.status,
                "snapshot_created": result.snapshot_created,
                "scan_id": result.scan_id,
                "routing_headers_count": result.routing_headers_count,
                "bom_headers_count": result.bom_headers_count,
                "total_lines_count": result.total_lines_count,
            },
        )
    except Exception as exc:
        logger.warning(
            "Failed to refresh production costing snapshots",
            extra={"error": str(exc)},
        )
