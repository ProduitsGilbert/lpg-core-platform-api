"""Helper utilities for EDI processing."""

from importlib import import_module

from .send_recieve import (
    SFTPSendResult,
    get_edi_paths,
    receive,
    receive_from_sftp,
    send,
    send_file,
    send_to_sftp,
)

_edi_850_module = import_module(".850", __name__)
build_edi_850_document = getattr(_edi_850_module, "build_edi_850_document")
generate_edi_850 = getattr(_edi_850_module, "generate_edi_850")

__all__ = [
    "SFTPSendResult",
    "build_edi_850_document",
    "generate_edi_850",
    "get_edi_paths",
    "receive",
    "receive_from_sftp",
    "send",
    "send_file",
    "send_to_sftp",
]
