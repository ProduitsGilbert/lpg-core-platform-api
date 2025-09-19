"""
PLM (Product Lifecycle Management) API Client
Interfaces with Gilbert-Tech PLM system (Windchill)
"""

import logging
import os
import ssl
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class PLMClient:
    """Client for PLM system integration"""

    def __init__(self):
        """Initialize PLM client with credentials from environment"""
        self.base_url = "https://plm.gilbert-tech.com/Windchill/servlet/odata/ProdMgmt"
        self.username = os.getenv("PLM_USERNAME", "girda01")
        self.password = os.getenv("PLM_PASSWORD", "123456")

        if not self.username or not self.password:
            logger.warning("PLM credentials not found in environment variables")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    async def get_part_data(self, part_number: str) -> dict[str, Any] | None:
        """
        Fetch part data from PLM system

        Args:
            part_number: 7-digit part number

        Returns:
            Part data dictionary or None if not found
        """
        try:
            endpoint = f"{self.base_url}/Parts?$filter=Number eq '{part_number}'"

            # Create SSL context that doesn't verify certificates (for internal API)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Create auth header
            auth = aiohttp.BasicAuth(self.username, self.password)

            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, auth=auth, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "value" in data and data["value"]:
                            logger.info(f"Successfully fetched PLM data for part {part_number}")
                            return data["value"][0]
                        else:
                            logger.warning(f"No PLM data found for part {part_number}")
                            return None
                    else:
                        logger.error(f"PLM API returned status {response.status} for part {part_number}")
                        return None

        except Exception as e:
            logger.error(f"Error fetching PLM data for part {part_number}: {e}")
            return None

    async def is_part_purchased(self, part_number: str) -> bool:
        """
        Check if a part is purchased (buy) or manufactured (make)
        Uses the Source field from PLM as the authoritative source

        Args:
            part_number: 7-digit part number

        Returns:
            True if part is purchased, False if manufactured
        """
        try:
            data = await self.get_part_data(part_number)

            if data and "Source" in data and "Value" in data["Source"]:
                source_value = data["Source"]["Value"]

                # "buy" means purchased part, "make" means manufactured
                is_purchased = source_value.lower() == "buy"

                logger.info(
                    f"Part {part_number} is {'purchased' if is_purchased else 'manufactured'} (source: {source_value})"
                )
                return is_purchased
            else:
                # Default to manufactured if we can't determine
                logger.warning(f"Could not determine source for part {part_number}, defaulting to manufactured")
                return False

        except Exception as e:
            logger.error(f"Error checking purchase status for part {part_number}: {e}")
            # Default to manufactured on error
            return False

    async def get_info_from_parts(self, part_number: str) -> dict[str, Any] | None:
        """
        Get part information from PLM (matches migrations/plm.py method name)

        Args:
            part_number: 7-digit part number

        Returns:
            Part information dictionary with "Revision" key or None if not found
        """
        try:
            data = await self.get_part_data(part_number)

            if data:
                # Format to match expected structure from migrations
                part_info = {
                    "Number": data.get("Number", part_number),
                    "Name": data.get("Name", ""),
                    "Description": data.get("Description", ""),
                    "Source": data.get("Source", {}).get("Value", "make"),
                    "State": data.get("State", {}).get("Value", ""),
                    "Version": data.get("Version", ""),
                    "Revision": data.get("Revision", ""),  # Capital R for compatibility
                    "Created": data.get("Created", ""),
                    "Modified": data.get("Modified", ""),
                }

                logger.debug(f"Retrieved part info from PLM for {part_number}: {part_info}")
                return part_info
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting part info from PLM for {part_number}: {e}")
            return None

    async def get_part_info(self, part_number: str) -> dict[str, Any] | None:
        """
        Get comprehensive part information from PLM

        Args:
            part_number: 7-digit part number

        Returns:
            Part information dictionary or None if not found
        """
        try:
            data = await self.get_part_data(part_number)

            if data:
                # Extract relevant fields
                part_info = {
                    "number": data.get("Number", part_number),
                    "name": data.get("Name", ""),
                    "description": data.get("Description", ""),
                    "source": data.get("Source", {}).get("Value", "make"),
                    "state": data.get("State", {}).get("Value", ""),
                    "version": data.get("Version", ""),
                    "revision": data.get("Revision", ""),
                    "created": data.get("Created", ""),
                    "modified": data.get("Modified", ""),
                    "weight": self._extract_weight(data),
                }

                logger.debug(f"Retrieved part info for {part_number}: {part_info}")
                return part_info
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting part info for {part_number}: {e}")
            return None

    async def get_pieces_achetee(self, part_number: str) -> str:
        """
        V1 compatibility method to check if part is purchased

        Args:
            part_number: 7-digit part number

        Returns:
            "buy" if purchased, "make" if manufactured
        """
        is_purchased = await self.is_part_purchased(part_number)
        return "buy" if is_purchased else "make"

    def _extract_weight(self, part_data: dict[str, Any]) -> float:
        """
        Extract weight from part data

        Args:
            part_data: Raw part data from PLM

        Returns:
            Weight in pounds or 0.0 if not found
        """
        try:
            # Priority 1: Try GpCalcMass (calculated mass)
            if "GpCalcMass" in part_data:
                mass_data = part_data["GpCalcMass"]
                if isinstance(mass_data, list) and mass_data:
                    # GpCalcMass is a list with dict containing Value directly as float
                    if "Value" in mass_data[0]:
                        weight_kg = float(mass_data[0]["Value"])
                        # Convert kg to lbs (1 kg = 2.20462 lbs)
                        weight_lbs = weight_kg * 2.20462
                        logger.debug(f"Extracted weight from GpCalcMass: {weight_kg} kg = {weight_lbs} lbs")
                        return round(weight_lbs, 2)

            # Priority 2: Try GpMass (stored mass)
            if "GpMass" in part_data:
                mass_data = part_data["GpMass"]
                if isinstance(mass_data, dict) and "Value" in mass_data:
                    weight_kg = float(mass_data["Value"])
                    # Convert kg to lbs
                    weight_lbs = weight_kg * 2.20462
                    logger.debug(f"Extracted weight from GpMass: {weight_kg} kg = {weight_lbs} lbs")
                    return round(weight_lbs, 2)

            # Priority 3: Try direct Weight field if it exists
            if "Weight" in part_data:
                weight = float(part_data["Weight"])
                logger.debug(f"Extracted weight from Weight field: {weight} lbs")
                return weight

            logger.debug("No weight data found in part data")
            return 0.0

        except Exception as e:
            logger.error(f"Error extracting weight from part data: {e}")
            return 0.0


# Global PLM client instance
plm_client = PLMClient()
