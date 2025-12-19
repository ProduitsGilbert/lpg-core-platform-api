from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class TransactionType(str, Enum):
    DEPOSIT = "Deposit"
    PAYMENT = "Payment"

class CurrencyCode(str, Enum):
    CAD = "CAD"
    USD = "USD"
    EUR = "EUR"

class RecurrenceFrequency(str, Enum):
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    YEARLY = "Yearly"

class CashflowSource(str, Enum):
    ERP_SALES = "ERP_Sales"
    ERP_PURCHASE = "ERP_Purchase"
    ERP_JOB = "ERP_Job"
    MANUAL = "Manual"
    MANUAL_PERIODIC = "Manual_Periodic"

class CashflowEntry(BaseModel):
    """
    Unified model for a single cashflow event (one-time).
    Used for calculation and aggregation.
    """
    date: date
    amount: Decimal
    currency: CurrencyCode
    transaction_type: TransactionType
    description: str
    source: CashflowSource
    reference_id: Optional[str] = None # Invoice No, PO No, or Manual Entry ID

class ManualEntryBase(BaseModel):
    description: str
    amount: Decimal
    currency_code: CurrencyCode
    transaction_type: TransactionType
    
    # One-time
    transaction_date: Optional[date] = None
    
    # Periodic
    is_periodic: bool = False
    recurrence_frequency: Optional[RecurrenceFrequency] = None
    recurrence_interval: Optional[int] = None
    recurrence_count: Optional[int] = None
    recurrence_end_date: Optional[date] = None

class ManualEntryCreate(ManualEntryBase):
    pass

class ManualEntryUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency_code: Optional[CurrencyCode] = None
    transaction_type: Optional[TransactionType] = None
    transaction_date: Optional[date] = None
    is_periodic: Optional[bool] = None
    recurrence_frequency: Optional[RecurrenceFrequency] = None
    recurrence_interval: Optional[int] = None
    recurrence_count: Optional[int] = None
    recurrence_end_date: Optional[date] = None

class ManualEntry(ManualEntryBase):
    """
    Representation of a row in Finance_Cashflow table.
    """
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DailyCashflow(BaseModel):
    date: date
    currency: CurrencyCode
    total_deposit: Decimal = Decimal("0")
    total_payment: Decimal = Decimal("0")
    net_flow: Decimal = Decimal("0")
    entries: List[CashflowEntry] = []

class CashflowProjection(BaseModel):
    start_date: date
    end_date: date
    daily_flows: List[DailyCashflow]

