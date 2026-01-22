"""
Direct SMB/NTFS file share connector.

Provides read/write helpers to interact with a Windows file share using SMB.
"""

from __future__ import annotations

import io
import logging
import os
import socket
from typing import Optional

from smb.SMBConnection import SMBConnection
from smb.smb_structs import OperationFailure

from app.settings import settings

logger = logging.getLogger(__name__)


class FileShareConnectorError(Exception):
    """Base exception for SMB file share connector."""


class FileShareDisabledError(FileShareConnectorError):
    """Raised when connector is disabled via configuration."""


class FileShareAuthenticationError(FileShareConnectorError):
    """Raised when authentication to the file share fails."""


class FileSharePathError(FileShareConnectorError):
    """Raised when an invalid path is provided."""


class SMBFileShareConnector:
    """
    Connector for direct SMB access to the Windows NTFS file share.
    """

    def __init__(self) -> None:
        self._enabled = settings.file_share_enabled
        self._server = settings.file_share_server
        self._share = settings.file_share_share
        self._base_path = settings.file_share_base_path or "/"
        self._username = settings.file_share_username
        self._password = settings.file_share_password
        self._domain = settings.file_share_domain
        self._port = settings.file_share_port or 445
        self._client_name = socket.gethostname() or "lpg-core-platform-api"

    def _ensure_enabled(self) -> None:
        if not self._enabled:
            raise FileShareDisabledError("File share connector is disabled")
        required = [self._server, self._share, self._username, self._password]
        if not all(required):
            raise FileShareConnectorError(
                "File share configuration is incomplete (server/share/credentials required)"
            )

    def _normalize_path(self, path: str) -> str:
        """Normalize path and prevent traversal outside of base path."""
        incoming = path or ""
        combined = os.path.normpath(
            os.path.join(self._base_path.lstrip("/"), incoming.lstrip("/"))
        )
        # Prevent going above base path
        if combined.startswith(".."):
            raise FileSharePathError("Path traversal is not allowed")
        # pysmb expects forward slashes
        normalized = combined.replace("\\", "/")
        # Avoid returning '.' which indicates root
        return "" if normalized == "." else normalized

    def _connect(self) -> SMBConnection:
        """Create and return an authenticated SMB connection."""
        self._ensure_enabled()

        try:
            conn = SMBConnection(
                self._username,
                self._password,
                self._client_name,
                self._server or "",
                domain=self._domain or "",
                use_ntlm_v2=True,
                is_direct_tcp=True,
            )
            # connect returns bool; will raise SMBTimeout on network errors
            connected = conn.connect(self._server, int(self._port), timeout=settings.request_timeout)
            if not connected:
                raise FileShareAuthenticationError("SMB connection failed")
            return conn
        except TimeoutError as exc:
            raise FileShareConnectorError(f"SMB connection timed out: {exc}") from exc
        except Exception as exc:  # pragma: no cover - catch-all for unexpected errors
            logger.exception("Unexpected SMB connection error")
            raise FileShareConnectorError(f"SMB connection error: {exc}") from exc

    def read_file(self, path: str) -> bytes:
        """
        Read a file from the SMB share.
        """
        remote_path = self._normalize_path(path)
        conn: Optional[SMBConnection] = None
        try:
            conn = self._connect()
            buffer = io.BytesIO()
            conn.retrieveFile(self._share, remote_path, buffer)
            return buffer.getvalue()
        except OperationFailure as exc:
            if "STATUS_OBJECT_NAME_NOT_FOUND" in str(exc):
                raise FileSharePathError(f"File not found at '{remote_path}'") from exc
            raise FileShareConnectorError(f"Failed to read file '{remote_path}': {exc}") from exc
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def list_directory(self, path: str) -> list[dict[str, object]]:
        """
        List files and subfolders inside the given path.
        """
        remote_path = self._normalize_path(path)
        conn: Optional[SMBConnection] = None
        try:
            conn = self._connect()
            # listPath expects directory path; empty string means root of share
            entries = conn.listPath(self._share, remote_path or "")
            results: list[dict[str, object]] = []
            for entry in entries:
                # Skip current/parent markers
                if entry.filename in {".", ".."}:
                    continue
                results.append(
                    {
                        "name": entry.filename,
                        "is_dir": entry.isDirectory,
                        "size": entry.file_size,
                        "last_modified": getattr(entry, "last_write_time", None),
                        "path": f"{remote_path}/{entry.filename}".lstrip("/"),
                    }
                )
            return results
        except OperationFailure as exc:
            raise FileShareConnectorError(f"Failed to list directory '{remote_path}': {exc}") from exc
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def write_file(self, path: str, content: bytes, overwrite: bool = True) -> None:
        """
        Write a file to the SMB share.
        """
        remote_path = self._normalize_path(path)
        conn: Optional[SMBConnection] = None
        try:
            conn = self._connect()

            if not overwrite:
                try:
                    # If attributes are found, file exists -> reject
                    conn.getAttributes(self._share, remote_path)
                    raise FileShareConnectorError(f"File already exists at '{remote_path}'")
                except OperationFailure:
                    # File does not exist; continue to write
                    pass

            conn.storeFile(self._share, remote_path, io.BytesIO(content))
        except OperationFailure as exc:
            raise FileShareConnectorError(f"Failed to write file '{remote_path}': {exc}") from exc
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

