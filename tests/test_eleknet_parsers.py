from app.domain.edi.eleknet.parsers import (
    build_order_request_xml,
    build_xpa_request_xml,
    parse_order_response,
    parse_xpa_response,
)
from app.domain.edi.eleknet.schemas import (
    ElekNetOrderHeader,
    ElekNetOrderLine,
    ElekNetOrderRequest,
    ElekNetPriceAvailabilityItemRequest,
    ElekNetPriceAvailabilityRequest,
)


def test_build_xpa_request_xml_contains_expected_structure():
    request = ElekNetPriceAvailabilityRequest(
        items=[
            ElekNetPriceAvailabilityItemRequest(productCode="ABC-001", qty=2),
            ElekNetPriceAvailabilityItemRequest(productCode="XYZ-002", qty=5),
        ],
        productInfo=True,
    )

    xml_payload = build_xpa_request_xml(
        username="lumen-user",
        password="secret",
        request=request,
    )

    assert xml_payload.startswith("<?xml version='1.0' encoding='utf-8'?>")
    assert "<header version=\"1.0\">" in xml_payload
    assert "<username>lumen-user</username>" in xml_payload
    assert "<password>secret</password>" in xml_payload
    assert "<productInfo>true</productInfo>" in xml_payload
    assert "<productCode>ABC-001</productCode>" in xml_payload
    assert "<qty>5</qty>" in xml_payload


def test_build_order_request_xml_contains_expected_structure():
    request = ElekNetOrderRequest(
        orderHeader=ElekNetOrderHeader(
            partner="Lumen",
            type="Order",
            custno="CUST-01",
            shipTo="SHIP-01",
            whse="WH-1",
            po="PO-100",
            delivery="Y",
            shipComplete="N",
        ),
        orderLines=[
            ElekNetOrderLine(productCode="ABC-001", qty=3, description="Widget", price=12.5),
        ],
    )

    xml_payload = build_order_request_xml(
        username="lumen-user",
        password="secret",
        request=request,
    )

    assert xml_payload.startswith("<?xml version='1.0' encoding='utf-8'?>")
    assert "<header><version>1.0</version><username>lumen-user</username><password>secret</password></header>" in xml_payload
    assert "<orderHeader>" in xml_payload
    assert "<partner>Lumen</partner>" in xml_payload
    assert "<orderLines><line><productCode>ABC-001</productCode><qty>3</qty>" in xml_payload


def test_parse_xpa_response_maps_empty_nodes_to_none_and_extracts_stock():
    xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<xPAResponse>
  <returnCode>S</returnCode>
  <itemList>
    <item>
      <status>S</status>
      <productCode>ABC-001</productCode>
      <unitPrice />
      <listPrice>21.5</listPrice>
      <netPrice>19.0</netPrice>
      <extPrice>38.0</extPrice>
      <UOM>EA</UOM>
      <stock>
        <whseDetail>
          <whse>W1</whse>
          <whseName>Main</whseName>
          <qtyStock>12</qtyStock>
        </whseDetail>
      </stock>
    </item>
  </itemList>
</xPAResponse>"""

    parsed = parse_xpa_response(xml_response)

    assert parsed.returnCode == "S"
    assert len(parsed.items) == 1
    assert parsed.items[0].productCode == "ABC-001"
    assert parsed.items[0].unitPrice is None
    assert parsed.items[0].listPrice == 21.5
    assert parsed.items[0].uom == "EA"
    assert parsed.items[0].stock[0].whse == "W1"
    assert parsed.items[0].stock[0].qtyStock == 12.0


def test_parse_order_response_extracts_core_fields():
    xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<orderResponse>
  <returnCode>S</returnCode>
  <po>PO-100</po>
  <orderNumber>12345</orderNumber>
</orderResponse>"""

    parsed = parse_order_response(xml_response)

    assert parsed.returnCode == "S"
    assert parsed.po == "PO-100"
    assert parsed.orderNumber == "12345"
