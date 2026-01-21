"""Attachment handling utilities for NanoChat."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class AttachmentType(Enum):
    """Type of file attachment."""

    IMAGE = "image"
    DOCUMENT = "document"


class DocumentType(Enum):
    """Supported document types."""

    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    EPUB = "epub"


# File extension to MIME type mapping
MIME_TYPES: dict[str, str] = {
    # Images
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    # Documents
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".epub": "application/epub+zip",
}

# Extension to document type mapping
DOCUMENT_TYPES: dict[str, DocumentType] = {
    ".pdf": DocumentType.PDF,
    ".md": DocumentType.MARKDOWN,
    ".markdown": DocumentType.MARKDOWN,
    ".txt": DocumentType.TEXT,
    ".epub": DocumentType.EPUB,
}

# Supported file extensions by category
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt", ".epub"}

# Maximum file sizes in bytes
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 MB


@dataclass
class PendingAttachment:
    """An attachment waiting to be uploaded or already uploaded."""

    path: Path
    attachment_type: AttachmentType
    mime_type: str
    document_type: Optional[DocumentType] = None
    # Set after upload
    storage_id: Optional[str] = None
    url: Optional[str] = None
    upload_error: Optional[str] = None

    @property
    def filename(self) -> str:
        """Get the filename."""
        return self.path.name

    @property
    def is_uploaded(self) -> bool:
        """Check if the attachment has been uploaded."""
        return self.storage_id is not None and self.url is not None

    @property
    def has_error(self) -> bool:
        """Check if upload failed."""
        return self.upload_error is not None


def get_attachment_type(path: Path) -> Optional[AttachmentType]:
    """Determine the attachment type from file extension.

    Args:
        path: Path to the file

    Returns:
        AttachmentType or None if not supported
    """
    ext = path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return AttachmentType.IMAGE
    if ext in DOCUMENT_EXTENSIONS:
        return AttachmentType.DOCUMENT
    return None


def get_mime_type(path: Path) -> Optional[str]:
    """Get MIME type for a file.

    Args:
        path: Path to the file

    Returns:
        MIME type string or None if not supported
    """
    ext = path.suffix.lower()
    return MIME_TYPES.get(ext)


def get_document_type(path: Path) -> Optional[DocumentType]:
    """Get document type for a file.

    Args:
        path: Path to the file

    Returns:
        DocumentType or None if not a document
    """
    ext = path.suffix.lower()
    return DOCUMENT_TYPES.get(ext)


def validate_attachment(path: Path) -> tuple[bool, str]:
    """Validate a file for attachment.

    Args:
        path: Path to the file

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path.exists():
        return False, "File does not exist"

    if not path.is_file():
        return False, "Path is not a file"

    attachment_type = get_attachment_type(path)
    if attachment_type is None:
        return False, f"Unsupported file type: {path.suffix}"

    file_size = path.stat().st_size

    if attachment_type == AttachmentType.IMAGE:
        if file_size > MAX_IMAGE_SIZE:
            return False, f"Image too large (max {MAX_IMAGE_SIZE // 1024 // 1024} MB)"
    else:
        if file_size > MAX_DOCUMENT_SIZE:
            return False, f"Document too large (max {MAX_DOCUMENT_SIZE // 1024 // 1024} MB)"

    return True, ""


def create_pending_attachment(path: Path) -> Optional[PendingAttachment]:
    """Create a PendingAttachment from a file path.

    Args:
        path: Path to the file

    Returns:
        PendingAttachment or None if file is not supported
    """
    attachment_type = get_attachment_type(path)
    if attachment_type is None:
        return None

    mime_type = get_mime_type(path)
    if mime_type is None:
        return None

    document_type = None
    if attachment_type == AttachmentType.DOCUMENT:
        document_type = get_document_type(path)

    return PendingAttachment(
        path=path,
        attachment_type=attachment_type,
        mime_type=mime_type,
        document_type=document_type,
    )
