"""
Fixture/pallet data access for Fastems1 Autopilot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

from app.integrations.cedule_repository import get_cedule_engine

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FixtureMatrixRow:
    piece_code: str
    fixture_code: str
    fixture_description: Optional[str]
    storage_location: Optional[str]
    machine_operation: Optional[str]
    machine_pallet_id: Optional[int]
    machine_pallet_number: Optional[str]
    machine_id: Optional[str]
    is_active: Optional[bool]
    required_plaque_model: Optional[str]
    pallet_plaque_model: Optional[str]


@dataclass(slots=True)
class MachinePalletReference:
    pallet_id: int
    pallet_number: Optional[str]
    machine_id: Optional[str]
    plaque_model: Optional[str]
    description: Optional[str]


def _normalize_code(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


class CeduleAutopilotRepository:
    """
    Provides fixture + pallet context using the Autopilot_FixtureMatrix view described
    in the PRD. Read-only calls only.
    """

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()
        self._pallet_cache: Optional[List[MachinePalletReference]] = None

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def get_fixture_matrix(self, piece_code: str) -> List[FixtureMatrixRow]:
        if not self._engine:
            logger.warning("Cedule Autopilot repository not configured; returning empty fixture matrix")
            return []

        piece_root = piece_code.split("-", 1)[0].strip().upper()
        params = {
            "piece_code": piece_code,
            "piece_code_upper": piece_code.upper(),
            "piece_prefix": f"{piece_root}-%",
        }

        query = text(
            """
            SELECT
                PieceCode,
                RequiredGabaritNumero AS FixtureCode,
                GabaritDescription,
                CONCAT(FixtureStorageRow, '-', FixtureStorageColumn) AS StorageLocation,
                RequiredMachineOperation,
                MachinePalletId,
                MachinePalletNumber,
                MachineForPallet,
                IsFixtureActive,
                RequiredPlaqueModel,
                PalletPlaqueModel
            FROM Cedule.dbo.Autopilot_FixtureMatrix
            WHERE
                RTRIM(LTRIM(PieceCode)) = :piece_code
                OR UPPER(RTRIM(LTRIM(PieceCode))) = :piece_code_upper
            """
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query, params).mappings().all()
        except ProgrammingError as exc:
            if "RequiredPlaqueModel" in str(exc):
                logger.warning(
                    "Autopilot_FixtureMatrix missing plaque columns; using compatibility query",
                    extra={"piece_code": piece_code},
                )
                rows = self._query_fixture_matrix_compat(piece_code, params)
            else:
                logger.error("Failed to query Autopilot_FixtureMatrix", exc_info=exc, extra={"piece_code": piece_code})
                return []
        except SQLAlchemyError as exc:
            logger.error("Failed to query Autopilot_FixtureMatrix", exc_info=exc, extra={"piece_code": piece_code})
            return []

        results: List[FixtureMatrixRow] = []
        for row in rows:
            results.append(
                FixtureMatrixRow(
                    piece_code=row.get("PieceCode", "").strip(),
                    fixture_code=_normalize_code(row.get("FixtureCode")),
                    fixture_description=row.get("GabaritDescription"),
                    storage_location=row.get("StorageLocation"),
                    machine_operation=row.get("RequiredMachineOperation"),
                    machine_pallet_id=row.get("MachinePalletId"),
                    machine_pallet_number=row.get("MachinePalletNumber"),
                    machine_id=row.get("MachineForPallet"),
                    is_active=bool(row.get("IsFixtureActive")),
                    required_plaque_model=_normalize_code(row.get("RequiredPlaqueModel")),
                    pallet_plaque_model=_normalize_code(row.get("PalletPlaqueModel")),
                )
            )

        has_fixture_codes = any(row.fixture_code for row in results)
        has_pallet_assignments = any(row.machine_pallet_id for row in results)
        missing_plaque = any(row.required_plaque_model is None for row in results)
        if results and has_fixture_codes and has_pallet_assignments and not missing_plaque:
            return results

        # Fallback: pull base fixture info even if no pallet is currently configured
        fallback_query = text(
            """
            SELECT
                pg.Piece AS PieceCode,
                pg.Gabarit AS FixtureCode,
                gu.Description AS GabaritDescription,
                CONCAT(gu.Emplacement_Lettre, '-', gu.Emplacement_Chiffre) AS StorageLocation,
                pg.MachineOperation AS RequiredMachineOperation,
                NULL AS MachinePalletId,
                NULL AS MachinePalletNumber,
                NULL AS MachineForPallet,
                CAST(0 AS BIT) AS IsFixtureActive,
                gu.PlaqueReceveuse_Numro AS RequiredPlaqueModel,
                NULL AS PalletPlaqueModel
            FROM Cedule.dbo.Gabarit_PieceGabarit AS pg
            LEFT JOIN Cedule.dbo.Gabarit_GabaritUsinage AS gu
                ON pg.Gabarit = gu.numero
            WHERE
                RTRIM(LTRIM(pg.Piece)) = :piece_code
                OR UPPER(RTRIM(LTRIM(pg.Piece))) = :piece_code_upper
            """
        )

        if results and (not has_pallet_assignments or missing_plaque):
            logger.debug(
                "Fixture matrix needs enrichment",
                extra={
                    "piece_code": piece_code,
                    "has_fixture_codes": has_fixture_codes,
                    "has_pallet_assignments": has_pallet_assignments,
                    "missing_plaque": missing_plaque,
                },
            )
        elif results:
            logger.debug(
                "Fixture matrix needs enrichment",
                extra={
                    "piece_code": piece_code,
                    "has_fixture_codes": has_fixture_codes,
                    "has_pallet_assignments": has_pallet_assignments,
                    "missing_plaque": missing_plaque,
                },
            )
        else:
            logger.debug("Fixture matrix empty; running fallback", extra={"piece_code": piece_code})
        try:
            with self._engine.connect() as connection:
                fallback_rows = connection.execute(fallback_query, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed fallback query for fixture info", exc_info=exc, extra={"piece_code": piece_code})
            return results

        if not fallback_rows and params.get("piece_prefix"):
            prefix_query = text(
                """
                SELECT
                    pg.Piece AS PieceCode,
                    pg.Gabarit AS FixtureCode,
                    gu.Description AS GabaritDescription,
                    CONCAT(gu.Emplacement_Lettre, '-', gu.Emplacement_Chiffre) AS StorageLocation,
                    pg.MachineOperation AS RequiredMachineOperation,
                    NULL AS MachinePalletId,
                    NULL AS MachinePalletNumber,
                    NULL AS MachineForPallet,
                    CAST(0 AS BIT) AS IsFixtureActive,
                    gu.PlaqueReceveuse_Numro AS RequiredPlaqueModel,
                    NULL AS PalletPlaqueModel
                FROM Cedule.dbo.Gabarit_PieceGabarit AS pg
                LEFT JOIN Cedule.dbo.Gabarit_GabaritUsinage AS gu
                    ON pg.Gabarit = gu.numero
                WHERE
                    RTRIM(LTRIM(pg.Piece)) LIKE :piece_prefix
                """
            )
            try:
                with self._engine.connect() as connection:
                    fallback_rows = connection.execute(prefix_query, params).mappings().all()
                    if fallback_rows:
                        logger.debug(
                            "Fallback by piece prefix",
                            extra={"piece_code": piece_code, "prefix": params["piece_prefix"], "rows": len(fallback_rows)},
                        )
            except SQLAlchemyError as exc:
                logger.error("Failed prefix fallback query for fixture info", exc_info=exc, extra={"piece_code": piece_code})

        plaque_lookup: Dict[str, Optional[str]] = {}
        for row in fallback_rows:
            code = _normalize_code(row.get("FixtureCode"))
            plaque = _normalize_code(row.get("RequiredPlaqueModel"))
            if code and plaque:
                plaque_lookup.setdefault(code, plaque)

        if results and plaque_lookup:
            for item in results:
                if not item.required_plaque_model:
                    key = _normalize_code(item.fixture_code)
                    if key and key in plaque_lookup:
                        item.required_plaque_model = plaque_lookup[key]
            if results and all(row.machine_pallet_id for row in results):
                missing_after = any(row.required_plaque_model is None for row in results)
                if not missing_after:
                    return results

        catalog = self.list_machine_pallets()
        fallback_count = len(fallback_rows)
        if fallback_count:
            logger.debug(
                "Using fallback fixture rows",
                extra={"piece_code": piece_code, "rows": fallback_count},
            )

        for row in fallback_rows:
            fixture_code = _normalize_code(row.get("FixtureCode"))
            required_plaque_model = _normalize_code(row.get("RequiredPlaqueModel")) or fixture_code
            pallet_matches = self._match_pallets(catalog, fixture_code, required_plaque_model)
            if pallet_matches:
                logger.debug(
                    "Matched pallets for fixture",
                    extra={
                        "piece_code": piece_code,
                        "fixture": fixture_code,
                        "required_plaque": required_plaque_model,
                        "pallet_count": len(pallet_matches),
                    },
                )
                for match in pallet_matches:
                    results.append(
                        FixtureMatrixRow(
                            piece_code=row.get("PieceCode", "").strip(),
                            fixture_code=fixture_code,
                            fixture_description=row.get("GabaritDescription"),
                            storage_location=row.get("StorageLocation"),
                            machine_operation=row.get("RequiredMachineOperation"),
                            machine_pallet_id=match.pallet_id,
                            machine_pallet_number=match.pallet_number,
                            machine_id=match.machine_id,
                            is_active=bool(row.get("IsFixtureActive")),
                            required_plaque_model=required_plaque_model or _normalize_code(match.plaque_model),
                            pallet_plaque_model=_normalize_code(match.plaque_model),
                        )
                    )
                continue
            results.append(
                FixtureMatrixRow(
                    piece_code=row.get("PieceCode", "").strip(),
                    fixture_code=fixture_code,
                    fixture_description=row.get("GabaritDescription"),
                    storage_location=row.get("StorageLocation"),
                    machine_operation=row.get("RequiredMachineOperation"),
                    machine_pallet_id=None,
                    machine_pallet_number=None,
                    machine_id=None,
                    is_active=bool(row.get("IsFixtureActive")),
                    required_plaque_model=required_plaque_model,
                    pallet_plaque_model=None,
                )
            )
        return results

    def _query_fixture_matrix_compat(self, piece_code: str, params: dict) -> List[dict]:
        if not self._engine:
            return []
        compat_query = text(
            """
            SELECT
                PieceCode,
                RequiredGabaritNumero AS FixtureCode,
                GabaritDescription,
                CONCAT(FixtureStorageRow, '-', FixtureStorageColumn) AS StorageLocation,
                RequiredMachineOperation,
                MachinePalletId,
                MachinePalletNumber,
                MachineForPallet,
                IsFixtureActive
            FROM Cedule.dbo.Autopilot_FixtureMatrix
            WHERE
                RTRIM(LTRIM(PieceCode)) = :piece_code
                OR UPPER(RTRIM(LTRIM(PieceCode))) = :piece_code_upper
            """
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(compat_query, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error(
                "Failed compatibility query for Autopilot_FixtureMatrix",
                exc_info=exc,
                extra={"piece_code": piece_code},
            )
            return []

        normalized = []
        for row in rows:
            normalized.append(
                {
                    "PieceCode": row.get("PieceCode", "").strip(),
                    "FixtureCode": row.get("FixtureCode"),
                    "GabaritDescription": row.get("GabaritDescription"),
                    "StorageLocation": row.get("StorageLocation"),
                    "RequiredMachineOperation": row.get("RequiredMachineOperation"),
                    "MachinePalletId": row.get("MachinePalletId"),
                    "MachinePalletNumber": row.get("MachinePalletNumber"),
                    "MachineForPallet": row.get("MachineForPallet"),
                    "IsFixtureActive": row.get("IsFixtureActive"),
                    "RequiredPlaqueModel": None,
                    "PalletPlaqueModel": None,
                }
            )
        return normalized

    def _match_pallets(
        self,
        catalog: List[MachinePalletReference],
        fixture_code: Optional[str],
        required_plaque_model: Optional[str],
    ) -> List[MachinePalletReference]:
        fixture_key = _normalize_code(fixture_code)
        plaque_key = _normalize_code(required_plaque_model)
        matches: List[MachinePalletReference] = []
        if not catalog:
            return matches
        for ref in catalog:
            ref_key = _normalize_code(ref.plaque_model) or _normalize_code(ref.description)
            if not ref_key:
                continue
            if ref_key == fixture_key or ref_key == plaque_key:
                matches.append(ref)
        return matches

    def list_machine_pallets(self) -> List[MachinePalletReference]:
        if not self._engine:
            logger.warning("Cedule Autopilot repository not configured; palette list unavailable")
            return []
        if self._pallet_cache is not None:
            return self._pallet_cache

        query = text(
            """
            SELECT
                ID,
                Numero,
                MachinePourPalette,
                PlaqueReceveuse,
                Description
            FROM Cedule.dbo.Gabarit_PaletteUsinage
            ORDER BY ID
            """
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Gabarit_PaletteUsinage", exc_info=exc)
            return []

        pallets: List[MachinePalletReference] = []
        for row in rows:
            pallets.append(
                MachinePalletReference(
                    pallet_id=row.get("ID"),
                    pallet_number=str(row.get("Numero")) if row.get("Numero") is not None else None,
                    machine_id=row.get("MachinePourPalette"),
                    plaque_model=_normalize_code(row.get("PlaqueReceveuse")),
                    description=row.get("Description"),
                )
            )
        self._pallet_cache = pallets
        return pallets
