"""XML builders and parsers for ElekNet integration."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from typing import Any

from .errors import ElekNetInvalidResponseError
from .schemas import (
    ElekNetOrderRequest,
    ElekNetOrderResponse,
    ElekNetPriceAvailabilityItem,
    ElekNetPriceAvailabilityRequest,
    ElekNetPriceAvailabilityResponse,
    ElekNetStockDetail,
)


def build_xpa_request_xml(
    *,
    username: str,
    password: str,
    request: ElekNetPriceAvailabilityRequest,
) -> str:
    """Build xPA XML request payload."""
    root = ET.Element("request")

    header = ET.SubElement(root, "header", attrib={"version": "1.0"})
    ET.SubElement(header, "username").text = username
    ET.SubElement(header, "password").text = password
    ET.SubElement(header, "productInfo").text = "true" if request.productInfo else "false"

    body = ET.SubElement(root, "body")
    item_list = ET.SubElement(body, "itemList")

    for line in request.items:
        item = ET.SubElement(item_list, "item")
        ET.SubElement(item, "productCode").text = line.productCode
        ET.SubElement(item, "qty").text = str(line.qty)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def build_order_request_xml(
    *,
    username: str,
    password: str,
    request: ElekNetOrderRequest,
) -> str:
    """Build order XML request payload."""
    root = ET.Element("request")

    header = ET.SubElement(root, "header")
    ET.SubElement(header, "version").text = "1.0"
    ET.SubElement(header, "username").text = username
    ET.SubElement(header, "password").text = password

    body = ET.SubElement(root, "body")
    xml_header = ET.SubElement(body, "orderHeader")
    header_data = request.orderHeader.model_dump(exclude_none=True)

    shipping_date = header_data.pop("shippingDate", None)
    if isinstance(shipping_date, date):
        header_data["shippingDate"] = shipping_date.isoformat()
    elif shipping_date is not None:
        header_data["shippingDate"] = str(shipping_date)

    shipping_address = header_data.pop("shippingAddress", None)

    header_order = [
        "partner",
        "type",
        "custno",
        "shipTo",
        "whse",
        "po",
        "delivery",
        "shipComplete",
        "shippingDate",
        "buyer",
        "contactName",
        "phone",
        "email",
        "comments",
    ]
    _append_ordered_tags(xml_header, header_data, header_order)

    if shipping_address:
        xml_shipping = ET.SubElement(xml_header, "shippingAddress")
        shipping_order = [
            "name",
            "address1",
            "address2",
            "city",
            "state",
            "postalCode",
            "country",
            "phone",
            "email",
        ]
        _append_ordered_tags(xml_shipping, shipping_address, shipping_order)

    xml_lines = ET.SubElement(body, "orderLines")
    for line in request.orderLines:
        xml_line = ET.SubElement(xml_lines, "line")
        line_data = line.model_dump(exclude_none=True)
        line_order = ["productCode", "qty", "description", "price", "comments", "uom"]
        _append_ordered_tags(xml_line, line_data, line_order)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def parse_xpa_response(xml_text: str) -> ElekNetPriceAvailabilityResponse:
    """Parse xPA XML response into normalized JSON shape."""
    root = _parse_xml(xml_text)
    return_code = _get_text(root, "returnCode")
    return_message = _get_text(root, "returnMessage")

    items: list[ElekNetPriceAvailabilityItem] = []
    for item in _find_all(root, "item"):
        additional_fields: dict[str, str] = {}
        for child in list(item):
            tag_name = _local_name(child.tag)
            tag_lower = tag_name.lower()
            if tag_lower in {
                "status",
                "productcode",
                "qty",
                "unitprice",
                "listprice",
                "netprice",
                "extprice",
                "uom",
                "description",
                "returnmessage",
                "stock",
            }:
                continue
            if list(child):
                continue
            text_value = _clean_text(child.text)
            if text_value is not None:
                additional_fields[tag_name] = text_value

        stock_entries = [
            ElekNetStockDetail(
                whse=_get_text(detail, "whse"),
                whseName=_get_text(detail, "whseName"),
                qtyStock=_as_float(_get_text(detail, "qtyStock")),
            )
            for detail in _find_all(item, "whseDetail")
        ]

        items.append(
            ElekNetPriceAvailabilityItem(
                status=_get_text(item, "status"),
                productCode=_get_text(item, "productCode"),
                qty=_as_float(_get_text(item, "qty")),
                unitPrice=_as_float(_get_text(item, "unitPrice")),
                listPrice=_as_float(_get_text(item, "listPrice")),
                netPrice=_as_float(_get_text(item, "netPrice")),
                extPrice=_as_float(_get_text(item, "extPrice")),
                uom=_get_text(item, "uom") or _get_text(item, "UOM"),
                description=_get_text(item, "description"),
                returnMessage=_get_text(item, "returnMessage"),
                stock=stock_entries,
                additionalFields=additional_fields,
            )
        )

    return ElekNetPriceAvailabilityResponse(
        returnCode=return_code,
        returnMessage=return_message,
        items=items,
    )


def parse_order_response(xml_text: str) -> ElekNetOrderResponse:
    """Parse order XML response into normalized JSON shape."""
    root = _parse_xml(xml_text)
    return ElekNetOrderResponse(
        returnCode=_get_text(root, "returnCode"),
        po=_get_text(root, "po"),
        orderNumber=_get_text(root, "orderNumber"),
        returnMessage=_get_text(root, "returnMessage"),
    )


def _append_ordered_tags(node: ET.Element, data: dict[str, Any], preferred_order: list[str]) -> None:
    """Append child tags in a preferred order then append any extra keys deterministically."""
    emitted: set[str] = set()
    for key in preferred_order:
        value = data.get(key)
        if value is None:
            continue
        ET.SubElement(node, key).text = str(value)
        emitted.add(key)

    for key in sorted(data.keys()):
        if key in emitted:
            continue
        value = data[key]
        if value is None:
            continue
        ET.SubElement(node, key).text = str(value)


def _parse_xml(xml_text: str) -> ET.Element:
    try:
        return ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ElekNetInvalidResponseError("Invalid XML response from ElekNet") from exc


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", maxsplit=1)[-1]
    return tag


def _find_all(element: ET.Element, name: str) -> list[ET.Element]:
    match = name.lower()
    return [node for node in element.iter() if _local_name(node.tag).lower() == match]


def _get_text(element: ET.Element, name: str) -> str | None:
    match = name.lower()
    for node in element.iter():
        if _local_name(node.tag).lower() == match:
            return _clean_text(node.text)
    return None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _as_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None
