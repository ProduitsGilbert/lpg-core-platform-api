"""
SMB Client for accessing Windows file shares
Used for downloading cutting plans and technical drawings
"""

import logging

import smbclient
from smbprotocol.exceptions import SMBException

from ..config import settings

logger = logging.getLogger(__name__)


class SMBClient:
    """Client for accessing Windows SMB/CIFS file shares"""

    def __init__(self):
        self.server = "LPGAFS01.gilbert-tech.com"  # File server hostname (192.168.0.220)
        self.username = settings.file_share_username
        self.password = settings.file_share_password
        self.domain = "gilbert-tech.com"

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download a file from SMB share to local path

        Args:
            remote_path: Path on the SMB share (e.g., "G:/000 oxycoupage/1234567-001-A.dwg")
            local_path: Local destination path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Configure SMB client with credentials
            smbclient.ClientConfig(username=self.username, password=self.password, domain=self.domain)

            # Convert Windows path to SMB UNC path
            # G:/path -> //server/DriveG$/path
            if remote_path.startswith("G:"):
                smb_path = remote_path.replace("G:", f"//{self.server}/DriveG$")
            else:
                smb_path = f"//{self.server}/DriveG$/{remote_path}"

            # Normalize path separators
            smb_path = smb_path.replace("\\", "/")

            logger.info(f"Attempting to download from SMB: {smb_path}")

            # Download the file
            with smbclient.open_file(smb_path, mode="rb") as src:
                with open(local_path, "wb") as dst:
                    dst.write(src.read())

            logger.info(f"Successfully downloaded {remote_path} to {local_path}")
            return True

        except SMBException as e:
            logger.error(f"SMB error downloading {remote_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return False

    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists on the SMB share

        Args:
            remote_path: Path on the SMB share

        Returns:
            True if file exists, False otherwise
        """
        try:
            # Configure SMB client
            smbclient.ClientConfig(username=self.username, password=self.password, domain=self.domain)

            # Convert to SMB UNC path
            if remote_path.startswith("G:"):
                smb_path = remote_path.replace("G:", f"//{self.server}/DriveG$")
            else:
                smb_path = f"//{self.server}/DriveG$/{remote_path}"

            smb_path = smb_path.replace("\\", "/")

            # Check if file exists
            return smbclient.path.exists(smb_path)

        except Exception as e:
            logger.error(f"Error checking file existence for {remote_path}: {e}")
            return False

    def list_directory(self, remote_path: str) -> list:
        """
        List files in a directory on the SMB share

        Args:
            remote_path: Directory path on the SMB share

        Returns:
            List of file names in the directory
        """
        try:
            # Configure SMB client
            smbclient.ClientConfig(username=self.username, password=self.password, domain=self.domain)

            # Convert to SMB UNC path
            if remote_path.startswith("G:"):
                smb_path = remote_path.replace("G:", f"//{self.server}/DriveG$")
            else:
                smb_path = f"//{self.server}/DriveG$/{remote_path}"

            smb_path = smb_path.replace("\\", "/")

            # List directory contents
            files = []
            for entry in smbclient.listdir(smb_path):
                files.append(entry)

            return files

        except Exception as e:
            logger.error(f"Error listing directory {remote_path}: {e}")
            return []
