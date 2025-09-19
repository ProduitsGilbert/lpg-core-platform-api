"""
Standardized API response models for v1
"""
from typing import TypeVar, Generic, Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar('T')

class MetaData(BaseModel):
    """Metadata for API responses"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0"

class PaginationMeta(MetaData):
    """Metadata with pagination info"""
    pagination: Dict[str, int] = Field(default_factory=dict)

class Links(BaseModel):
    """Links for API responses"""
    self: str
    next: Optional[str] = None
    prev: Optional[str] = None
    last: Optional[str] = None

class SingleResponse(BaseModel, Generic[T]):
    """Standard single item response"""
    data: T
    meta: MetaData = Field(default_factory=MetaData)

class CollectionResponse(BaseModel, Generic[T]):
    """Standard collection response"""
    data: List[T]
    meta: PaginationMeta = Field(default_factory=PaginationMeta)
    links: Optional[Links] = None

class ErrorDetail(BaseModel):
    """Error detail for validation errors"""
    field: str
    message: str
    code: str

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: Dict[str, Any]