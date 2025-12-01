"""Service for assembling Business Central item attribute values."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Iterable, List, Optional

import logfire

from app.domain.erp.business_central_data_service import BusinessCentralODataService
from app.domain.erp.models import ItemAttributeValueEntry, ItemAttributesResponse

logger = logging.getLogger(__name__)

_ITEMS_TABLE_ID = 27


class ItemAttributeService:
    """Retrieve and assemble item attributes from Business Central."""

    def __init__(self, odata_service: Optional[BusinessCentralODataService] = None) -> None:
        self._odata_service = odata_service or BusinessCentralODataService()

    async def get_item_attributes(self, item_no: str) -> ItemAttributesResponse:
        """Return all attribute values assigned to a specific item."""
        normalized_item = (item_no or "").strip()
        if not normalized_item:
            raise ValueError("item_no must be provided")

        with logfire.span("item_attributes.get", item_no=normalized_item):
            mappings = await self._odata_service.fetch_collection(
                "ItemAttributeValueMapping",
                filter_field="ItemNo",
                filter_value=normalized_item,
            )

            filtered_mappings = []
            for mapping in mappings:
                table_id = mapping.get("TableID")
                if table_id is not None and table_id != _ITEMS_TABLE_ID:
                    continue
                filtered_mappings.append(mapping)

            if not filtered_mappings:
                return ItemAttributesResponse(item_id=normalized_item, attributes=[])

            attribute_ids = {
                int(mapping["ItemAttributeID"])
                for mapping in filtered_mappings
                if mapping.get("ItemAttributeID") is not None
            }
            value_ids = {
                int(mapping["ItemAttributeValueID"])
                for mapping in filtered_mappings
                if mapping.get("ItemAttributeValueID") is not None
            }

            attribute_records, value_records = await asyncio.gather(
                self._load_attributes(attribute_ids),
                self._load_values(value_ids),
            )

            attributes: List[ItemAttributeValueEntry] = []
            for mapping in filtered_mappings:
                attr_id_raw = mapping.get("ItemAttributeID")
                value_id_raw = mapping.get("ItemAttributeValueID")
                attr_id = int(attr_id_raw) if attr_id_raw is not None else None
                value_id = int(value_id_raw) if value_id_raw is not None else None

                attribute = attribute_records.get(attr_id) if attr_id is not None else None
                value = value_records.get(value_id) if value_id is not None else None

                if not attribute or not value:
                    logger.warning(
                        "Missing attribute/value for mapping",
                        extra={
                            "item_no": normalized_item,
                            "attribute_id": attr_id,
                            "value_id": value_id,
                        },
                    )
                    continue

                attributes.append(
                    ItemAttributeValueEntry(
                        attribute_id=attr_id,
                        attribute_name=str(attribute.get("Name", "")),
                        attribute_type=str(attribute.get("Type", "")),
                        value_id=value_id,
                        value=str(value.get("Value", "")),
                    )
                )

            return ItemAttributesResponse(item_id=normalized_item, attributes=attributes)

    async def _load_attributes(self, attribute_ids: Iterable[int]) -> Dict[int, Dict[str, object]]:
        if not attribute_ids:
            return {}

        tasks = [
            self._odata_service.fetch_collection(
                "ItemAttributes",
                filter_field="ID",
                filter_value=attribute_id,
                top=1,
            )
            for attribute_id in attribute_ids
        ]

        results = await asyncio.gather(*tasks)
        attributes: Dict[int, Dict[str, object]] = {}

        for attr_list in results:
            if not attr_list:
                continue
            record = attr_list[0]
            attr_id = record.get("ID")
            if attr_id is None:
                continue
            attributes[int(attr_id)] = record

        return attributes

    async def _load_values(self, value_ids: Iterable[int]) -> Dict[int, Dict[str, object]]:
        if not value_ids:
            return {}

        tasks = [
            self._odata_service.fetch_collection(
                "ItemAttributeValues",
                filter_field="ID",
                filter_value=value_id,
                top=1,
            )
            for value_id in value_ids
        ]

        results = await asyncio.gather(*tasks)
        values: Dict[int, Dict[str, object]] = {}

        for value_list in results:
            if not value_list:
                continue
            record = value_list[0]
            value_id = record.get("ID")
            if value_id is None:
                continue
            values[int(value_id)] = record

        return values
