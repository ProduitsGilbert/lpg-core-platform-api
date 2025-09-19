"""
Front App integration client
Streamlined version with only essential functions needed by V2 processors
Based on migrations/front_app.py
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import FormData

from ..config import settings

logger = logging.getLogger(__name__)


class FrontClient:
    """
    Streamlined Front App client
    Only includes functions actually used by V2 processors
    """

    def __init__(self):
        self.base_url = "https://api2.frontapp.com"
        self.api_token = settings.front_api_key
        self.session = None

        # Configure timeout
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)

    async def __aenter__(self):
        """Async context manager entry"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Create SSL context that doesn't verify certificates (for development)
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(limit=10, ssl=ssl_context)
        self.session = aiohttp.ClientSession(headers=headers, timeout=self.timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any] | None:
        """Make authenticated request to Front API"""
        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status in [200, 201, 204]:
                    if response.status == 204:
                        return {"success": True}
                    return await response.json()
                else:
                    logger.error(f"Front API error {response.status} for {endpoint}")
                    error_text = await response.text()
                    logger.error(f"Error response: {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Front API request failed for {endpoint}: {e}")
            return None

    # Essential functions for processors

    async def add_comment(self, conversation_id: str, comment: str) -> bool:
        """
        Add comment to Front conversation
        Used by: All processors
        Migrated from front_app.py new_comments()
        """
        endpoint = f"/conversations/{conversation_id}/comments"

        # Try without author_id first (system comment)
        data = {"body": comment}

        result = await self._make_request("POST", endpoint, json=data)
        if result:
            logger.info(f"Added comment to conversation {conversation_id}")
            return True
        else:
            logger.error(f"Failed to add comment to conversation {conversation_id}")
            return False

    async def reply_to_conversation(self, conversation_id: str, message: str, archive: bool = False) -> bool:
        """
        Reply to a Front conversation (sends email reply to original sender)
        Used by: Processors that need to respond to the requester
        Migrated from front_app.py reply_conversation()
        """
        try:
            endpoint = f"/conversations/{conversation_id}/messages"

            # Add signature if configured
            signature = "\n\n--\nDépartement des achats\nLes Produits Gilbert Inc."
            full_message = f"{message}{signature}"

            payload = {"body": full_message, "options": {"archive": archive}}

            result = await self._make_request("POST", endpoint, json=payload)
            if result:
                logger.info(f"Sent reply to conversation {conversation_id}")
                return True
            else:
                logger.error(f"Failed to reply to conversation {conversation_id}")
                return False

        except Exception as e:
            logger.error(f"Error replying to conversation {conversation_id}: {e}")
            return False

    async def snooze_conversation(self, conversation_id: str, days: int) -> bool:
        """
        Snooze a conversation for a specified number of days
        Used by: Processors that need to follow up
        Migrated from front_app.py Snooze()
        """
        try:
            import datetime

            # Calculate snooze until timestamp (days from now)
            snooze_until = datetime.datetime.now() + datetime.timedelta(days=days)
            snooze_timestamp = int(snooze_until.timestamp())

            endpoint = f"/conversations/{conversation_id}"
            payload = {"snooze_until": snooze_timestamp}

            result = await self._make_request("PATCH", endpoint, json=payload)
            if result:
                logger.info(f"Snoozed conversation {conversation_id} for {days} days")
                return True
            else:
                logger.error(f"Failed to snooze conversation {conversation_id}")
                return False

        except Exception as e:
            logger.error(f"Error snoozing conversation {conversation_id}: {e}")
            return False

    async def add_tag(self, conversation_id: str, tag_id: str) -> bool:
        """
        Add tag to conversation
        Used by: SoumissionProcessor, ConfirmationProcessor
        Migrated from front_app.py add_tag()
        """
        endpoint = f"/conversations/{conversation_id}/tags"
        data = {"tag_ids": [tag_id]}

        result = await self._make_request("POST", endpoint, json=data)
        if result:
            logger.info(f"Added tag {tag_id} to conversation {conversation_id}")
            return True
        else:
            logger.error(f"Failed to add tag {tag_id} to conversation {conversation_id}")
            return False

    async def remove_tag(self, conversation_id: str, tag_id: str) -> bool:
        """
        Remove tag from conversation
        Used by: SoumissionProcessor, CreationProcessor, EnvoiPlanProcessor
        Migrated from front_app.py remove_tag()
        """
        endpoint = f"/conversations/{conversation_id}/tags"
        data = {"tag_ids": [tag_id]}

        result = await self._make_request("DELETE", endpoint, json=data)
        if result:
            logger.info(f"Removed tag {tag_id} from conversation {conversation_id}")
            return True
        else:
            logger.error(f"Failed to remove tag {tag_id} from conversation {conversation_id}")
            return False

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send new email
        Used by: SoumissionProcessor, CreationProcessor, EnvoiPlanProcessor
        Migrated from front_app.py send_new_email()
        """
        endpoint = "/channels/cha_cks/messages"  # Default channel
        data = {"to": [to_email], "subject": subject, "body": body, "options": {"archive": True}}

        result = await self._make_request("POST", endpoint, json=data)
        if result:
            logger.info(f"Sent email to {to_email} with subject '{subject}'")
            return True
        else:
            logger.error(f"Failed to send email to {to_email}")
            return False

    async def snooze_conversation(self, conversation_id: str, days: int) -> bool:
        """
        Snooze conversation for specified days
        Used by: SoumissionProcessor
        Migrated from front_app.py Snooze()
        """
        # Calculate snooze until date
        snooze_until = datetime.utcnow() + timedelta(days=days)
        # snooze_timestamp = int(snooze_until.timestamp())  # Unused variable

        endpoint = f"/conversations/{conversation_id}"
        data = {"status": "archived"}  # Front handles snoozing via status

        result = await self._make_request("PATCH", endpoint, json=data)
        if result:
            logger.info(f"Snoozed conversation {conversation_id} for {days} days")
            return True
        else:
            logger.error(f"Failed to snooze conversation {conversation_id}")
            return False

    async def archive_conversation(self, conversation_id: str) -> bool:
        """
        Archive conversation
        Used by: Various processors
        Migrated from front_app.py Archive()
        """
        endpoint = f"/conversations/{conversation_id}"
        data = {"status": "archived"}

        result = await self._make_request("PATCH", endpoint, json=data)
        if result:
            logger.info(f"Archived conversation {conversation_id}")
            return True
        else:
            logger.error(f"Failed to archive conversation {conversation_id}")
            return False

    async def mark_as_processed(self, conversation_id: str) -> bool:
        """
        Mark conversation as processed
        Used by: CreationProcessor, RevisionProcessor
        Migrated from front_app.py mark_conversation_as_processed()
        """
        # Add processed tag
        processed_tag = "tag_3w1bq0"  # From V1 tag mapping
        return await self.add_tag(conversation_id, processed_tag)

    async def get_message_by_id(self, message_id: str) -> dict[str, Any] | None:
        """
        Get complete message details by message ID
        Used to fetch full message content when webhook provides minimal payload
        """
        try:
            endpoint = f"/messages/{message_id}"
            message_data = await self._make_request("GET", endpoint)

            if message_data:
                logger.info(f"Fetched complete message content for {message_id}")
                return message_data
            else:
                logger.error(f"Failed to fetch message {message_id} from Front API")
                return None

        except Exception as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            return None

    async def download_message_attachments(self, message_id: str, dest_folder: str) -> list[str]:
        """
        Download attachments from a message
        Used by: BaseProcessor
        Migrated from front_app.py download_attachement()
        """
        downloaded_files = []

        try:
            # Get message details
            endpoint = f"/messages/{message_id}"
            message_data = await self._make_request("GET", endpoint)

            if not message_data or "attachments" not in message_data:
                return downloaded_files

            # Ensure destination folder exists
            os.makedirs(dest_folder, exist_ok=True)

            # Download each attachment
            for attachment in message_data["attachments"]:
                filename = attachment.get("filename", "unknown")
                download_url = attachment.get("url")

                if not download_url:
                    continue

                # Download attachment
                async with self.session.get(download_url) as response:
                    if response.status == 200:
                        file_path = os.path.join(dest_folder, filename)

                        with open(file_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)

                        downloaded_files.append(file_path)
                        logger.info(f"Downloaded attachment: {filename}")
                    else:
                        logger.error(f"Failed to download attachment: {filename}")

        except Exception as e:
            logger.error(f"Error downloading attachments for message {message_id}: {e}")

        return downloaded_files

    async def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """
        Get conversation details
        Used by: Test scripts and processors for conversation metadata
        """
        try:
            endpoint = f"/conversations/{conversation_id}"
            return await self._make_request("GET", endpoint)
        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {e}")
            return None

    async def get_message_body(self, conversation_id: str) -> dict[str, Any] | None:
        """
        Get message body from conversation
        Used by: SuiviProcessor
        Migrated from front_app.py get_message_body()
        """
        try:
            # Get conversation messages
            endpoint = f"/conversations/{conversation_id}/messages"
            messages_data = await self._make_request("GET", endpoint)

            if not messages_data or "_results" not in messages_data:
                logger.error(f"Could not get messages for conversation {conversation_id}")
                return None

            # Return the messages in the expected format
            return messages_data

        except Exception as e:
            logger.error(f"Error getting message body for conversation {conversation_id}: {e}")
            return None

    async def get_single_message(self, message_id: str) -> dict[str, Any] | None:
        """
        Get a single message by ID
        Used to fetch only the specific message instead of all conversation messages
        """
        try:
            endpoint = f"/messages/{message_id}"
            message_data = await self._make_request("GET", endpoint)

            if not message_data:
                logger.error(f"Could not get message {message_id}")
                return None

            return message_data

        except Exception as e:
            logger.error(f"Error getting single message {message_id}: {e}")
            return None

    async def get_conversation_comments(self, conversation_id: str) -> dict[str, Any] | None:
        """
        Get all comments in a conversation

        Args:
            conversation_id: Front conversation ID

        Returns:
            Dictionary containing comments or None if failed
        """
        endpoint = f"/conversations/{conversation_id}/comments"

        try:
            result = await self._make_request("GET", endpoint)
            return result
        except Exception as e:
            logger.error(f"Error getting comments for {conversation_id}: {e}")
            return None

    async def new_discussion(self, subject: str, message: str) -> str | None:
        """
        Create a new discussion/conversation

        Args:
            subject: Subject/title for the conversation
            message: Initial message content

        Returns:
            Conversation ID if successful, None otherwise
        """
        endpoint = "/conversations"

        payload = {
            "type": "discussion",
            "subject": subject,
            "comment": {"body": message, "author_id": "alt:address:jules@gilbert-tech.com"},  # System user
            "assignee_id": "tea_1234567",  # Default team assignment
        }

        try:
            result = await self._make_request("POST", endpoint, json=payload)
            if result and "id" in result:
                logger.info(f"Created new discussion: {result['id']}")
                return result["id"]
        except Exception as e:
            logger.error(f"Error creating new discussion: {e}")

        return None

    async def new_comments_on_cvn_id(self, conversation_id: str, comment: str) -> bool:
        """
        Add a comment to an existing conversation

        Args:
            conversation_id: Front conversation ID
            comment: Comment text to add

        Returns:
            True if successful, False otherwise
        """
        return await self.add_comment(conversation_id, comment)

    async def create_draft_message_with_files(self, conversation_id: str, folder_path: str) -> bool:
        """
        Create draft message with files from folder using multipart form data
        Used by: EnvoiPlanProcessor
        Based on migrations/front_app.py new_draft_message_with_file()
        """
        try:
            # Get files from folder
            file_paths = []
            if os.path.exists(folder_path):
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    if os.path.isfile(file_path):
                        file_paths.append(file_path)

            if not file_paths:
                logger.warning(f"No files found in {folder_path}")
                return False

            logger.info(f"Found {len(file_paths)} files to attach: {[os.path.basename(f) for f in file_paths]}")

            # Create multipart form data
            form_data = FormData()

            # Add draft fields
            form_data.add_field("mode", "shared")
            form_data.add_field("to[0]", "achat@gilbert-tech.com")
            form_data.add_field("body", "Voici les fichiers joints")
            form_data.add_field("author_id", "alt:email:dave.girard@gilbert-tech.com")
            form_data.add_field("channel_id", "cha_eaac8")
            form_data.add_field("should_add_default_signature", "true")

            # Add files as attachments - read file content first
            file_contents = []
            for i, file_path in enumerate(file_paths):
                filename = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    content = f.read()
                    file_contents.append((filename, content))

                form_data.add_field(
                    f"attachments[{i}]", content, filename=filename, content_type="application/octet-stream"
                )
                logger.debug(f"Added attachment {i}: {filename} ({len(content)} bytes)")

            # Create draft with attachments using multipart form
            url = f"{self.base_url}/conversations/{conversation_id}/drafts"

            # We need to use a different session for multipart uploads
            # to avoid conflicts with the JSON-based session headers
            headers = {
                "Authorization": f"Bearer {self.api_token}"
                # Content-Type will be set automatically by aiohttp with boundary
            }

            # Create SSL context that doesn't verify certificates (for development)
            import ssl

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)

            async with aiohttp.ClientSession(connector=connector) as upload_session:
                async with upload_session.post(url, headers=headers, data=form_data) as response:
                    if response.status in [200, 201, 204]:
                        logger.info(f"Created draft with {len(file_paths)} files for conversation {conversation_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create draft: {response.status} - {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Error creating draft with files: {e}")
            return False

    async def download_attachment(self, attachment_url: str) -> bytes | None:
        """
        Download attachment content from Front API
        Used by: DemandeTraitementProcessor

        Args:
            attachment_url: Direct URL to attachment

        Returns:
            bytes: Attachment content, or None if download fails
        """
        try:
            logger.info(f"Downloading attachment from: {attachment_url}")

            # Use aiohttp directly since attachment URLs are typically direct download links
            async with self.session.get(attachment_url) as response:
                if response.status == 200:
                    content = await response.read()
                    logger.info(f"Successfully downloaded attachment: {len(content)} bytes")
                    return content
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to download attachment: {response.status} - {error_text}")
                    return None

        except Exception as e:
            logger.error(f"Error downloading attachment: {e}")
            return None


# Sync wrapper functions for V1 compatibility
def new_comments(conversation: dict[str, Any], comment: str):
    """Sync wrapper for add_comment - used by migration files"""

    async def _add():
        async with FrontClient() as client:
            conversation_id = conversation.get("id")
            if conversation_id:
                return await client.add_comment(conversation_id, comment)
            return False

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_add())
    except RuntimeError:
        return asyncio.run(_add())


def add_tag(conversation_id: str, tag_id: str) -> bool:
    """Sync wrapper for add_tag - used by migration files"""

    async def _add():
        async with FrontClient() as client:
            return await client.add_tag(conversation_id, tag_id)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_add())
    except RuntimeError:
        return asyncio.run(_add())


def remove_tag(conversation_id: str, tag_id: str) -> bool:
    """Sync wrapper for remove_tag - used by migration files"""

    async def _add():
        async with FrontClient() as client:
            return await client.remove_tag(conversation_id, tag_id)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_add())
    except RuntimeError:
        return asyncio.run(_add())


def send_new_email(to_email: str, subject: str, body: str) -> bool:
    """Sync wrapper for send_email - used by migration files"""

    async def _send():
        async with FrontClient() as client:
            return await client.send_email(to_email, subject, body)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_send())
    except:
        return asyncio.run(_send())


def Snooze(conversation: dict[str, Any], days: int) -> bool:
    """Sync wrapper for snooze_conversation - used by migration files"""

    async def _snooze():
        async with FrontClient() as client:
            conversation_id = conversation.get("id")
            if conversation_id:
                return await client.snooze_conversation(conversation_id, days)
            return False

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_snooze())
    except:
        return asyncio.run(_snooze())


def Archive(conversation: dict[str, Any]) -> bool:
    """Sync wrapper for archive_conversation - used by migration files"""

    async def _archive():
        async with FrontClient() as client:
            conversation_id = conversation.get("id")
            if conversation_id:
                return await client.archive_conversation(conversation_id)
            return False

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_archive())
    except:
        return asyncio.run(_archive())


def mark_conversation_as_processed(conversation_id: str) -> bool:
    """Sync wrapper for mark_as_processed - used by migration files"""

    async def _mark():
        async with FrontClient() as client:
            return await client.mark_as_processed(conversation_id)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_mark())
    except:
        return asyncio.run(_mark())


def new_draft_message_with_file(conversation: dict[str, Any], folder_path: str) -> bool:
    """Sync wrapper for create_draft_message_with_files - used by migration files"""

    async def _create():
        async with FrontClient() as client:
            conversation_id = conversation.get("id")
            if conversation_id:
                return await client.create_draft_message_with_files(conversation_id, folder_path)
            return False

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_create())
    except:
        return asyncio.run(_create())


def download_attachement(url: str) -> bytes:
    """Sync wrapper for downloading attachment - used by migration files"""

    async def _download():
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                return b""

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_download())
    except:
        return asyncio.run(_download())


def get_message_body(conversation: dict[str, Any]) -> dict[str, Any]:
    """
    Get message body from conversation
    Used by migration files - simplified version
    """
    # This would typically make API call to get full message body
    # For now, return the message data from the webhook payload
    return conversation.get("message", {})


def get_comments_body(conversation: dict[str, Any]) -> dict[str, Any]:
    """
    Get comments from conversation
    Used by migration files - simplified version
    """
    # This would typically make API call to get comments
    # For now, return empty structure
    return {"_results": []}
