from typing import List, Optional
from datetime import datetime
import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.integrations.cedule_repository import get_cedule_engine
from app.domain.finance.models import ManualEntry, ManualEntryCreate, ManualEntryUpdate, CurrencyCode, TransactionType, RecurrenceFrequency
from app.errors import DatabaseError

logger = logging.getLogger(__name__)

class FinanceRepository:
    """Repository for manual cashflow entries in Cedule database."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def get_all_entries(self) -> List[ManualEntry]:
        """Retrieve all manual entries (both one-time and periodic)."""
        if not self._engine:
            return []

        query = text("""
            SELECT 
                id, description, amount, currency_code, transaction_type,
                transaction_date, is_periodic, recurrence_frequency,
                recurrence_interval, recurrence_count, recurrence_end_date,
                created_at, updated_at
            FROM [Cedule].[dbo].[Finance_Cashflow]
            ORDER BY transaction_date DESC, created_at DESC
        """)

        try:
            with self._engine.connect() as connection:
                result = connection.execute(query).mappings().all()
                return [self._map_row_to_model(row) for row in result]
        except SQLAlchemyError as exc:
            logger.error("Failed to fetch finance entries", exc_info=exc)
            raise DatabaseError("Unable to fetch finance entries") from exc

    def get_entry_by_id(self, entry_id: int) -> Optional[ManualEntry]:
        if not self._engine:
            return None

        query = text("""
            SELECT * FROM [Cedule].[dbo].[Finance_Cashflow] WHERE id = :id
        """)

        try:
            with self._engine.connect() as connection:
                row = connection.execute(query, {"id": entry_id}).mappings().first()
                if row:
                    return self._map_row_to_model(row)
                return None
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch finance entry {entry_id}", exc_info=exc)
            raise DatabaseError(f"Unable to fetch finance entry {entry_id}") from exc

    def create_entry(self, entry: ManualEntryCreate) -> ManualEntry:
        if not self._engine:
            raise DatabaseError("Database not configured")

        query = text("""
            INSERT INTO [Cedule].[dbo].[Finance_Cashflow] (
                description, amount, currency_code, transaction_type,
                transaction_date, is_periodic, recurrence_frequency,
                recurrence_interval, recurrence_count, recurrence_end_date
            )
            OUTPUT 
                INSERTED.id, INSERTED.created_at, INSERTED.updated_at
            VALUES (
                :description, :amount, :currency_code, :transaction_type,
                :transaction_date, :is_periodic, :recurrence_frequency,
                :recurrence_interval, :recurrence_count, :recurrence_end_date
            )
        """)

        params = entry.model_dump()
        # Convert enums to values
        params['currency_code'] = params['currency_code'].value
        params['transaction_type'] = params['transaction_type'].value
        if params.get('recurrence_frequency'):
            params['recurrence_frequency'] = params['recurrence_frequency'].value

        try:
            with self._engine.begin() as connection:
                row = connection.execute(query, params).mappings().first()
                
                # Construct the full model
                created_entry = ManualEntry(
                    id=row['id'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    **entry.model_dump()
                )
                return created_entry
        except SQLAlchemyError as exc:
            logger.error("Failed to create finance entry", exc_info=exc)
            raise DatabaseError("Unable to create finance entry") from exc

    def update_entry(self, entry_id: int, updates: ManualEntryUpdate) -> Optional[ManualEntry]:
        if not self._engine:
            raise DatabaseError("Database not configured")

        # Get existing first to ensure it exists
        current = self.get_entry_by_id(entry_id)
        if not current:
            return None

        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            return current

        set_clauses = []
        params = {"id": entry_id, "updated_at": datetime.utcnow()}
        
        for key, value in update_data.items():
            set_clauses.append(f"{key} = :{key}")
            # Handle enums
            if hasattr(value, 'value'):
                params[key] = value.value
            else:
                params[key] = value

        set_clauses.append("updated_at = :updated_at")
        
        query_str = f"""
            UPDATE [Cedule].[dbo].[Finance_Cashflow]
            SET {', '.join(set_clauses)}
            WHERE id = :id
        """
        
        try:
            with self._engine.begin() as connection:
                connection.execute(text(query_str), params)
                
            return self.get_entry_by_id(entry_id)
        except SQLAlchemyError as exc:
            logger.error(f"Failed to update finance entry {entry_id}", exc_info=exc)
            raise DatabaseError(f"Unable to update finance entry {entry_id}") from exc

    def delete_entry(self, entry_id: int) -> bool:
        if not self._engine:
            raise DatabaseError("Database not configured")

        query = text("DELETE FROM [Cedule].[dbo].[Finance_Cashflow] WHERE id = :id")
        
        try:
            with self._engine.begin() as connection:
                result = connection.execute(query, {"id": entry_id})
                return result.rowcount > 0
        except SQLAlchemyError as exc:
            logger.error(f"Failed to delete finance entry {entry_id}", exc_info=exc)
            raise DatabaseError(f"Unable to delete finance entry {entry_id}") from exc

    def _map_row_to_model(self, row) -> ManualEntry:
        return ManualEntry(
            id=row['id'],
            description=row['description'],
            amount=row['amount'],
            currency_code=CurrencyCode(row['currency_code']),
            transaction_type=TransactionType(row['transaction_type']),
            transaction_date=row['transaction_date'],
            is_periodic=row['is_periodic'],
            recurrence_frequency=RecurrenceFrequency(row['recurrence_frequency']) if row['recurrence_frequency'] else None,
            recurrence_interval=row['recurrence_interval'],
            recurrence_count=row['recurrence_count'],
            recurrence_end_date=row['recurrence_end_date'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )








