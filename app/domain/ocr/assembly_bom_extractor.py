"""
Deterministic BOM extractor for mechanical assembly drawings.

This is intentionally non-LLM: for most Gilbert engineering drawings the BOM table
is text-based and pypdf can extract a reliable text layer.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Optional

from pypdf import PdfReader


@dataclass(frozen=True)
class _ParsedComponent:
    item_no: str
    qty: int
    position: str


class AssemblyBOMExtractor:
    """
    Extract component list from a technical drawing PDF.

    Strategy (works for `tests/7260012.pdf`):
    - Extract text using pypdf
    - Find 7-digit item numbers in the text
    - For each item number, infer qty and position from adjacent digit runs
      (because the table columns often end up concatenated in the extracted text).
    """

    # BOM rows usually appear as digit-runs: (qty)(item_no)(position), often concatenated.
    # Some rows can have extra leading digits due to dimension fragments being concatenated.
    _DIGIT_RUN_RE = re.compile(r"\d{9,30}")
    # Fallback: table-like text where columns are separated by whitespace/newlines:
    #   <position> <item_no> <qty>
    # Supports positions like "1" and "R1".
    _TABLE_ROW_RE = re.compile(r"(?m)^\s*(?P<pos>R\d+|\d+)\s+(?P<item>\d{7})\s+(?P<qty>\d{1,3})\b")

    def extract_components_from_pdf(
        self,
        pdf_bytes: bytes,
        *,
        root_item_no: Optional[str] = None,
        max_pages: int = 5,
    ) -> list[_ParsedComponent]:
        text = self._extract_pdf_text(pdf_bytes, max_pages=max_pages)
        return self.extract_components_from_text(text, root_item_no=root_item_no)

    def extract_components_from_text(
        self,
        text: str,
        *,
        root_item_no: Optional[str] = None,
    ) -> list[_ParsedComponent]:
        if not text:
            return []

        components: list[_ParsedComponent] = []
        seen: set[tuple[str, str]] = set()  # (position, item_no)

        for m in self._DIGIT_RUN_RE.finditer(text):
            run = m.group(0)
            parsed = self._parse_digit_run(run)
            if not parsed:
                continue
            if root_item_no and parsed.item_no == root_item_no:
                continue

            key = (parsed.position, parsed.item_no)
            if key in seen:
                continue
            seen.add(key)

            components.append(parsed)

        # Fallback/augment: table rows with explicit position + item_no + qty.
        for m in self._TABLE_ROW_RE.finditer(text):
            position = m.group("pos")
            item_no = m.group("item")
            qty = int(m.group("qty"))
            if root_item_no and item_no == root_item_no:
                continue
            if qty <= 0:
                continue
            key = (position, item_no)
            if key in seen:
                continue
            seen.add(key)
            components.append(_ParsedComponent(item_no=item_no, qty=qty, position=str(position)))

        components.sort(key=self._position_sort_key)
        return components

    @staticmethod
    def _extract_pdf_text(pdf_bytes: bytes, *, max_pages: int) -> str:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text: list[str] = []
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            extracted = page.extract_text() or ""
            if extracted.strip():
                pages_text.append(extracted)
        return "\n".join(pages_text)

    @classmethod
    def _parse_digit_run(cls, run: str) -> Optional[_ParsedComponent]:
        """
        Parse a digit run into (qty, item_no, position).

        Expected shape (ending at the end of the run):
          [optional noise digits][qty 1-3][item_no 7][position 1-3]
        """
        if not run or not run.isdigit():
            return None

        best: tuple[int, _ParsedComponent] | None = None

        # Many drawings concatenate extra numeric fragments before the BOM digits.
        # We'll search over tails that end at the run end, dropping an increasing amount
        # of leading noise, and pick the highest-scoring parse.
        max_tail = min(len(run), 20)
        tail = run[-max_tail:]
        max_drop = max(0, len(tail) - 9)  # need at least qty(1)+item(7)+pos(1)

        for drop in range(0, max_drop + 1):
            candidate_run = tail[drop:]
            parsed = cls._parse_bom_tail(candidate_run)
            if not parsed:
                continue
            dropped = tail[:drop]
            score = cls._score_component(parsed, dropped_prefix=dropped)
            # Prefer not to drop dimension-like digits (qty parsing can usually handle those).
            if dropped and dropped.isdigit() and all(ch in "1234" for ch in dropped):
                score -= 2 * len(dropped)
            if best is None or score > best[0]:
                best = (score, parsed)

        return best[1] if best else None

    @classmethod
    def _parse_bom_tail(cls, digits: str) -> Optional[_ParsedComponent]:
        """
        Parse a tail substring into qty/item/position by assuming:
          ... [qty_prefix][item_no 7][pos 1-3]
        """
        if len(digits) < 9 or not digits.isdigit():
            return None

        best: tuple[int, _ParsedComponent] | None = None

        for pos_len in (1, 2, 3):
            if pos_len >= len(digits):
                continue
            pos_str = digits[-pos_len:]
            if pos_str == "0":
                continue
            pos = int(pos_str)
            if not (1 <= pos <= 300):
                continue

            core = digits[:-pos_len]
            if len(core) < 8:
                continue
            item_str = core[-7:]
            qty_prefix = core[:-7]

            qty = cls._choose_qty_from_prefix(qty_prefix)
            if qty is None or not (1 <= qty <= 300):
                continue

            comp = _ParsedComponent(item_no=item_str, qty=qty, position=str(pos))
            score = cls._score_component(comp, dropped_prefix="")

            # Prefer the "natural" position-length for the position value.
            if pos >= 10 and pos_len >= 2:
                score += 4
            if pos < 10 and pos_len == 1:
                score += 2

            # Gilbert part numbers very rarely start with 1/2/4/5; those are usually artifacts.
            if item_str[0] in {"1", "2", "4", "5"}:
                score -= 6

            if best is None or score > best[0]:
                best = (score, comp)

        return best[1] if best else None

    @staticmethod
    def _choose_qty_from_prefix(prefix: str) -> Optional[int]:
        """
        Pick qty from the digits preceding the item number.
        Allows up to 2 leading 'noise' digits (often from dimensions like 1/2, 3/4).
        """
        prefix = (prefix or "").strip()
        if not prefix or not prefix.isdigit():
            return None

        best: tuple[int, int] | None = None  # (score, qty)
        for qty_len in (1, 2, 3):
            if qty_len > len(prefix):
                continue
            qty_str = prefix[-qty_len:]
            noise = prefix[:-qty_len]
            if len(noise) > 2:
                continue
            if qty_str == "0":
                continue
            qty = int(qty_str)
            if qty <= 0:
                continue

            score = 0
            if noise and all(ch in "1234" for ch in noise):
                score += 4
                if qty <= 20:
                    score += 4
            elif not noise:
                score += 2
            else:
                score -= 2

            # Special-case: avoid interpreting '16' as noise '1' + qty '6' (common false positive).
            # For 2-digit prefixes, only allow 1-digit noise when the noise digit is a typical fraction digit.
            if len(prefix) == 2 and len(noise) == 1:
                if noise == "1":
                    score -= 8
                elif noise in {"2", "4"} and qty <= 9:
                    score += 3

            # For 3-digit prefixes, a 2-digit "noise" is usually a bad sign (it tends to produce qty=4 instead of 24).
            if len(noise) == 2:
                score -= 6

            if qty <= 99:
                score += 2
            if qty in (1, 2, 4, 8, 10, 16, 24, 40, 64, 88):
                score += 1

            score -= len(noise)

            if best is None or score > best[0]:
                best = (score, qty)

        return best[1] if best else None

    @staticmethod
    def _score_component(comp: _ParsedComponent, *, dropped_prefix: str) -> int:
        """
        Score to break ties between parses.
        """
        score = 0
        pos = int(comp.position) if comp.position.isdigit() else 9999

        # Prefer "natural" position formatting.
        if pos >= 10 and len(comp.position) >= 2:
            score += 3
        if pos <= 99:
            score += 2
        if pos >= 90:
            score -= 8

        # Mild preference for smaller qty unless the parse requires it.
        if comp.qty <= 99:
            score += 2
        if comp.qty in (1, 2, 4, 8, 10, 16, 24, 40, 64, 88):
            score += 1

        # Penalize obviously shifted item numbers (double leading zeros are rare).
        if comp.item_no.startswith("00"):
            score -= 12
        if comp.item_no.startswith("0"):
            score += 1

        # If we dropped prefix digits and they look like dimension fragments, reward.
        if dropped_prefix and dropped_prefix.isdigit() and all(ch in "1234" for ch in dropped_prefix):
            score += 2

        return score

    @staticmethod
    def _position_sort_key(comp: _ParsedComponent) -> tuple[int, int, str]:
        pos = comp.position
        if pos.isdigit():
            return (0, int(pos), pos)
        # Reference positions like R1 should come after numeric ones, but still sort by their numeric portion.
        digits = "".join(ch for ch in pos if ch.isdigit())
        num = int(digits) if digits else 10_000
        return (1, num, pos)


