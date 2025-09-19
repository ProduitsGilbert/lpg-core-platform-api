"""
OCR Service for document text extraction and analysis
"""

from typing import Dict, List, Optional, Any, BinaryIO
from enum import Enum
import json
import base64
from datetime import datetime
import logfire
from pydantic import BaseModel, Field

from app.domain.documents.ocr_document_types import (
    DocumentCategory,
    InvoiceType,
    ShippingDocumentType,
    CustomsDocumentType,
    DocumentTypeDefinition,
    DocumentClassifier,
    DOCUMENT_TYPES
)


class OCRProvider(str, Enum):
    """Available OCR providers"""
    AZURE_COGNITIVE = "azure_cognitive"
    AWS_TEXTRACT = "aws_textract"
    GOOGLE_VISION = "google_vision"
    TESSERACT = "tesseract"


class OCRConfidence(BaseModel):
    """OCR confidence scores"""
    overall: float = Field(ge=0, le=1)
    text_detection: float = Field(ge=0, le=1)
    field_extraction: float = Field(ge=0, le=1)
    document_type: float = Field(ge=0, le=1)


class OCRRequest(BaseModel):
    """OCR processing request"""
    document_type: Optional[str] = None  # Auto-detect if not specified
    provider: OCRProvider = OCRProvider.AZURE_COGNITIVE
    language: str = "en"
    enhance_quality: bool = True
    extract_tables: bool = False
    extract_fields: Optional[List[str]] = None


class OCRResult(BaseModel):
    """OCR processing result"""
    text: str
    confidence: OCRConfidence
    document_type: str
    extracted_data: Dict[str, Any]
    tables: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any]
    processing_time_ms: int
    warnings: List[str] = Field(default_factory=list)


class DocumentValidation(BaseModel):
    """Document validation result"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    confidence_score: float


class OCRService:
    """Service for OCR operations"""
    
    def __init__(self, provider: OCRProvider = OCRProvider.AZURE_COGNITIVE):
        self.provider = provider
        logfire.info(f'Initializing OCR service with provider: {provider}')
    
    async def extract_text(
        self,
        document: BinaryIO,
        document_type: Optional[str] = None,
        extract_tables: bool = False,
        extract_fields: Optional[List[str]] = None
    ) -> OCRResult:
        """
        Extract text and structured data from document
        
        Args:
            document: Binary document file
            document_type: Type of document (auto-detect if None)
            extract_tables: Whether to extract table data
            extract_fields: Specific fields to extract
            
        Returns:
            OCR extraction result
        """
        start_time = datetime.utcnow()
        
        with logfire.span(f'OCR extraction'):
            # Convert document to base64 for processing
            document_data = document.read()
            document_b64 = base64.b64encode(document_data).decode('utf-8')
            
            # Call appropriate OCR provider
            if self.provider == OCRProvider.AZURE_COGNITIVE:
                text, confidence = await self._azure_ocr(document_b64)
            elif self.provider == OCRProvider.AWS_TEXTRACT:
                text, confidence = await self._aws_ocr(document_b64)
            else:
                text, confidence = await self._generic_ocr(document_b64)
            
            # Auto-detect document type if not specified
            if not document_type:
                document_type = DocumentClassifier.identify_document_type(text)
                if document_type:
                    logfire.info(f'Auto-detected document type: {document_type}')
            
            # Perform document type specific extraction
            if document_type and document_type in DOCUMENT_TYPES:
                extracted_data = await self._extract_typed_fields(text, document_type)
            else:
                extracted_data = {}
            
            # Extract tables if requested
            tables = None
            if extract_tables:
                tables = await self._extract_tables(text)
            
            # Extract specific fields if requested
            if extract_fields:
                for field in extract_fields:
                    if field not in extracted_data:
                        value = await self._extract_specific_field(text, field)
                        if value:
                            extracted_data[field] = value
            
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return OCRResult(
                text=text,
                confidence=OCRConfidence(
                    overall=confidence,
                    text_detection=confidence,
                    field_extraction=0.85 if extracted_data else 0.0,
                    document_type=0.9 if document_type else 0.0
                ),
                document_type=document_type or "unknown",
                extracted_data=extracted_data,
                tables=tables,
                metadata={
                    'provider': self.provider.value,
                    'extraction_timestamp': datetime.utcnow().isoformat(),
                    'document_size_bytes': len(document_data)
                },
                processing_time_ms=processing_time
            )
    
    async def _extract_typed_fields(self, text: str, document_type: str) -> Dict[str, Any]:
        """Extract fields based on document type definition"""
        if document_type not in DOCUMENT_TYPES:
            return {}
        
        definition = DOCUMENT_TYPES[document_type]
        fields = {}
        extraction_template = DocumentClassifier.get_extraction_template(document_type)
        
        import re
        
        # Extract fields based on document type definition
        for field_def in definition.required_fields + definition.optional_fields:
            field_name = field_def.name
            
            # Try to find field using main name and aliases
            for alias in [field_name] + field_def.aliases:
                # Create a flexible pattern for the field
                pattern = rf'{re.escape(alias)}[:\s]*([^\n]+)'
                match = re.search(pattern, text, re.IGNORECASE)
                
                if match:
                    value = match.group(1).strip()
                    
                    # Apply type conversion based on data_type
                    if field_def.data_type == "number":
                        # Extract numeric value
                        number_match = re.search(r'[\d,]+\.?\d*', value)
                        if number_match:
                            value = number_match.group().replace(',', '')
                            try:
                                value = float(value)
                            except ValueError:
                                pass
                    elif field_def.data_type == "date":
                        # Extract date pattern
                        date_match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', value)
                        if date_match:
                            value = date_match.group()
                    
                    fields[field_name] = value
                    break
            
            # Special handling for array fields (like line items)
            if field_def.data_type == "array" and field_name not in fields:
                # Try to extract table data
                if field_name == "line_items" or field_name == "items":
                    items = await self._extract_line_items(text)
                    if items:
                        fields[field_name] = items
                elif field_name == "hs_codes":
                    hs_codes = re.findall(r'\b\d{4}\.\d{2}(?:\.\d{2})?\b', text)
                    if hs_codes:
                        fields[field_name] = hs_codes
        
        # Add document type metadata
        fields['_document_type'] = document_type
        fields['_document_category'] = definition.category.value
        
        return fields
    
    async def _extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract line items from document text"""
        items = []
        import re
        
        # Look for table-like patterns with item details
        # Pattern for lines with item number, description, quantity, price
        line_pattern = r'(\d+)\s+([A-Z0-9][^\t\n]{5,50})\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+(?:\.\d{2})?)'        
        matches = re.findall(line_pattern, text)
        
        for match in matches:
            items.append({
                'line_number': match[0],
                'description': match[1].strip(),
                'quantity': float(match[2]),
                'price': float(match[3].replace(',', ''))
            })
        
        return items
    
    async def validate_document(
        self,
        ocr_result: OCRResult,
        strict: bool = False
    ) -> DocumentValidation:
        """
        Validate extracted document against type requirements
        
        Args:
            ocr_result: OCR extraction result
            strict: Whether to enforce all required fields
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        missing_fields = []
        
        if ocr_result.document_type not in DOCUMENT_TYPES:
            return DocumentValidation(
                is_valid=False,
                errors=[f"Unknown document type: {ocr_result.document_type}"],
                confidence_score=0.0
            )
        
        definition = DOCUMENT_TYPES[ocr_result.document_type]
        extracted = ocr_result.extracted_data
        
        # Check required fields
        for field in definition.required_fields:
            if field.name not in extracted or not extracted[field.name]:
                if strict:
                    errors.append(f"Missing required field: {field.name}")
                    missing_fields.append(field.name)
                else:
                    warnings.append(f"Missing field: {field.name}")
                    missing_fields.append(field.name)
            elif field.validation_pattern:
                # Validate field format
                import re
                value = str(extracted[field.name])
                if not re.match(field.validation_pattern, value):
                    errors.append(f"Invalid format for {field.name}: {value}")
        
        # Run custom validation rules
        for rule_name, rule in definition.validation_rules.items():
            # This would require a safe expression evaluator
            # For now, just log that validation rules exist
            logfire.info(f'Validation rule {rule_name}: {rule}')
        
        # Calculate confidence score
        total_fields = len(definition.required_fields)
        found_fields = total_fields - len(missing_fields)
        confidence_score = found_fields / total_fields if total_fields > 0 else 0.0
        
        # Add OCR confidence to overall score
        confidence_score = (confidence_score + ocr_result.confidence.overall) / 2
        
        is_valid = len(errors) == 0 if strict else confidence_score >= 0.7
        
        return DocumentValidation(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields,
            confidence_score=confidence_score
        )
    
    async def _azure_ocr(self, document_b64: str) -> tuple[str, float]:
        """Azure Cognitive Services OCR implementation"""
        # Placeholder for Azure OCR API call
        # In production, this would call Azure Cognitive Services
        logfire.info('Using Azure Cognitive Services for OCR')
        
        # Mock response for now
        text = "Sample extracted text from document"
        confidence = 0.95
        
        return text, confidence
    
    async def _aws_ocr(self, document_b64: str) -> tuple[str, float]:
        """AWS Textract OCR implementation"""
        # Placeholder for AWS Textract API call
        logfire.info('Using AWS Textract for OCR')
        
        # Mock response
        text = "Sample extracted text from document"
        confidence = 0.93
        
        return text, confidence
    
    async def _generic_ocr(self, document_b64: str) -> tuple[str, float]:
        """Generic OCR implementation (Tesseract or other)"""
        # Placeholder for generic OCR
        logfire.info('Using generic OCR provider')
        
        # Mock response
        text = "Sample extracted text from document"
        confidence = 0.85
        
        return text, confidence
    
    async def _extract_tables(self, text: str) -> List[Dict[str, Any]]:
        """Extract table data from text"""
        tables = []
        
        # Simplified table extraction logic
        # In production, this would use more sophisticated table detection
        import re
        
        # Look for patterns that suggest tabular data
        lines = text.split('\n')
        current_table = []
        
        for line in lines:
            # Check if line contains multiple tab or space-separated values
            if '\t' in line or re.search(r'\s{2,}', line):
                values = re.split(r'\t|\s{2,}', line)
                if len(values) > 1:
                    current_table.append(values)
            elif current_table:
                # End of table
                if len(current_table) > 1:
                    tables.append({
                        'headers': current_table[0] if current_table else [],
                        'rows': current_table[1:] if len(current_table) > 1 else []
                    })
                current_table = []
        
        # Don't forget last table
        if current_table and len(current_table) > 1:
            tables.append({
                'headers': current_table[0],
                'rows': current_table[1:]
            })
        
        return tables
    
    async def _extract_specific_field(self, text: str, field_name: str) -> Optional[str]:
        """Extract a specific field from text"""
        import re
        
        # Try common patterns for the field
        patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}',
            'url': r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            'date': r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            'amount': r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
            'percentage': r'\d+(?:\.\d+)?%',
        }
        
        # Check if we have a predefined pattern
        if field_name.lower() in patterns:
            match = re.search(patterns[field_name.lower()], text)
            if match:
                return match.group()
        
        # Try generic field extraction
        pattern = rf'{re.escape(field_name)}[:\s]*([^\n]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    async def analyze_document(
        self,
        ocr_result: OCRResult,
        analysis_type: str = "summary"
    ) -> Dict[str, Any]:
        """
        Perform advanced analysis on extracted document
        
        Args:
            ocr_result: OCR extraction result
            analysis_type: Type of analysis to perform
            
        Returns:
            Analysis results
        """
        with logfire.span(f'Document analysis: {analysis_type}'):
            analysis = {
                'document_type': ocr_result.document_type,
                'confidence': ocr_result.confidence.overall,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if analysis_type == "summary":
                # Generate document summary
                analysis['summary'] = await self._generate_summary(ocr_result)
            elif analysis_type == "compliance":
                # Check compliance requirements
                analysis['compliance'] = await self._check_compliance(ocr_result)
            elif analysis_type == "anomaly":
                # Detect anomalies
                analysis['anomalies'] = await self._detect_anomalies(ocr_result)
            
            return analysis
    
    async def _generate_summary(self, ocr_result: OCRResult) -> Dict[str, Any]:
        """Generate document summary"""
        summary = {
            'field_count': len(ocr_result.extracted_data),
            'has_tables': bool(ocr_result.tables),
            'key_values': {}
        }
        
        # Extract key values for summary
        if ocr_result.document_type in DOCUMENT_TYPES:
            definition = DOCUMENT_TYPES[ocr_result.document_type]
            for field in definition.required_fields[:5]:  # Top 5 required fields
                if field.name in ocr_result.extracted_data:
                    summary['key_values'][field.name] = ocr_result.extracted_data[field.name]
        
        return summary
    
    async def _check_compliance(self, ocr_result: OCRResult) -> Dict[str, Any]:
        """Check document compliance"""
        validation = await self.validate_document(ocr_result, strict=True)
        
        return {
            'is_compliant': validation.is_valid,
            'missing_fields': validation.missing_fields,
            'errors': validation.errors,
            'confidence': validation.confidence_score
        }
    
    async def _detect_anomalies(self, ocr_result: OCRResult) -> List[Dict[str, Any]]:
        """Detect anomalies in document"""
        anomalies = []
        
        # Check for suspicious patterns
        if ocr_result.confidence.overall < 0.5:
            anomalies.append({
                'type': 'low_confidence',
                'severity': 'high',
                'description': 'Document has very low OCR confidence'
            })
        
        # Check for missing critical fields
        if ocr_result.document_type in DOCUMENT_TYPES:
            definition = DOCUMENT_TYPES[ocr_result.document_type]
            critical_missing = []
            
            for field in definition.required_fields:
                if field.name not in ocr_result.extracted_data:
                    critical_missing.append(field.name)
            
            if critical_missing:
                anomalies.append({
                    'type': 'missing_critical_fields',
                    'severity': 'medium',
                    'description': f'Missing fields: {", ".join(critical_missing)}'
                })
        
        return anomalies