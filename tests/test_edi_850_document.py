import pytest

from migration.edi import build_edi_850_document


@pytest.fixture
def po_header():
    return {
        "Document_Date": "2024-05-01",
        "Amount": "100.00",
        "Amount_Including_VAT": "115.00",
        "Buy_from_Vendor_No": "VEND01",
        "Payment_Terms_Code": "NET30",
    }


@pytest.fixture
def po_lines():
    return [
        {
            "Line_No": 10000,
            "Quantity": "2",
            "Unit_of_Measure_Code": "EA",
            "Direct_Unit_Cost": "50.00",
            "Vendor_Item_No": "VI-100",
            "No": "ITEM-100",
            "Description": "Sample Item",
        }
    ]


@pytest.fixture
def vendor_info():
    return {
        "No": "VEND01",
        "Name": "Vendor Inc",
        "Address": "123 Main",
        "City": "Townsville",
        "County": "QC",
        "Post_Code": "A1B2C3",
    }


def test_build_edi_850_document_matches_expected_format(po_header, po_lines, vendor_info):
    document = build_edi_850_document("PO123", po_header, po_lines, vendor_info)

    lines = document.strip().splitlines()

    assert lines[0] == "ID|850|GILBERTTECHP|VEND01|"
    assert "HEAD|||20240501|PO123|00|NE|" in lines
    assert "TERMS_GEN|NET30|" in lines
    assert "DATE|DR|20240501|" in lines
    assert "FOB|PP|ZZ|SHIPPING POINT|" in lines
    assert "ITEM|1|2.0000|EA|50.0000|VN|VI-100" in document
    assert "DESC|Sample Item|" in lines
    assert "TOTAL|TT|115.00|100.00|" in lines
    assert "TOTAL_TAX|TAX|15.00|" in lines


def test_build_edi_850_document_requires_lines(po_header, vendor_info):
    with pytest.raises(ValueError):
        build_edi_850_document("PO123", po_header, [], vendor_info)


def test_build_edi_850_document_requires_vendor_number(po_header, po_lines):
    header_without_vendor = {key: value for key, value in po_header.items() if key != "Buy_from_Vendor_No"}

    with pytest.raises(ValueError):
        build_edi_850_document("PO123", header_without_vendor, po_lines, {})
