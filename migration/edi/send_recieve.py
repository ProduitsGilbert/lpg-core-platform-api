import configparser
import os
import platform
from dataclasses import dataclass
from typing import Optional, Tuple

import posixpath

import logfire
import paramiko
from dotenv import load_dotenv

# Let the application configure logfire globally; do not reconfigure here.

config = configparser.ConfigParser()
config.read("data/config.ini")

# Load .env file so local development picks up credentials.
load_dotenv()


def get_edi_paths():
    """Determine local folders for EDI send/receive operations."""

    # Allow explicit override for all environments
    base_override = (
        os.environ.get("EDI_BASE_PATH")
        or os.environ.get("EDI_LOCAL_BASE")
    )

    if base_override:
        base = base_override
    elif os.environ.get("CONTAINER") or os.path.isdir("/app"):
        # Default inside application container image
        base = "/app/edi"
    elif platform.system() == "Windows":
        # Windows environment
        base = "c:\\edi"
    else:
        # macOS/Linux local environment
        home = os.path.expanduser("~")
        base = os.path.join(home, "edi")

    return os.path.join(base, "send"), os.path.join(base, "receive")


LOCAL_FOLDER_SEND, LOCAL_FOLDER_RECEIVE = get_edi_paths()

# if platform.system() == "Windows":
# Local development
#    LOCAL_FOLDER_SEND = "c:\\edi\\send"
#    LOCAL_FOLDER_RECEIVE = "c:\\edi\\receive"
# else:
# Docker environment
#    LOCAL_FOLDER_SEND = "/app/send"
#    LOCAL_FOLDER_RECEIVE = "/Users/girda01/edi/receive"
# LOCAL_FOLDER_RECEIVE = "/tmp/receive"
#    LOCAL_FOLDER_RECEIVE = "/Users/girda01/edi/receive"

def _config_or_env(key: str, *, env: str, default: Optional[str] = None) -> Optional[str]:
    """Helper to fetch a value from environment variables with config fallback."""

    value = os.getenv(env)
    if value:
        return value

    if config.has_section("credentials"):
        return config["credentials"].get(key, default)

    return default


PORT = int(_config_or_env("PORT", env="PORT", default="22"))
HOST = _config_or_env("HOST", env="HOST", default="") or ""
USERNAME = _config_or_env("SFTP_USERNAME", env="SFTP_USERNAME", default="") or ""
PASSWORD = _config_or_env("SFTP_PASSWORD", env="SFTP_PASSWORD", default="") or ""
REMOTE_FOLDER_SEND = _config_or_env("REMOTE_FOLDER_SEND", env="REMOTE_FOLDER_SEND", default="") or ""
REMOTE_FOLDER_RECEIVE = _config_or_env("REMOTE_FOLDER_RECEIVE", env="REMOTE_FOLDER_RECEIVE", default="") or ""


@dataclass
class SFTPSendResult:
    """Structured result returned by EDI SFTP send operations."""

    success: bool
    remote_path: Optional[str] = None
    message: Optional[str] = None


def send_to_sftp(host, port, username, password, local_folder_path, remote_folder_path):
    with logfire.span("SFTP Send Operation"):
        # Assume transfer is successful unless proven otherwise
        transfer_successful = False

        # Create an SSH client instance
        ssh_client = paramiko.SSHClient()

        # Automatically add the server's host key (note: this is insecure and used for demonstration)
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Connect to the SSH server
            with logfire.span("SFTP Connection Setup"):
                logfire.info(
                    f"Connecting to SFTP server at {host}:{port} with username {username}"
                )
                ssh_client.connect(host, port, username, password)
                logfire.info("Successfully connected to SFTP server")

                # Open an SFTP session
                sftp = ssh_client.open_sftp()
                logfire.info("SFTP session opened")

            # List all files in the local folder
            files_to_send = [
                f
                for f in os.listdir(local_folder_path)
                if os.path.isfile(os.path.join(local_folder_path, f))
            ]

            with logfire.span(f"Transfer {len(files_to_send)} files"):
                for filename in files_to_send:
                    local_file_path = os.path.join(local_folder_path, filename)
                    remote_file_path = os.path.join(remote_folder_path, filename)

                    with logfire.span(f"Transfer file {filename}"):
                        try:
                            # Attempt to send the file to the SFTP server (this will overwrite if the file already exists)
                            sftp.put(local_file_path, remote_file_path)
                            logfire.info(
                                f"Successfully transferred: {local_file_path} to {remote_file_path}"
                            )
                            os.remove(
                                local_file_path
                            )  # Remove the file after successful transfer
                            transfer_successful = True  # Mark transfer as successful
                        except Exception as e:
                            logfire.error(
                                f"Failed to transfer {local_file_path} to {remote_file_path}: {e}"
                            )
                            transfer_successful = False
                            break  # Exit the loop on failure

        except Exception as e:
            logfire.fatal(f"Failed to connect or transfer files to SFTP server: {e}")
            transfer_successful = False
        finally:
            # Close the SFTP session and SSH connection
            with logfire.span("SFTP Connection Cleanup"):
                try:
                    if "sftp" in locals():
                        sftp.close()
                        logfire.info("SFTP session closed")
                    ssh_client.close()
                    logfire.info("SSH connection closed")
                except Exception as e:
                    logfire.error(f"Error closing SFTP session or SSH connection: {e}")

        # Return the success status
        return transfer_successful


def _connect_sftp(host: str, port: int, username: str, password: str) -> Tuple[paramiko.SSHClient, paramiko.SFTPClient]:
    """Establish and return an SSH client and open SFTP session."""

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(host, port, username, password)
    return ssh_client, ssh_client.open_sftp()


def _ensure_remote_directory(sftp_client: paramiko.SFTPClient, remote_directory: str) -> None:
    """Create the remote directory tree if it does not already exist."""

    if not remote_directory:
        return

    parts = [part for part in remote_directory.split("/") if part]
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else part
        try:
            sftp_client.stat(current)
        except FileNotFoundError:
            sftp_client.mkdir(current)


def send_file(
    local_file_path: str,
    *,
    remote_folder_path: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    remove_local_on_success: bool = True,
) -> SFTPSendResult:
    """Send a single file to the SFTP endpoint defined in the configuration."""

    resolved_host = host or HOST
    resolved_port = port or PORT
    resolved_username = username or USERNAME
    resolved_password = password or PASSWORD
    resolved_remote_folder = remote_folder_path or REMOTE_FOLDER_SEND

    if not os.path.isfile(local_file_path):
        return SFTPSendResult(False, message=f"Local file does not exist: {local_file_path}")

    try:
        os.makedirs(os.path.dirname(local_file_path) or ".", exist_ok=True)
    except Exception as exc:  # pragma: no cover - defensive; directory may already exist
        return SFTPSendResult(False, message=f"Failed to ensure local directory: {exc}")

    with logfire.span("SFTP Single File Send", file=local_file_path, remote_folder=resolved_remote_folder):
        ssh_client: Optional[paramiko.SSHClient] = None
        sftp_client: Optional[paramiko.SFTPClient] = None
        try:
            ssh_client, sftp_client = _connect_sftp(
                resolved_host,
                resolved_port,
                resolved_username,
                resolved_password,
            )

            remote_filename = os.path.basename(local_file_path)
            cleaned_folder = (resolved_remote_folder or "").strip("/")
            remote_path = (
                posixpath.join(cleaned_folder, remote_filename)
                if cleaned_folder
                else remote_filename
            )

            remote_directory = posixpath.dirname(remote_path)
            _ensure_remote_directory(sftp_client, remote_directory)

            logfire.info(
                "Uploading EDI document", file=local_file_path, remote_path=remote_path
            )
            sftp_client.put(local_file_path, remote_path)

            if remove_local_on_success:
                try:
                    os.remove(local_file_path)
                except OSError as exc:
                    logfire.warning(
                        "Failed to remove local EDI file after transfer",
                        file=local_file_path,
                        error=str(exc),
                    )

            return SFTPSendResult(True, remote_path=remote_path)

        except Exception as exc:  # pragma: no cover - network/IO heavy
            logfire.error("EDI SFTP transfer failed", error=str(exc))
            return SFTPSendResult(False, message=str(exc))

        finally:
            if sftp_client is not None:
                try:
                    sftp_client.close()
                except Exception:
                    pass
            if ssh_client is not None:
                try:
                    ssh_client.close()
                except Exception:
                    pass


def receive_from_sftp(
    host, port, username, password, local_folder_path, remote_folder_path
):
    with logfire.span("SFTP Receive Operation"):
        if not remote_folder_path:
            raise ValueError("The remote_folder_path is not specified or is None.")

        os.makedirs(local_folder_path, exist_ok=True)
        # Create an SSH client instance
        ssh_client = paramiko.SSHClient()

        try:
            # Automatically add the server's host key
            with logfire.span("SFTP Connection Setup for Receive"):
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(host, port, username, password)
                sftp = ssh_client.open_sftp()

            # Validate remote folder
            with logfire.span("Validate Remote Folder"):
                try:
                    remote_files = sftp.listdir(remote_folder_path)
                    logfire.info(f"Found {len(remote_files)} files in remote folder")
                except FileNotFoundError:
                    raise ValueError(
                        f"The specified remote folder '{remote_folder_path}' does not exist."
                    )

            # List and process files in the remote SFTP folder
            with logfire.span(f"Download {len(remote_files)} files"):
                for filename in remote_files:
                    remote_file_path = os.path.join(remote_folder_path, filename)
                    local_file_path = os.path.join(local_folder_path, filename)

                    with logfire.span(f"Download file {filename}"):
                        try:
                            if (
                                sftp.stat(remote_file_path).st_mode & 0o100000
                            ):  # Regular file
                                # Download the file
                                sftp.get(remote_file_path, local_file_path)
                                # Delete the file on the SFTP server
                                sftp.remove(remote_file_path)
                                logfire.info(
                                    f"Successfully downloaded and removed {filename}"
                                )
                        except Exception as e:
                            logfire.error(
                                f"Error processing file {remote_file_path}: {e}"
                            )

            # Close the SFTP client
            sftp.close()
        except Exception as e:
            logfire.error(f"Error in SFTP operation: {e}")
        finally:
            with logfire.span("SFTP Connection Cleanup for Receive"):
                ssh_client.close()


def send():
    result = send_to_sftp(
        HOST, PORT, USERNAME, PASSWORD, LOCAL_FOLDER_SEND, REMOTE_FOLDER_SEND
    )
    return result


def receive():
    receive_from_sftp(
        HOST, PORT, USERNAME, PASSWORD, LOCAL_FOLDER_RECEIVE, REMOTE_FOLDER_RECEIVE
    )


# Usage example:


def main():
    send_to_sftp(HOST, PORT, USERNAME, PASSWORD, LOCAL_FOLDER_SEND, REMOTE_FOLDER_SEND)
    receive_from_sftp(
        HOST, PORT, USERNAME, PASSWORD, LOCAL_FOLDER_RECEIVE, REMOTE_FOLDER_RECEIVE
    )


if __name__ == "__main__":
    # Specify the path to the folder to monitor
    main()
