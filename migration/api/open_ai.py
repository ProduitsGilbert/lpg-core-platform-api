"""
OpenAI integration client
Streamlined version with only essential functions needed by V2 processors
Based on migrations/chat_GPT.py
"""

import asyncio
import logging
from typing import Any

import backoff
import tiktoken
from openai import AsyncOpenAI

from ..config import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Streamlined OpenAI client
    Only includes functions actually used by V2 processors
    """

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.client = None

        # Constants from V1
        self.embedding_model = "text-embedding-ada-002"
        self.embedding_ctx_length = 15000
        self.embedding_encoding = "cl100k_base"
        self.default_model = "gpt-5-2025-08-07"  # Best available model

        if not self.api_key:
            logger.warning("OpenAI API key not configured. OpenAI integration disabled.")
        else:
            # Initialize client immediately if API key is available
            self.client = AsyncOpenAI(api_key=self.api_key)

    async def __aenter__(self):
        """Async context manager entry"""
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.close()

    def _truncate_text_tokens(self, text: str, max_tokens: int = None) -> str:
        """
        Truncate text to max tokens
        Migrated from chat_GPT.py truncate_text_tokens()
        """
        if max_tokens is None:
            max_tokens = self.embedding_ctx_length

        try:
            encoding = tiktoken.get_encoding(self.embedding_encoding)
            tokens = encoding.encode(text)
            if len(tokens) <= max_tokens:
                return text

            truncated_tokens = tokens[:max_tokens]
            return encoding.decode(truncated_tokens)
        except Exception as e:
            logger.warning(f"Error truncating text: {e}")
            return text[: max_tokens * 4]  # Rough character estimate

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def _safe_chat_completion(self, **kwargs) -> Any | None:
        """
        Safe chat completion with retry
        Migrated from chat_GPT.py safe_chat_completion()
        """
        if not self.client:
            logger.warning("OpenAI client not initialized. Returning dummy response.")
            return None

        try:
            return await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def get_text_response_with_model(self, user_prompt: str, model: str) -> str:
        """
        Get text response from OpenAI with specific model
        Used for complex documents that need reasoning capabilities
        """
        try:
            response = await self._safe_chat_completion(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant that extracts data from documents accurately.",
                    },
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_completion_tokens=2000,  # Use max_completion_tokens for new models
            )

            if response and response.choices:
                return response.choices[0].message.content
            return ""

        except Exception as e:
            logger.error(f"Error getting text response with model {model}: {e}")
            return ""

    async def get_text_response(self, user_prompt: str) -> str:
        """
        Get text response from OpenAI
        Used by: SoumissionProcessor
        Migrated from chat_GPT.py get_text_response()
        """
        try:
            system_prompt = "You are a helpful assistant."

            response = await self._safe_chat_completion(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_completion_tokens=500,  # Use max_completion_tokens for new models
                temperature=0.1,
                top_p=1,
                frequency_penalty=0.5,
                presence_penalty=0,
            )

            if response and response.choices:
                return response.choices[0].message.content.strip()
            else:
                return "Error: No response from OpenAI"

        except Exception as e:
            logger.error(f"Error getting text response: {e}")
            return f"Error generating response: {e}"

    async def completion(self, user_prompt: str) -> str:
        """
        General completion function
        Used by: Various processors
        Migrated from chat_GPT.py completion()
        """
        try:
            response = await self._safe_chat_completion(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": user_prompt},
                ],
            )

            if response and response.choices:
                result = response.choices[0].message.content
                logger.info(f"OpenAI completion response: {result[:100]}...")
                return result
            else:
                return "Error: No response from OpenAI"

        except Exception as e:
            logger.error(f"Error in completion: {e}")
            return f"Error: {e}"

    async def translate_to_english(self, text: str) -> str:
        """
        Translate French text to English
        Used by: Various processors
        Migrated from chat_GPT.py Translate_to_English()
        """
        try:
            system_prompt = "You are a translation assistant. Please translate this french text to english."

            response = await self._safe_chat_completion(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                max_completion_tokens=500,  # Use max_completion_tokens for new models
                temperature=0.1,
                top_p=1,
                frequency_penalty=0.5,
                presence_penalty=0,
            )

            if response and response.choices:
                return response.choices[0].message.content.strip()
            else:
                return text  # Return original if translation fails

        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return text

    async def format_date(self, date_to_format: str) -> str:
        """
        Format date using OpenAI with business day calculations for shipping
        Handles relative dates and adds 2 business days for warehouse processing
        """
        try:
            from datetime import datetime

            today = datetime.today()
            today_str = today.strftime("%Y-%m-%d")
            weekday = today.strftime("%A")  # e.g., "Thursday"

            prompt = (
                f"Convert this supplier delivery text to an expected receipt date: {date_to_format}\n\n"
                f"IMPORTANT RULES:\n"
                f"1. Add 2 BUSINESS DAYS for shipping/warehouse processing to any date\n"
                f"2. Business days are Monday-Friday only (skip weekends)\n"
                f"3. Your response must be EXACTLY in format: yyyy-MM-dd\n"
                f"4. Return ONLY the date, no other text\n\n"
                f"TODAY'S CONTEXT:\n"
                f"- Today is {weekday}, {today_str}\n"
                f"- Current time for reference\n\n"
                f"EXAMPLES (assuming today is {today_str}):\n"
                f"- 'shipped yesterday' → calculate yesterday's date + 2 business days\n"
                f"- 'will ship Friday' → find next Friday + 2 business days\n"
                f"- 'will ship this Friday' → this coming Friday + 2 business days\n"
                f"- 'you'll have it Monday' → that Monday (no additional days needed, already includes transit)\n"
                f"- 'ships tomorrow' → tomorrow + 2 business days\n"
                f"- 'shipped today' → today + 2 business days\n"
                f"- 'in stock' or 'stock' → today + 2 business days\n"
                f"- '2-3 jours' → 3 days + 2 business days\n"
                f"- '8/28/25' → 2025-08-28 + 2 business days\n"
                f"- 'next week' → Monday of next week + 2 business days\n"
                f"- 'Expédier 2025-08-18' → 2025-08-18 + 2 business days (French 'will ship' + transit)\n"
                f"- 'Expédier 2025-08-25' → 2025-08-25 + 2 business days\n"
                f"- 'expédié le 2025-08-15' → 2025-08-15 + 2 business days (French 'shipped' + transit)\n"
                f"- 'Sera expédié 2025-09-01' → 2025-09-01 + 2 business days\n"
                f"- 'Livraison 2025-09-05' → 2025-09-05 (already includes delivery, no extra days)\n\n"
                f"FRENCH SHIPPING TERMS:\n"
                f"- 'Expédier' / 'Expédition' = 'to ship' / 'shipping' → add 2 business days\n"
                f"- 'Sera expédié' = 'will be shipped' → add 2 business days\n"
                f"- 'Expédié' = 'shipped' → add 2 business days\n"
                f"- 'Livraison' / 'Livré' = 'delivery' / 'delivered' → no extra days\n"
                f"- 'Réception' = 'receipt' → no extra days\n\n"
                f"REMEMBER:\n"
                f"- If text says 'you'll have it', 'receive by', 'livraison', don't add extra days\n"
                f"- If text says 'ship', 'shipped', 'expédier', 'expédié', add 2 business days\n"
                f"- Skip weekends when counting business days\n"
                f"- The format 'Expédier YYYY-MM-DD' means will ship on that date, so add 2 business days\n\n"
                f"If you cannot parse the date, return: nan"
            )

            response = await self._safe_chat_completion(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
            )

            if response and response.choices:
                return response.choices[0].message.content.strip()
            else:
                return "nan"

        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return "nan"

    async def extract_delivery_dates_from_email(self, email_body: str, po_items: list) -> dict[str, str]:
        """
        Extract delivery dates from supplier email body using GPT-4 with structured output

        Args:
            email_body: The full email body from the supplier
            po_items: List of dicts with PO and line info that need dates extracted
                     Each dict should have: document_no, line_no, item_no

        Returns:
            Dict mapping "PO_LineNo" to extracted date in YYYY-MM-DD format
        """
        try:
            import json
            from datetime import datetime

            from pydantic import BaseModel, Field

            # Create structured output schema
            class DeliveryDate(BaseModel):
                po_number: str = Field(description="Purchase Order number from the PO LINES list")
                line_no: str = Field(description="Line number (Line_No) from the PO LINES list, NOT the item number")
                delivery_date: str = Field(
                    description="Extracted delivery date in YYYY-MM-DD format, or 'nan' if not found"
                )

            class DeliveryDates(BaseModel):
                dates: list[DeliveryDate] = Field(description="List of extracted delivery dates")

            today = datetime.today()
            today_str = today.strftime("%Y-%m-%d")

            # Format PO items for the prompt with both Line_No and Item No for better matching
            po_lines = "\n".join(
                [
                    f"- PO: {item['document_no']}, Line_No: {item['line_no']}, Item/Part Number: {item.get('item_no', 'N/A')}"
                    for item in po_items
                ]
            )

            prompt = (
                f"Extract delivery dates from this supplier email for the following PO lines:\n\n"
                f"PO LINES NEEDING DATES:\n{po_lines}\n\n"
                f"IMPORTANT: Suppliers often reference the Item/Part Number instead of Line_No.\n"
                f"Match based on EITHER the Line_No OR the Item/Part Number mentioned in the email.\n\n"
                f"SUPPLIER EMAIL:\n{email_body}\n\n"
                f"INSTRUCTIONS:\n"
                f"1. Find delivery information for each PO line in the email\n"
                f"2. Match lines by looking for EITHER:\n"
                f"   - The Line_No (e.g., 'Line 10000', 'ligne 10000')\n"
                f"   - The Item/Part Number (e.g., 'ABC123', 'part ABC123', 'item ABC123')\n"
                f"   - If email mentions ALL orders/commands generally (e.g., 'Ces commandes', 'these orders'), apply to ALL lines\n"
                f"3. Look for dates, shipping info, availability statements in French and English\n"
                f"4. Convert any found dates to YYYY-MM-DD format\n"
                f"5. Add 2 business days for shipping if the date is a ship date\n"
                f"6. Today's date is {today_str}\n"
                f"7. If no date found for a line, return 'nan'\n\n"
                f"Common patterns:\n"
                f"- 'Item ABC123 ships tomorrow' → tomorrow + 2 business days\n"
                f"- 'Part XYZ789 in stock' → today + 2 business days\n"
                f"- 'Line 10000 available next week' → Monday of next week + 2 business days\n"
                f"- '2-3 jours for ABC123' → 3 days + 2 business days\n"
                f"- Direct dates like '2025-08-28' → that date + 2 business days\n"
                f"- 'Ces 2 commandes vont partir aujourd'hui' → today + 2 business days for ALL lines\n"
                f"- 'partir aujourd'hui' / 'ships today' → today + 2 business days\n"
                f"- 'demain' / 'tomorrow' → tomorrow + 2 business days\n"
                f"- 'cette semaine' / 'this week' → end of this week + 2 business days\n\n"
                f"French time expressions:\n"
                f"- aujourd'hui = today\n"
                f"- demain = tomorrow\n"
                f"- cette semaine = this week\n"
                f"- la semaine prochaine = next week\n"
                f"- lundi, mardi, mercredi, jeudi, vendredi = Monday through Friday\n\n"
                f"RETURN the Line_No from the PO LINES list above, not the item number."
            )

            # Use GPT-4 with structured output
            response = await self._safe_chat_completion(
                model="gpt-5-2025-08-07",  # Using latest GPT-5 for confirmation processing
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting delivery dates from supplier emails.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "delivery_dates",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "dates": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "po_number": {"type": "string"},
                                            "line_no": {"type": "string"},
                                            "delivery_date": {"type": "string"},
                                        },
                                        "required": ["po_number", "line_no", "delivery_date"],
                                        "additionalProperties": False,
                                    },
                                }
                            },
                            "required": ["dates"],
                            "additionalProperties": False,
                        },
                    },
                },
            )

            if response and response.choices:
                result = json.loads(response.choices[0].message.content)

                # Convert to dict for easy lookup
                date_map = {}
                for item in result.get("dates", []):
                    key = f"{item['po_number']}_{item['line_no']}"
                    date_map[key] = item["delivery_date"]

                # Log extraction details for debugging
                if date_map:
                    logger.info(f"Successfully extracted {len(date_map)} delivery dates from email body")
                    for key, date in date_map.items():
                        if date != "nan":
                            logger.info(f"  - {key}: {date}")
                else:
                    logger.warning("No delivery dates could be extracted from email body")

                return date_map
            else:
                logger.error("No response from OpenAI for delivery date extraction")
                return {}

        except Exception as e:
            logger.error(f"Error extracting delivery dates from email: {e}")
            return {}

    async def get_chat_completion(self, prompt: str) -> str:
        """
        Get chat completion with classification system prompt
        Used by: Classification tasks
        Migrated from chat_GPT.py get_chat_completion()
        """
        try:
            truncated_prompt = self._truncate_text_tokens(prompt)

            response = await self._safe_chat_completion(
                model=self.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant capable of classifying texts into specific categories.",
                    },
                    {"role": "user", "content": truncated_prompt},
                ],
            )

            if response and response.choices:
                return response.choices[0].message.content.strip()
            else:
                return "Error: No response from OpenAI"

        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            return f"Error: {e}"

    async def create_completion(self, model: str, messages: list, max_tokens: int = None) -> dict[str, Any]:
        """
        Create completion with custom model and messages
        Used for vision API and other advanced features
        """
        try:
            kwargs = {
                "model": model,
                "messages": messages,
            }

            if max_tokens:
                # Use max_completion_tokens for new models
                kwargs["max_completion_tokens"] = max_tokens

            response = await self._safe_chat_completion(**kwargs)

            if response:
                # Convert response to dict format for compatibility
                return {"choices": [{"message": {"content": response.choices[0].message.content}}]}
            else:
                return {"choices": [{"message": {"content": ""}}]}

        except Exception as e:
            logger.error(f"Error in create_completion: {e}")
            return {"choices": [{"message": {"content": f"Error: {e}"}}]}

    async def analyze_image_with_prompt(self, base64_image: str, prompt: str) -> str | None:
        """
        Analyze an image using GPT-4 Vision API with a custom prompt
        Used for processing screenshots and image attachments

        Args:
            base64_image: Base64 encoded image string
            prompt: Analysis prompt describing what to extract

        Returns:
            Analysis result as string, or None if failed
        """
        try:
            logger.info("Analyzing image with GPT-5 Vision API")

            response = await self._safe_chat_completion(
                model="gpt-5-2025-08-07",  # Use GPT-5 for vision tasks (best accuracy)
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high",  # High detail for better table extraction
                                },
                            },
                        ],
                    }
                ],
                max_completion_tokens=2000,  # Use max_completion_tokens for new models
                temperature=0.1,  # Low temperature for accurate extraction
            )

            if response and response.choices and len(response.choices) > 0:
                result = response.choices[0].message.content
                logger.info(f"Vision API analysis complete, result length: {len(result)}")
                return result
            else:
                logger.warning("Vision API returned empty response")
                return None

        except Exception as e:
            logger.error(f"Error analyzing image with Vision API: {e}")
            return None

    async def extract_part_numbers(self, text: str) -> list:
        """
        Extract part numbers from text using OpenAI
        Used by: UnknownProcessor for extracting part numbers from PDF content

        Args:
            text: Text content to analyze (typically from PDF)

        Returns:
            List of extracted part numbers
        """
        try:
            prompt = (
                "Extract all part numbers, item numbers, SKUs, or product codes from the following text.\n"
                "Part numbers can be in various formats like:\n"
                "- Alphanumeric codes (e.g., ABC123, XYZ-789, 12345-AB)\n"
                "- Numeric codes (e.g., 123456, 7890)\n"
                "- Codes with special characters (e.g., ABC_123, XYZ.456)\n\n"
                "Return ONLY a JSON array of part numbers found, without any explanation.\n"
                "If no part numbers are found, return an empty array [].\n\n"
                f"Text to analyze:\n{text[:4000]}"  # Limit text to avoid token limits
            )

            response = await self._safe_chat_completion(
                model=self.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting part numbers and product codes from documents.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=500,  # Use max_completion_tokens for new models
                temperature=0.1,
            )

            if response and response.choices:
                content = response.choices[0].message.content.strip()
                # Try to parse as JSON array
                try:
                    import json

                    parts = json.loads(content)
                    if isinstance(parts, list):
                        logger.info(f"Extracted {len(parts)} part numbers from text")
                        return parts
                    else:
                        logger.warning(f"Invalid response format for part numbers: {content}")
                        return []
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse part numbers response as JSON: {content}")
                    return []
            else:
                logger.warning("No response from OpenAI for part number extraction")
                return []

        except Exception as e:
            logger.error(f"Error extracting part numbers: {e}")
            return []


# Sync wrapper functions for V1 compatibility (used by confirmation_commande.py and others)
def get_text_response(user_prompt: str) -> str:
    """Sync wrapper for get_text_response - used by migration files"""

    async def _get():
        async with OpenAIClient() as client:
            return await client.get_text_response(user_prompt)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())
    except:
        return asyncio.run(_get())


def completion(user_prompt: str) -> str:
    """Sync wrapper for completion - used by migration files"""

    async def _complete():
        async with OpenAIClient() as client:
            return await client.completion(user_prompt)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_complete())
    except:
        return asyncio.run(_complete())


def Translate_to_English(user_prompt: str) -> str:
    """Sync wrapper for translate_to_english - used by migration files"""

    async def _translate():
        async with OpenAIClient() as client:
            return await client.translate_to_english(user_prompt)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_translate())
    except:
        return asyncio.run(_translate())


def Formater_Date(date_to_format: str) -> str:
    """Sync wrapper for format_date - used by migration files"""

    async def _format():
        async with OpenAIClient() as client:
            return await client.format_date(date_to_format)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_format())
    except:
        return asyncio.run(_format())


def get_chat_completion(prompt: str) -> str:
    """Sync wrapper for get_chat_completion - used by migration files"""

    async def _get():
        async with OpenAIClient() as client:
            return await client.get_chat_completion(prompt)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())
    except:
        return asyncio.run(_get())
