"""
AI client adapter for intelligent processing.

This module provides integration with AI services (OpenAI and local agents)
for intelligent document processing, data extraction, and decision support.
"""

import json
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import logging

logger = logging.getLogger(__name__)

from app.settings import settings
from app.errors import ExternalServiceException
from app.ports import AIClientProtocol


class AIProvider(str, Enum):
    """AI service provider enumeration."""
    OPENAI = "openai"
    LOCAL_AGENT = "local_agent"


class AIClient(AIClientProtocol):
    """
    AI service client for intelligent processing.
    
    Supports both OpenAI API and local AI agent services.
    """
    
    def __init__(
        self,
        openai_key: Optional[str] = None,
        local_agent_url: Optional[str] = None
    ):
        """
        Initialize AI client.
        
        Args:
            openai_key: Override OpenAI API key from settings
            local_agent_url: Override local agent URL from settings
        """
        self.openai_key = openai_key or settings.openai_api_key
        self.local_agent_url = local_agent_url or settings.local_agent_base_url
        self.openai_model = settings.openai_model
        self._enabled = settings.enable_ai_assistance
        
        # Initialize OpenAI client if configured
        self.openai_client = None
        if self._enabled and self.openai_key:
            self.openai_client = httpx.Client(
                base_url="https://api.openai.com/v1",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                timeout=settings.request_timeout
            )
        
        # Initialize local agent client if configured
        self.local_client = None
        if self._enabled and self.local_agent_url:
            self.local_client = httpx.Client(
                base_url=self.local_agent_url,
                headers={"Content-Type": "application/json"},
                timeout=settings.request_timeout
            )
    
    def __del__(self):
        """Clean up HTTP clients on deletion."""
        if hasattr(self, 'openai_client') and self.openai_client:
            self.openai_client.close()
        if hasattr(self, 'local_client') and self.local_client:
            self.local_client.close()
    
    @property
    def enabled(self) -> bool:
        """Check if AI assistance is enabled."""
        return self._enabled
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type(httpx.TimeoutException)
    )
    def analyze_purchase_order(
        self,
        po_data: Dict[str, Any],
        analysis_type: str = "risk"
    ) -> Dict[str, Any]:
        """
        Analyze a purchase order using AI.
        
        Args:
            po_data: Purchase order data to analyze
            analysis_type: Type of analysis (risk, optimization, compliance)
        
        Returns:
            Analysis results including:
            - risk_score: Risk assessment (0-100)
            - recommendations: List of recommendations
            - issues: Identified issues
            - confidence: Confidence score
        
        Raises:
            ExternalServiceException: If AI service fails
        """
        if not self.enabled:
            # Return stub analysis for development
            return {
                "risk_score": 25,
                "recommendations": [
                    "Consider negotiating better payment terms",
                    "Verify vendor compliance certificates"
                ],
                "issues": [],
                "confidence": 0.85,
                "provider": "stub"
            }
        
        with logfire.span(
            "AI analyze_purchase_order",
            po_id=po_data.get("po_id"),
            analysis_type=analysis_type
        ):
            prompt = self._build_po_analysis_prompt(po_data, analysis_type)
            
            # Try OpenAI first, fallback to local agent
            if self.openai_client:
                try:
                    return self._analyze_with_openai(prompt, "po_analysis")
                except Exception as e:
                    logfire.warning(f"OpenAI analysis failed, trying local agent: {e}")
            
            if self.local_client:
                return self._analyze_with_local_agent(prompt, "po_analysis")
            
            raise ExternalServiceException(
                "AI",
                "No AI service available for analysis"
            )
    
    def _build_po_analysis_prompt(
        self,
        po_data: Dict[str, Any],
        analysis_type: str
    ) -> str:
        """Build prompt for PO analysis."""
        po_summary = json.dumps(po_data, indent=2, default=str)
        
        prompts = {
            "risk": f"""Analyze this purchase order for potential risks:
{po_summary}

Identify:
1. Financial risks (pricing, payment terms)
2. Delivery risks (dates, quantities)
3. Vendor risks (reliability, compliance)
4. Operational risks

Provide a risk score (0-100) and specific recommendations.""",
            
            "optimization": f"""Analyze this purchase order for optimization opportunities:
{po_summary}

Identify:
1. Cost saving opportunities
2. Process improvements
3. Better timing strategies
4. Quantity optimization

Provide specific, actionable recommendations.""",
            
            "compliance": f"""Review this purchase order for compliance:
{po_summary}

Check for:
1. Policy compliance
2. Budget alignment
3. Approval requirements
4. Documentation completeness

Identify any compliance issues and required actions."""
        }
        
        return prompts.get(analysis_type, prompts["risk"])
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type(httpx.TimeoutException)
    )
    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from unstructured text using AI.
        
        Args:
            text: Unstructured text to process
            schema: Expected output schema
            context: Additional context for extraction
        
        Returns:
            Structured data matching the schema
        
        Raises:
            ExternalServiceException: If AI service fails
        """
        if not self.enabled:
            # Return stub data for development
            return schema
        
        with logfire.span(
            "AI extract_structured_data",
            text_length=len(text),
            schema_fields=list(schema.keys())
        ):
            prompt = f"""Extract structured data from the following text according to the schema.

Text:
{text}

Expected Schema:
{json.dumps(schema, indent=2)}

{f'Context: {context}' if context else ''}

Return only valid JSON matching the schema."""
            
            if self.openai_client:
                try:
                    return self._analyze_with_openai(prompt, "extraction")
                except Exception as e:
                    logfire.warning(f"OpenAI extraction failed: {e}")
            
            if self.local_client:
                return self._analyze_with_local_agent(prompt, "extraction")
            
            raise ExternalServiceException(
                "AI",
                "No AI service available for extraction"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type(httpx.TimeoutException)
    )
    def suggest_corrections(
        self,
        original_data: Dict[str, Any],
        validation_errors: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Suggest corrections for validation errors using AI.
        
        Args:
            original_data: Data that failed validation
            validation_errors: List of validation error messages
            context: Additional context (e.g., historical data)
        
        Returns:
            Suggested corrections with explanations
        
        Raises:
            ExternalServiceException: If AI service fails
        """
        if not self.enabled:
            return {
                "corrections": {},
                "explanations": [],
                "confidence": 0.0
            }
        
        with logfire.span(
            "AI suggest_corrections",
            error_count=len(validation_errors)
        ):
            prompt = f"""Suggest corrections for the following validation errors:

Original Data:
{json.dumps(original_data, indent=2, default=str)}

Validation Errors:
{chr(10).join(f'- {error}' for error in validation_errors)}

{f'Context: {json.dumps(context, indent=2)}' if context else ''}

Provide specific corrections for each field with explanations."""
            
            if self.openai_client:
                try:
                    return self._analyze_with_openai(prompt, "corrections")
                except Exception as e:
                    logfire.warning(f"OpenAI correction suggestion failed: {e}")
            
            if self.local_client:
                return self._analyze_with_local_agent(prompt, "corrections")
            
            return {
                "corrections": {},
                "explanations": ["AI service unavailable"],
                "confidence": 0.0
            }
    
    def _analyze_with_openai(
        self,
        prompt: str,
        task_type: str
    ) -> Dict[str, Any]:
        """
        Perform analysis using OpenAI API.
        
        Args:
            prompt: Analysis prompt
            task_type: Type of task for logging
        
        Returns:
            Analysis results
        
        Raises:
            ExternalServiceException: If OpenAI API fails
        """
        if not self.openai_client:
            raise ExternalServiceException("AI", "OpenAI client not configured")
        
        try:
            response = self.openai_client.post(
                "/chat/completions",
                json={
                    "model": self.openai_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert ERP analyst specializing in purchasing and supply chain optimization. Provide structured, actionable insights."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"} if task_type in ["extraction", "corrections"] else None
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response if expected
            if task_type in ["extraction", "corrections"]:
                try:
                    parsed = json.loads(content)
                    parsed["provider"] = "openai"
                    return parsed
                except json.JSONDecodeError:
                    logfire.error(f"Failed to parse OpenAI JSON response: {content}")
                    raise ExternalServiceException("AI", "Invalid JSON response from OpenAI")
            
            # For analysis tasks, structure the response
            return self._structure_analysis_response(content, "openai")
            
        except httpx.HTTPStatusError as e:
            logfire.error(f"OpenAI API error: {e.response.status_code}")
            raise ExternalServiceException(
                "AI",
                f"OpenAI API error: {e.response.status_code}",
                context={"status_code": e.response.status_code}
            )
        except httpx.TimeoutException:
            raise ExternalServiceException("AI", "OpenAI API timeout")
        except Exception as e:
            logfire.error(f"OpenAI analysis error: {str(e)}")
            raise ExternalServiceException("AI", f"OpenAI error: {str(e)}")
    
    def _analyze_with_local_agent(
        self,
        prompt: str,
        task_type: str
    ) -> Dict[str, Any]:
        """
        Perform analysis using local AI agent.
        
        Args:
            prompt: Analysis prompt
            task_type: Type of task for logging
        
        Returns:
            Analysis results
        
        Raises:
            ExternalServiceException: If local agent fails
        """
        if not self.local_client:
            raise ExternalServiceException("AI", "Local agent not configured")
        
        try:
            response = self.local_client.post(
                "/analyze",
                json={
                    "prompt": prompt,
                    "task_type": task_type
                }
            )
            response.raise_for_status()
            
            result = response.json()
            result["provider"] = "local_agent"
            return result
            
        except httpx.HTTPStatusError as e:
            logfire.error(f"Local agent error: {e.response.status_code}")
            raise ExternalServiceException(
                "AI",
                f"Local agent error: {e.response.status_code}",
                context={"status_code": e.response.status_code}
            )
        except httpx.TimeoutException:
            raise ExternalServiceException("AI", "Local agent timeout")
        except Exception as e:
            logfire.error(f"Local agent error: {str(e)}")
            raise ExternalServiceException("AI", f"Local agent error: {str(e)}")
    
    def _structure_analysis_response(
        self,
        content: str,
        provider: str
    ) -> Dict[str, Any]:
        """
        Structure free-form analysis response into consistent format.
        
        Args:
            content: Raw analysis content
            provider: AI provider used
        
        Returns:
            Structured analysis response
        """
        # Simple parsing - in production, use more sophisticated NLP
        lines = content.strip().split('\n')
        
        recommendations = []
        issues = []
        risk_score = 50  # Default medium risk
        
        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('•'):
                if 'risk' in line.lower() or 'issue' in line.lower():
                    issues.append(line.lstrip('-•').strip())
                else:
                    recommendations.append(line.lstrip('-•').strip())
            elif 'score' in line.lower() and any(char.isdigit() for char in line):
                # Try to extract risk score
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    risk_score = min(100, max(0, int(numbers[0])))
        
        return {
            "risk_score": risk_score,
            "recommendations": recommendations or ["No specific recommendations"],
            "issues": issues,
            "confidence": 0.75,  # Default confidence
            "provider": provider,
            "raw_analysis": content
        }
    
    def health_check(self) -> Dict[str, bool]:
        """
        Check health of available AI services.
        
        Returns:
            Dictionary with service health status
        """
        health = {
            "openai": False,
            "local_agent": False,
            "enabled": self.enabled
        }
        
        if not self.enabled:
            return health
        
        # Check OpenAI
        if self.openai_client:
            try:
                response = self.openai_client.get("/models", timeout=5)
                health["openai"] = response.status_code == 200
            except Exception as e:
                logfire.warning(f"OpenAI health check failed: {e}")
        
        # Check local agent
        if self.local_client:
            try:
                response = self.local_client.get("/health", timeout=5)
                health["local_agent"] = response.status_code == 200
            except Exception as e:
                logfire.warning(f"Local agent health check failed: {e}")
        
        return health