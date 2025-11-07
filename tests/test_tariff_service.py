import pytest

from app.domain.erp.tariff_service import TariffCalculationService
from app.integrations.cedule_repository import MillTestCertificate


class FakeERPClient:
    def __init__(self) -> None:
        self.items = {
            "PARENT": {
                "No": "PARENT",
                "Production_BOM_No": "BOM-001",
            },
            "COMP-ASM": {
                "No": "COMP-ASM",
                "Production_BOM_No": "BOM-ASM",
                "Description": "SUB ASSEMBLY",
                "Standard_Cost": 1.23,
            },
            "RAW-ROUND": {
                "No": "RAW-ROUND",
                "Description": 'ROUND BAR 2" DIA',
                "Standard_Cost": 12.5,
                "Vendor_No": "VENDOR-1",
                "Vendor_Item_No": "V1-ROUND",
            },
            "RAW-PLATE": {
                "No": "RAW-PLATE",
                "Description": 'PLAQUE 1/2" X 10 X 10',
                "Standard_Cost": 8.75,
                "Vendor_No": "VENDOR-2",
                "Vendor_Item_No": "V2-PLATE",
            },
        }
        self.boms = {
            "BOM-001": [
                {
                    "Type": "Item",
                    "No": "COMP-ASM",
                    "Description": "SUB ASSEMBLY",
                    "Quantity_per": 1,
                    "Scrap_Percent": 0,
                    "Calculation_Formula": "",
                    "Length": 0,
                    "Width": 0,
                    "Depth": 0,
                    "Unit_of_Measure_Code": "UN",
                },
                {
                    "Type": "Item",
                    "No": "RAW-ROUND",
                    "Description": 'ROUND BAR 2" DIA',
                    "Quantity_per": 2,
                    "Scrap_Percent": 5,
                    "Calculation_Formula": "Length",
                    "Length": 18,
                    "Width": 0,
                    "Depth": 0,
                    "Unit_of_Measure_Code": "UN",
                },
            ],
            "BOM-ASM": [
                {
                    "Type": "Item",
                    "No": "RAW-PLATE",
                    "Description": 'PLAQUE 1/2" X 10 X 10',
                    "Quantity_per": 1,
                    "Scrap_Percent": 10,
                    "Calculation_Formula": "Length * Width",
                    "Length": 10,
                    "Width": 10,
                    "Depth": 0.5,
                    "Unit_of_Measure_Code": "PO2",
                }
            ],
        }

    async def get_item(self, item_id: str):
        return self.items.get(item_id)

    async def get_bom_component_lines(self, bom_no: str):
        return list(self.boms.get(bom_no, []))


class FakeCertificateRepo:
    def __init__(self) -> None:
        self.is_configured = True

    def get_latest_certificate(self, part_number: str):
        mapping = {
            "PARENT": MillTestCertificate(
                part_number="PARENT",
                country_of_melt_and_pour="Canada",
                country_of_manufacture="Canada",
                material_description="Assembly",
                line_total_weight=100.0,
                weight_unit="LB",
                certification_date=None,
            ),
            "RAW-ROUND": MillTestCertificate(
                part_number="RAW-ROUND",
                country_of_melt_and_pour="USA",
                country_of_manufacture="Mexico",
                material_description="Round Bar",
                line_total_weight=50.0,
                weight_unit="LB",
                certification_date=None,
            ),
            "RAW-PLATE": MillTestCertificate(
                part_number="RAW-PLATE",
                country_of_melt_and_pour="USA",
                country_of_manufacture="USA",
                material_description="Plate",
                line_total_weight=25.0,
                weight_unit="LB",
                certification_date=None,
            ),
        }
        return mapping.get(part_number)


@pytest.mark.asyncio
async def test_tariff_service_builds_summary_and_materials():
    service = TariffCalculationService(
        erp_client=FakeERPClient(),
        certificate_repo=FakeCertificateRepo(),
    )

    response = await service.calculate("PARENT")

    assert response.item_id == "PARENT"
    assert response.production_bom_no == "BOM-001"
    assert response.summary.total_materials == 2
    assert response.summary.total_weight_kg > 0
    assert response.summary.total_cost_cad > 0
    assert response.parent_country_of_melt_and_pour == "Canada"
    melt_countries = {m.country_of_melt_and_pour for m in response.materials}
    assert "USA" in melt_countries
    vendors = {m.vendor_no for m in response.materials}
    assert "VENDOR-1" in vendors
    assert response.report.startswith("TARIFF/WEIGHT CALCULATION REPORT")
