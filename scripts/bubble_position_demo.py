"""
Demo script: locate BOM bubble label positions on the exploded view (Option A: vector/text).

This does NOT modify any API endpoint. It's a local experiment to validate feasibility.

Usage:
  python3 scripts/bubble_position_demo.py --item 7260012 --pdf tests/7260012.pdf --page 1

Output:
  Prints JSON with components and an optional PdfPosition block:
    { "page": 1, "top": 152, "left": 625 }

Notes:
  - Coordinates are in PyMuPDF page space (origin top-left, units in PDF points).
  - This finds the *label text* bbox, not the circle outline.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF

# Allow running as a script from repo root without installing the package.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.domain.ocr.assembly_bom_extractor import AssemblyBOMExtractor  # noqa: E402


def _rect_to_pos(rect: fitz.Rect) -> dict[str, int]:
    # Use top-left of the bbox; can be switched to center if preferred.
    return {"left": int(round(rect.x0)), "top": int(round(rect.y0))}


def _find_best_label_rect(
    page: fitz.Page,
    label: str,
    *,
    max_candidates: int = 25,
) -> Optional[fitz.Rect]:
    """
    Find the best bbox for a bubble label on a given page.

    Heuristic: choose among exact text matches and prefer small bboxes (bubble labels are small).
    """
    label = (label or "").strip()
    if not label:
        return None

    # search_for finds occurrences of the string in the page text layer.
    rects = page.search_for(label)
    if not rects:
        return None

    # Keep best candidates; sort by area (ascending), then by y then x for determinism.
    rects = sorted(rects, key=lambda r: ((r.width * r.height), r.y0, r.x0))[:max_candidates]

    # Choose smallest by area. This will often pick the bubble label over title/table digits.
    return rects[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--item", required=True, help="Root assembly item number")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--page", type=int, default=1, help="1-based page number to search for bubbles (default: 1)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    pdf_bytes = pdf_path.read_bytes()

    extractor = AssemblyBOMExtractor()
    components = extractor.extract_components_from_pdf(pdf_bytes, root_item_no=args.item)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_idx = max(0, args.page - 1)
    page = doc[page_idx]

    out_components: list[dict[str, Any]] = []
    for c in components:
        rect = _find_best_label_rect(page, c.position)
        payload: dict[str, Any] = {
            "itemNo": c.item_no,
            "qty": c.qty,
            "position": c.position,
        }
        if rect is not None:
            payload["PdfPosition"] = {"page": args.page, **_rect_to_pos(rect)}
        else:
            payload["PdfPosition"] = None
        out_components.append(payload)

    out = {"itemNo": args.item, "type": "Assembly", "pageSearched": args.page, "components": out_components}
    print(json.dumps(out, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


