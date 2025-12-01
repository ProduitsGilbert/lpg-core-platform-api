import pytest

from app.domain.erp.item_attribute_service import ItemAttributeService


class StubODataService:
    async def fetch_collection(self, resource, *, filter_field=None, filter_value=None, top=None):
        if resource == "ItemAttributeValueMapping":
            return [
                {"TableID": 27, "ItemNo": "0410604", "ItemAttributeID": 2, "ItemAttributeValueID": 372},
                {"TableID": 27, "ItemNo": "0410604", "ItemAttributeID": 5, "ItemAttributeValueID": 90},
                {"TableID": 99, "ItemNo": "0410604", "ItemAttributeID": 999, "ItemAttributeValueID": 999},
            ]

        if resource == "ItemAttributes":
            if filter_value == 2:
                return [{"ID": 2, "Name": "Matériel", "Type": "Option"}]
            if filter_value == 5:
                return [{"ID": 5, "Name": "Epaisseur", "Type": "Decimal"}]
            return []

        if resource == "ItemAttributeValues":
            if filter_value == 372:
                return [{"ID": 372, "Value": "HARDOX-450"}]
            if filter_value == 90:
                return [{"ID": 90, "Value": "0.375"}]
            return []

        return []


@pytest.mark.asyncio
async def test_item_attribute_service_returns_joined_attributes():
    service = ItemAttributeService(odata_service=StubODataService())

    result = await service.get_item_attributes("0410604")

    assert result.item_id == "0410604"
    assert len(result.attributes) == 2
    assert result.attributes[0].attribute_name == "Matériel"
    assert result.attributes[0].value == "HARDOX-450"
    assert result.attributes[1].attribute_type == "Decimal"
    assert result.attributes[1].value == "0.375"


@pytest.mark.asyncio
async def test_item_attribute_service_requires_item_no():
    service = ItemAttributeService(odata_service=StubODataService())
    with pytest.raises(ValueError):
        await service.get_item_attributes("")
