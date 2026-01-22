import io
import pytest

from smb.smb_structs import OperationFailure

from app.domain.documents.file_share_connector import (
    SMBFileShareConnector,
    FileSharePathError,
)
from app.settings import settings


class _FakeSMBConnection:
    """Simple in-memory SMB connection stub."""

    def __init__(self):
        self.files = {}

    def storeFile(self, share, path, file_obj):
        self.files[(share, path)] = file_obj.read()

    def retrieveFile(self, share, path, file_obj):
        if (share, path) not in self.files:
            raise FileSharePathError("File not found")
        file_obj.write(self.files[(share, path)])

    def getAttributes(self, share, path):
        if (share, path) not in self.files:
            raise FileSharePathError("File not found")
        return {"exists": True}

    def listPath(self, share, path):
        # path '' or directory prefix
        entries = []
        seen_dirs = set()
        prefix = f"{path.rstrip('/')}/" if path else ""

        class _Entry:
            def __init__(self, filename, is_dir, file_size):
                self.filename = filename
                self.isDirectory = is_dir
                self.file_size = file_size
                self.last_write_time = None

        for (s, full_path), content in self.files.items():
            if s != share:
                continue
            if not full_path.startswith(prefix):
                continue
            remainder = full_path[len(prefix):]
            parts = remainder.split("/", 1)
            name = parts[0]
            if len(parts) == 1:
                entries.append(_Entry(name, False, len(content)))
            else:
                if name not in seen_dirs:
                    seen_dirs.add(name)
                    entries.append(_Entry(name, True, 0))

        # Always include '.' and '..' like real SMB
        entries.append(_Entry(".", True, 0))
        entries.append(_Entry("..", True, 0))
        return entries

    def close(self):
        return None


@pytest.fixture
def connector(monkeypatch):
    # Enable and configure file share settings for the test
    settings.file_share_enabled = True
    settings.file_share_server = "lpgafs01.gilbert-tech.com"
    settings.file_share_share = "commun"
    settings.file_share_base_path = "/"
    settings.file_share_username = "serviceAI"
    settings.file_share_password = "secret"
    settings.file_share_domain = "gilbert-tech.com"
    settings.file_share_port = 445

    fake_conn = _FakeSMBConnection()
    c = SMBFileShareConnector()
    monkeypatch.setattr(c, "_connect", lambda: fake_conn)
    return c, fake_conn


def test_write_and_read_markdown_file(connector):
    c, fake_conn = connector

    path = (
        "/commun/120_AMÉLIORATION CONTINUE, QUALITÉ & T.I/"
        "10_AC/30_INTELLIGENCE ARTIFICIEL/20_DÉVELOPPEMENT & CODE/"
        "TESTS FONCTIONNELS/test.md"
    )
    content = b"# Test\n\nThis is a functional SMB write/read test.\n"

    # Write the file (overwrite allowed)
    c.write_file(path, content, overwrite=True)

    # Ensure it was stored under the normalized path
    normalized = "commun/120_AMÉLIORATION CONTINUE, QUALITÉ & T.I/10_AC/30_INTELLIGENCE ARTIFICIEL/20_DÉVELOPPEMENT & CODE/TESTS FONCTIONNELS/test.md"
    assert ("commun", normalized) in fake_conn.files

    # Read back
    read_back = c.read_file(path)
    assert read_back == content


def test_read_missing_file_raises(connector):
    c, _ = connector
    with pytest.raises(FileSharePathError):
        c.read_file("/commun/nonexistent/file.md")


def test_list_directory(connector):
    c, _ = connector
    base_dir = (
        "/commun/120_AMÉLIORATION CONTINUE, QUALITÉ & T.I/"
        "10_AC/30_INTELLIGENCE ARTIFICIEL/20_DÉVELOPPEMENT & CODE/"
        "TESTS FONCTIONNELS"
    )
    file_path = f"{base_dir}/test.md"
    c.write_file(file_path, b"hello", overwrite=True)

    entries = c.list_directory(base_dir)
    names = {e["name"] for e in entries}
    assert "test.md" in names

