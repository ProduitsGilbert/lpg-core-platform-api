"""
Locate bubble label positions for BOM components in technical drawings (Option A: text coordinates).

This uses PyMuPDF to find the text occurrences of the bubble label (e.g., "1", "R1", "A2")
and returns a best-effort page/top/left. It does NOT attempt to detect the circle outline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import fitz  # PyMuPDF


@dataclass(frozen=True)
class BubbleLocation:
    page: int  # 1-based
    top: int
    left: int


class BubbleLocator:
    def locate_label(
        self,
        pdf_bytes: bytes,
        *,
        label: str,
        preferred_page: int | None = 1,
        prefer_drawing_pages: bool = True,
        max_pages: int | None = None,
    ) -> Optional[BubbleLocation]:
        label = (label or "").strip()
        if not label:
            return None

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            # First pass: explicitly prefer a specific page (default: 1) since exploded views
            # are typically on the first page for assembly drawings.
            if preferred_page is not None and doc.page_count > 0:
                idx = preferred_page - 1
                if 0 <= idx < doc.page_count:
                    page = doc[idx]
                    rects = page.search_for(label)
                    if rects:
                        r = sorted(rects, key=lambda rr: (rr.width * rr.height, rr.y0, rr.x0))[0]
                        return BubbleLocation(page=preferred_page, left=int(round(r.x0)), top=int(round(r.y0)))

            page_indices = list(range(doc.page_count))
            if max_pages is not None:
                page_indices = page_indices[:max_pages]

            # Heuristic: exploded-view pages usually have little text, while BOM tables have lots.
            if prefer_drawing_pages:
                scored = []
                for i in page_indices:
                    t = (doc[i].get_text("text") or "")
                    scored.append((len(t), i))
                scored.sort(key=lambda x: x[0])
                page_indices = [i for _, i in scored]

            # best tuple uses only primitive types to avoid Rect comparisons
            best: tuple[float, int, float, float, fitz.Rect] | None = None  # (area, page_idx, y0, x0, rect)
            for i in page_indices:
                page = doc[i]
                rects = page.search_for(label)
                if not rects:
                    continue
                for r in rects:
                    area = r.width * r.height
                    candidate = (area, i, r.y0, r.x0, r)
                    if best is None or candidate[:4] < best[:4]:
                        best = candidate

            if best is None and prefer_drawing_pages:
                # Fallback: scan all pages in order.
                for i in (list(range(doc.page_count)) if max_pages is None else list(range(min(doc.page_count, max_pages)))):
                    page = doc[i]
                    rects = page.search_for(label)
                    if not rects:
                        continue
                    r = sorted(rects, key=lambda rr: rr.width * rr.height)[0]
                    return BubbleLocation(page=i + 1, left=int(round(r.x0)), top=int(round(r.y0)))

            if best is None:
                return None

            _, page_idx, _, _, rect = best
            return BubbleLocation(page=page_idx + 1, left=int(round(rect.x0)), top=int(round(rect.y0)))
        finally:
            doc.close()


