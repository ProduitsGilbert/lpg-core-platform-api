from app.domain.ocr.carrier_statement_repository import CarrierStatementRepository


GILBERT_HQ_ADDRESS = """Les Produits Gilbert Inc
Departement Dexpedition
1840 Marcotte BOUL
ROBERVAL
QC
G8H 2P2"""


def test_infer_purchase_when_shipped_to_gilbert_hq():
    workflow = CarrierStatementRepository.infer_workflow_type(
        shipped_from_address="DRILLMEX 2005 INC\n2105 RUE BOMBARDIER\nSAINTEJULIE\nQC\nJ3E 2N1",
        shipped_to_address=GILBERT_HQ_ADDRESS,
        ref_1=None,
        ref_2=None,
        fallback="sales",
    )
    assert workflow == "purchase"


def test_infer_sales_when_from_gilbert_and_gi_reference():
    workflow = CarrierStatementRepository.infer_workflow_type(
        shipped_from_address=GILBERT_HQ_ADDRESS,
        shipped_to_address="INTERFOR US INC\n71 GEORGIA PACIFIC RD\nBAY SPRINGS\nMS\n39422 US",
        ref_1=None,
        ref_2="GI21960",
        fallback="purchase",
    )
    assert workflow == "sales"


def test_infer_sales_when_from_gilbert_and_r_reference():
    workflow = CarrierStatementRepository.infer_workflow_type(
        shipped_from_address=GILBERT_HQ_ADDRESS,
        shipped_to_address="CLUB AUTONEIGE\n761 DES PRAIRIES CH\nJOLIETTE\nQC\nJ6E 8T6",
        ref_1="R1234",
        ref_2=None,
        fallback="purchase",
    )
    assert workflow == "sales"


def test_infer_fallback_when_rules_do_not_match():
    workflow = CarrierStatementRepository.infer_workflow_type(
        shipped_from_address="UNRELATED ORIGIN",
        shipped_to_address="UNRELATED DESTINATION",
        ref_1=None,
        ref_2=None,
        fallback="purchase",
    )
    assert workflow == "purchase"
