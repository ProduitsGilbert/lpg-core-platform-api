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
import logfire

from app.settings import settings
from app.errors import ExternalServiceException
from app.ports import AIClientProtocol


class AIProvider(str, Enum):
    """AI service provider enumeration."""
    XAI = "xai"
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
        self.grok_key = settings.grok_api_key
        self.local_agent_url = local_agent_url or settings.local_agent_base_url
        self.openai_model = settings.openai_model
        self.xai_model = settings.xai_model
        self.xai_reasoning_effort = settings.xai_reasoning_effort
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

        # Initialize xAI client if configured.
        self.xai_client = None
        if self._enabled and self.grok_key:
            xai_timeout = max(settings.request_timeout, settings.xai_timeout_seconds)
            self.xai_client = httpx.Client(
                base_url="https://api.x.ai/v1",
                headers={
                    "Authorization": f"Bearer {self.grok_key}",
                    "Content-Type": "application/json",
                },
                timeout=xai_timeout,
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
        if hasattr(self, 'xai_client') and self.xai_client:
            self.xai_client.close()
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
            
            # Prefer xAI Grok for extraction/reasoning when configured.
            if self.xai_client:
                try:
                    return self._analyze_with_xai(prompt, "po_analysis")
                except Exception as e:
                    logger.warning("xAI analysis failed, trying OpenAI/local fallback: %s", e)

            # Try OpenAI first, fallback to local agent
            if self.openai_client:
                try:
                    return self._analyze_with_openai(prompt, "po_analysis")
                except Exception as e:
                    logger.warning("OpenAI analysis failed, trying local agent: %s", e)
            
            if self.local_client:
                return self._analyze_with_local_agent(prompt, "po_analysis")
            
            raise ExternalServiceException(
                detail="No AI service available for analysis",
                service="AI",
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
            
            if self.xai_client:
                try:
                    return self._analyze_with_xai(prompt, "extraction")
                except Exception as e:
                    logger.warning("xAI structured extraction failed, trying OpenAI/local fallback: %s", e)

            if self.openai_client:
                try:
                    return self._analyze_with_openai(prompt, "extraction")
                except Exception as e:
                    logger.warning("OpenAI extraction failed: %s", e)
            
            if self.local_client:
                return self._analyze_with_local_agent(prompt, "extraction")
            
            raise ExternalServiceException(
                detail="No AI service available for extraction",
                service="AI",
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
            
            if self.xai_client:
                try:
                    return self._analyze_with_xai(prompt, "corrections")
                except Exception as e:
                    logger.warning("xAI correction suggestion failed, trying OpenAI/local fallback: %s", e)

            if self.openai_client:
                try:
                    return self._analyze_with_openai(prompt, "corrections")
                except Exception as e:
                    logger.warning("OpenAI correction suggestion failed: %s", e)
            
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
            raise ExternalServiceException(detail="OpenAI client not configured", service="AI")
        
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
                    raise ExternalServiceException(detail="Invalid JSON response from OpenAI", service="AI")
            
            # For analysis tasks, structure the response
            return self._structure_analysis_response(content, "openai")
            
        except httpx.HTTPStatusError as e:
            logfire.error(f"OpenAI API error: {e.response.status_code}")
            raise ExternalServiceException(
                detail=f"OpenAI API error: {e.response.status_code}",
                service="AI",
            )
        except httpx.TimeoutException:
            raise ExternalServiceException(detail="OpenAI API timeout", service="AI")
        except Exception as e:
            logfire.error(f"OpenAI analysis error: {str(e)}")
            raise ExternalServiceException(detail=f"OpenAI error: {str(e)}", service="AI")

    def _analyze_with_xai(
        self,
        prompt: str,
        task_type: str,
    ) -> Dict[str, Any]:
        """
        Perform analysis using xAI Grok chat completions.
        """
        if not self.xai_client:
            raise ExternalServiceException(detail="xAI client not configured", service="AI")

        try:
            payload: Dict[str, Any] = {
                "model": self.xai_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert manufacturing estimator and technical drawing analyst. "
                            "Return high-quality structured outputs that strictly follow schema constraints."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0.1,
            }
            if self.xai_reasoning_effort:
                payload["reasoning_effort"] = self.xai_reasoning_effort
            if task_type in {"extraction", "corrections"}:
                payload["response_format"] = {"type": "json_object"}

            response = self.xai_client.post("/chat/completions", json=payload)
            applied_reasoning_effort = payload.get("reasoning_effort")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as first_err:
                body = ""
                try:
                    body = first_err.response.text or ""
                except Exception:
                    body = ""
                body_lower = body.lower()
                if (
                    payload.get("reasoning_effort")
                    and first_err.response.status_code == 400
                    and "does not support parameter reasoningeffort" in body_lower
                ):
                    logger.warning(
                        "xAI model %s rejected reasoning_effort; retrying without reasoning_effort",
                        self.xai_model,
                    )
                    fallback_payload = dict(payload)
                    fallback_payload.pop("reasoning_effort", None)
                    response = self.xai_client.post("/chat/completions", json=fallback_payload)
                    response.raise_for_status()
                    applied_reasoning_effort = None
                else:
                    raise

            data = response.json()
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
            if not isinstance(content, str):
                raise ExternalServiceException(detail="xAI returned empty response content", service="AI")

            if task_type in {"extraction", "corrections"}:
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        parsed["provider"] = "xai"
                        parsed["model"] = self.xai_model
                        parsed["reasoning_effort"] = applied_reasoning_effort
                        return parsed
                    raise ExternalServiceException(detail="xAI returned non-object JSON", service="AI")
                except json.JSONDecodeError as exc:
                    logfire.error(f"Failed to parse xAI JSON response: {content}")
                    raise ExternalServiceException(detail="Invalid JSON response from xAI", service="AI") from exc

            return self._structure_analysis_response(content, "xai")
        except httpx.HTTPStatusError as e:
            logfire.error(f"xAI API error: {e.response.status_code}")
            response_text = ""
            try:
                response_text = (e.response.text or "")[:400]
            except Exception:
                response_text = ""
            logger.error("xAI API error body: %s", response_text)
            if task_type in {"extraction", "corrections"} and self.openai_client:
                logger.warning("Retrying extraction with OpenAI fallback after xAI 4xx/5xx")
                return self._analyze_with_openai(prompt, task_type)
            raise ExternalServiceException(
                detail=f"xAI API error: {e.response.status_code}",
                service="AI",
            )
        except httpx.TimeoutException:
            if task_type in {"extraction", "corrections"} and self.openai_client:
                logger.warning("xAI timeout, retrying extraction with OpenAI fallback")
                return self._analyze_with_openai(prompt, task_type)
            raise ExternalServiceException(detail="xAI API timeout", service="AI")
        except Exception as e:
            logfire.error(f"xAI analysis error: {str(e)}")
            if task_type in {"extraction", "corrections"} and self.openai_client:
                logger.warning("xAI generic error, retrying extraction with OpenAI fallback: %s", e)
                return self._analyze_with_openai(prompt, task_type)
            raise ExternalServiceException(detail=f"xAI error: {str(e)}", service="AI")
    
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
            raise ExternalServiceException(detail="Local agent not configured", service="AI")
        
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
                detail=f"Local agent error: {e.response.status_code}",
                service="AI",
            )
        except httpx.TimeoutException:
            raise ExternalServiceException(detail="Local agent timeout", service="AI")
        except Exception as e:
            logfire.error(f"Local agent error: {str(e)}")
            raise ExternalServiceException(detail=f"Local agent error: {str(e)}", service="AI")
    
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
            "xai": False,
            "openai": False,
            "local_agent": False,
            "enabled": self.enabled
        }
        
        if not self.enabled:
            return health
        
        if self.xai_client:
            try:
                response = self.xai_client.get("/models", timeout=10)
                health["xai"] = response.status_code == 200
            except Exception as e:
                logger.warning("xAI health check failed: %s", e)

        # Check OpenAI
        if self.openai_client:
            try:
                response = self.openai_client.get("/models", timeout=5)
                health["openai"] = response.status_code == 200
            except Exception as e:
                logger.warning("OpenAI health check failed: %s", e)
        
        # Check local agent
        if self.local_client:
            try:
                response = self.local_client.get("/health", timeout=5)
                health["local_agent"] = response.status_code == 200
            except Exception as e:
                logger.warning("Local agent health check failed: %s", e)
        
        return health
