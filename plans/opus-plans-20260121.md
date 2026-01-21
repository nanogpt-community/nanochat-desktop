# Implementation Plans - January 21, 2026

**Author**: Claude (Architect Mode)
**Target Version**: v0.5.0
**Status**: Ready for Implementation

---

## Overview

This document contains detailed implementation plans for two features from the pending tasks list:

1. **File Attachments** (combines Drag and Drop Attachments, Image Attachments, and Document Attachments)
2. **Message Copy Button**

Each plan is written to be actionable by an LLM implementing in Code mode, with specific file paths, code patterns, and step-by-step instructions.

---

## Feature 1: File Attachments

### Summary

Enable users to attach images and documents to messages. This combines three related tasks:
- **Drag and Drop Attachments** (CRITICAL) - Drag files into chat input
- **Image Attachments** (MEDIUM) - Attach images via file picker
- **Document Attachments** (MEDIUM) - Attach PDFs, markdown, text, epub files

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        NanoChatWindow                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     Input Area                            │   │
│  │  ┌──────────────────────────────────────────────────────┐│   │
│  │  │              Attachment Preview Bar                  ││   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐                ││   │
│  │  │  │ Thumb 1 │ │ Thumb 2 │ │ Doc.pdf │ ...            ││   │
│  │  │  │   [x]   │ │   [x]   │ │   [x]   │                ││   │
│  │  │  └─────────┘ └─────────┘ └─────────┘                ││   │
│  │  └──────────────────────────────────────────────────────┘│   │
│  │  ┌────┐ ┌──────────────────────────────────────┐ ┌────┐ │   │
│  │  │ 📎 │ │        Message Entry                  │ │Send│ │   │
│  │  └────┘ └──────────────────────────────────────┘ └────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### API Endpoints Used

1. **Upload file**: `POST /api/storage`
   - Headers: `Content-Type: <mime-type>`, `x-filename: <filename>`
   - Body: Binary file content
   - Response: `{ "storageId": "string", "url": "string" }`

2. **Generate message with attachments**: `POST /api/generate-message/stream`
   - Request includes `images` and/or `documents` arrays

### Implementation Steps

---

#### Step 1: Add API Client Methods for File Upload

**File**: [`src/nanochat/api/client.py`](src/nanochat/api/client.py)

Add the following method to the `NanoChatClient` class after the `test_connection` method around line 180:

```python
async def upload_file(
    self,
    content: bytes,
    filename: str,
    mime_type: str,
) -> tuple[str, str]:
    """Upload a file to storage.

    Args:
        content: Binary file content
        filename: Original filename
        mime_type: MIME type of the file

    Returns:
        Tuple of (storage_id, url)

    Raises:
        NanoChatAPIError: If upload fails
    """
    try:
        response = await self._client.post(
            "/api/storage",
            content=content,
            headers={
                "Content-Type": mime_type,
                "x-filename": filename,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["storageId"], data["url"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise AuthenticationError("Invalid API key") from e
        raise NanoChatAPIError(f"Upload failed: {e.response.status_code}") from e
    except httpx.NetworkError as e:
        raise APIConnectionError("Cannot connect to server") from e


async def delete_file(self, storage_id: str) -> bool:
    """Delete a file from storage.

    Args:
        storage_id: The storage ID to delete

    Returns:
        True if deleted successfully
    """
    try:
        await self._request("DELETE", "/api/storage", params={"id": storage_id})
        return True
    except Exception:
        return False
```

---

#### Step 2: Update GenerateMessageRequest Model

**File**: [`src/nanochat/api/models.py`](src/nanochat/api/models.py)

Add new models for attachments before the `GenerateMessageRequest` class (around line 120):

```python
class ImageAttachment(BaseModel):
    """Image attachment for message generation."""

    url: str
    storage_id: str = Field(alias="storage_id")
    file_name: Optional[str] = Field(default=None, alias="fileName")

    model_config = {"populate_by_name": True}


class DocumentAttachment(BaseModel):
    """Document attachment for message generation."""

    url: str
    storage_id: str = Field(alias="storage_id")
    file_name: Optional[str] = Field(default=None, alias="fileName")
    file_type: str = Field(alias="fileType")  # pdf, markdown, text, epub

    model_config = {"populate_by_name": True}
```

Then update `GenerateMessageRequest` to include these fields (add after line 134):

```python
class GenerateMessageRequest(BaseModel):
    """Request to generate a message."""

    message: Optional[str] = None
    model_id: str
    assistant_id: Optional[str] = Field(default=None, alias="assistantId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    conversation_id: Optional[str] = None
    web_search_enabled: Optional[bool] = None
    web_search_mode: Optional[str] = None
    web_search_provider: Optional[str] = None
    reasoning_effort: Optional[str] = Field(default=None, alias="reasoningEffort")
    temporary: Optional[bool] = None
    # NEW: File attachments
    images: Optional[list[ImageAttachment]] = None
    documents: Optional[list[DocumentAttachment]] = None

    model_config = {"populate_by_name": True}
```

Update the imports at the top of the file to include `list` if not present.

---

#### Step 3: Create Attachment Data Classes

**File**: `src/nanochat/ui/attachments.py` (NEW FILE)

Create a new file for attachment-related data structures and utilities:

```python
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
```

---

#### Step 4: Create Attachment Preview Widget

**File**: `src/nanochat/ui/attachment_preview.py` (NEW FILE)

Create a widget for displaying attachment previews in the input area:

```python
"""Attachment preview widgets for the input area."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GdkPixbuf, GLib, Gtk

from nanochat.ui.attachments import AttachmentType, PendingAttachment


class AttachmentThumbnail(Gtk.Box):
    """A single attachment thumbnail with remove button."""

    def __init__(
        self,
        attachment: PendingAttachment,
        on_remove: callable,
        **kwargs: object,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2, **kwargs)

        self.attachment = attachment
        self._on_remove = on_remove

        self.set_size_request(80, 90)
        self.add_css_class("attachment-thumbnail")

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the thumbnail UI."""
        # Container with overlay for remove button
        overlay = Gtk.Overlay()
        overlay.set_size_request(72, 72)

        # Thumbnail or icon
        if self.attachment.attachment_type == AttachmentType.IMAGE:
            # Load image thumbnail
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(self.attachment.path),
                    64,
                    64,
                    True,
                )
                image = Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                # Fallback to icon if image can't be loaded
                image = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
                image.set_pixel_size(48)
        else:
            # Document icon based on type
            icon_name = self._get_document_icon()
            image = Gtk.Image.new_from_icon_name(icon_name)
            image.set_pixel_size(48)

        image.add_css_class("attachment-image")

        # Frame for the image
        frame = Gtk.Frame()
        frame.set_child(image)
        frame.add_css_class("attachment-frame")
        overlay.set_child(frame)

        # Remove button
        remove_btn = Gtk.Button(icon_name="window-close-symbolic")
        remove_btn.add_css_class("circular")
        remove_btn.add_css_class("flat")
        remove_btn.add_css_class("attachment-remove-btn")
        remove_btn.set_halign(Gtk.Align.END)
        remove_btn.set_valign(Gtk.Align.START)
        remove_btn.set_tooltip_text("Remove attachment")
        remove_btn.connect("clicked", self._on_remove_clicked)
        overlay.add_overlay(remove_btn)

        self.append(overlay)

        # Filename label (truncated)
        filename = self.attachment.filename
        if len(filename) > 12:
            filename = filename[:9] + "..."
        label = Gtk.Label(label=filename)
        label.set_ellipsize(True)
        label.add_css_class("caption")
        label.add_css_class("dim-label")
        self.append(label)

        # Show upload status
        if self.attachment.has_error:
            self.add_css_class("upload-error")
            error_icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
            error_icon.set_tooltip_text(self.attachment.upload_error)
            self.append(error_icon)

    def _get_document_icon(self) -> str:
        """Get icon name for document type."""
        if self.attachment.document_type is None:
            return "text-x-generic-symbolic"

        icons = {
            "pdf": "application-pdf-symbolic",
            "markdown": "text-x-generic-symbolic",
            "text": "text-x-generic-symbolic",
            "epub": "application-epub+zip-symbolic",
        }
        return icons.get(self.attachment.document_type.value, "text-x-generic-symbolic")

    def _on_remove_clicked(self, button: Gtk.Button) -> None:
        """Handle remove button click."""
        self._on_remove(self.attachment)


class AttachmentPreviewBar(Gtk.Box):
    """Bar showing attachment previews above the input area."""

    def __init__(self, on_remove: callable, **kwargs: object) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, **kwargs)

        self._on_remove = on_remove
        self._thumbnails: dict[PendingAttachment, AttachmentThumbnail] = {}

        self.add_css_class("attachment-preview-bar")
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_bottom(8)

        # Scrolled window for many attachments
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self._scroll.set_hexpand(True)

        self._box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._scroll.set_child(self._box)
        self.append(self._scroll)

        # Initially hidden
        self.set_visible(False)

    def add_attachment(self, attachment: PendingAttachment) -> None:
        """Add an attachment to the preview bar."""
        thumbnail = AttachmentThumbnail(attachment, self._on_remove)
        self._thumbnails[attachment] = thumbnail
        self._box.append(thumbnail)
        self.set_visible(True)

    def remove_attachment(self, attachment: PendingAttachment) -> None:
        """Remove an attachment from the preview bar."""
        if attachment in self._thumbnails:
            thumbnail = self._thumbnails.pop(attachment)
            self._box.remove(thumbnail)

        # Hide if empty
        if not self._thumbnails:
            self.set_visible(False)

    def clear(self) -> None:
        """Remove all attachments."""
        for thumbnail in list(self._thumbnails.values()):
            self._box.remove(thumbnail)
        self._thumbnails.clear()
        self.set_visible(False)

    def update_attachment(self, attachment: PendingAttachment) -> None:
        """Update display for an attachment (e.g., after upload)."""
        if attachment in self._thumbnails:
            # Rebuild the thumbnail
            old_thumbnail = self._thumbnails[attachment]
            new_thumbnail = AttachmentThumbnail(attachment, self._on_remove)
            self._thumbnails[attachment] = new_thumbnail

            # Replace in box
            idx = 0
            child = self._box.get_first_child()
            while child is not None:
                if child == old_thumbnail:
                    break
                idx += 1
                child = child.get_next_sibling()

            self._box.remove(old_thumbnail)
            self._box.insert_child_after(new_thumbnail, self._box.get_first_child() if idx == 0 else None)

    def get_attachments(self) -> list[PendingAttachment]:
        """Get all current attachments."""
        return list(self._thumbnails.keys())
```

---

#### Step 5: Add CSS Styles for Attachments

**File**: `data/styles/attachments.css` (NEW FILE)

Create CSS styles for attachment UI elements:

```css
/* Attachment Preview Bar */
.attachment-preview-bar {
    background-color: alpha(@card_bg_color, 0.5);
    border-radius: 8px 8px 0 0;
    padding: 8px;
    border-bottom: 1px solid alpha(@borders, 0.3);
}

/* Attachment Thumbnail */
.attachment-thumbnail {
    background-color: @card_bg_color;
    border-radius: 6px;
    padding: 4px;
}

.attachment-thumbnail:hover {
    background-color: alpha(@accent_bg_color, 0.1);
}

.attachment-thumbnail.upload-error {
    background-color: alpha(@error_bg_color, 0.2);
}

.attachment-frame {
    border-radius: 4px;
    overflow: hidden;
}

.attachment-image {
    min-width: 64px;
    min-height: 64px;
}

.attachment-remove-btn {
    margin: 2px;
    padding: 2px;
    min-width: 20px;
    min-height: 20px;
    background-color: alpha(@window_bg_color, 0.8);
}

.attachment-remove-btn:hover {
    background-color: @error_bg_color;
    color: @error_fg_color;
}

/* Attach Button */
.attach-button {
    padding: 8px;
}

.attach-button:hover {
    background-color: alpha(@accent_bg_color, 0.1);
}

/* Drop target highlight */
.drop-target-active {
    background-color: alpha(@accent_bg_color, 0.15);
    border: 2px dashed @accent_bg_color;
    border-radius: 8px;
}
```

---

#### Step 6: Update Window with Attachment Support

**File**: [`src/nanochat/ui/window.py`](src/nanochat/ui/window.py)

Make the following changes to add attachment support:

##### 6.1: Add Imports

At the top of the file, add these imports after the existing imports (around line 19):

```python
from pathlib import Path
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from nanochat.ui.attachments import (
    AttachmentType,
    PendingAttachment,
    create_pending_attachment,
    validate_attachment,
    IMAGE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
)
from nanochat.ui.attachment_preview import AttachmentPreviewBar
```

##### 6.2: Add Instance Variables

In the `__init__` method, add these instance variables after line 65 (after `_current_assistant_id`):

```python
# Attachment state
self._pending_attachments: list[PendingAttachment] = []
self._attachment_preview_bar: AttachmentPreviewBar | None = None
self._is_uploading: bool = False
```

##### 6.3: Update Input Area Creation

Replace the `_create_input_area` method (starting around line 237) with this updated version:

```python
def _create_input_area(self) -> Gtk.Box:
    """Create message input area with attachments and web search toggle."""
    # Outer container for preview bar + input
    outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    # Attachment preview bar (hidden by default)
    self._attachment_preview_bar = AttachmentPreviewBar(
        on_remove=self._on_attachment_remove
    )
    outer_box.append(self._attachment_preview_bar)

    # Input row
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.set_margin_bottom(12)
    box.add_css_class("chat-input-box")

    # Set up drop target for the input area
    self._setup_drop_target(box)

    # Attach button
    self.attach_btn = Gtk.Button(icon_name="mail-attachment-symbolic")
    self.attach_btn.set_tooltip_text("Attach files (images, PDFs, etc.)")
    self.attach_btn.add_css_class("flat")
    self.attach_btn.add_css_class("attach-button")
    self.attach_btn.connect("clicked", self._on_attach_clicked)
    box.append(self.attach_btn)

    # Web search toggle button
    self.web_search_btn = Gtk.ToggleButton()
    self.web_search_btn.set_icon_name("edit-find-symbolic")
    self.web_search_btn.set_tooltip_text("Enable web search")
    self.web_search_btn.add_css_class("flat")
    self.web_search_btn.add_css_class("web-search-toggle")
    self.web_search_btn.connect("toggled", self._on_web_search_toggled)
    box.append(self.web_search_btn)

    # Web search config popover (attached to toggle button)
    from nanochat.ui.web_search_config import WebSearchConfigPopover

    self.web_search_popover = WebSearchConfigPopover(
        initial_mode=self._web_search_mode,
        initial_provider=self._web_search_provider,
    )
    self.web_search_popover.set_parent(self.web_search_btn)
    self.web_search_popover.connect("settings-changed", self._on_web_search_settings_changed)

    # Add right-click handler for config popover
    right_click = Gtk.GestureClick()
    right_click.set_button(3)  # Right mouse button
    right_click.connect("pressed", self._on_web_search_right_click)
    self.web_search_btn.add_controller(right_click)

    # Add long-press handler for touch/mouse
    long_press = Gtk.GestureLongPress()
    long_press.connect("pressed", self._on_web_search_long_press)
    self.web_search_btn.add_controller(long_press)

    # Text entry (with linked styling)
    entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    entry_box.add_css_class("linked")
    entry_box.set_hexpand(True)

    self.message_entry = Gtk.Entry()
    self.message_entry.set_placeholder_text("Type a message...")
    self.message_entry.set_hexpand(True)
    self.message_entry.set_sensitive(True)
    self.message_entry.connect("activate", self._on_send)
    entry_box.append(self.message_entry)

    box.append(entry_box)

    # Send button
    self.send_btn = Gtk.Button(icon_name="mail-send-symbolic")
    self.send_btn.set_tooltip_text("Send Message")
    self.send_btn.add_css_class("suggested-action")
    self.send_btn.add_css_class("send-button")
    self.send_btn.set_sensitive(True)
    self.send_btn.connect("clicked", self._on_send)
    box.append(self.send_btn)

    outer_box.append(box)

    # Load saved web search preferences
    self._load_web_search_settings()

    return outer_box
```

##### 6.4: Add Drag and Drop Support

Add these new methods after `_create_input_area` (before `_setup_keyboard_shortcuts`):

```python
def _setup_drop_target(self, widget: Gtk.Widget) -> None:
    """Set up drag and drop target for file attachments."""
    drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
    drop_target.connect("enter", self._on_drop_enter)
    drop_target.connect("leave", self._on_drop_leave)
    drop_target.connect("drop", self._on_file_dropped)
    widget.add_controller(drop_target)

def _on_drop_enter(
    self,
    drop_target: Gtk.DropTarget,
    x: float,
    y: float,
) -> Gdk.DragAction:
    """Handle drag enter event."""
    widget = drop_target.get_widget()
    widget.add_css_class("drop-target-active")
    return Gdk.DragAction.COPY

def _on_drop_leave(self, drop_target: Gtk.DropTarget) -> None:
    """Handle drag leave event."""
    widget = drop_target.get_widget()
    widget.remove_css_class("drop-target-active")

def _on_file_dropped(
    self,
    drop_target: Gtk.DropTarget,
    value: Gio.File,
    x: float,
    y: float,
) -> bool:
    """Handle file dropped on input area."""
    widget = drop_target.get_widget()
    widget.remove_css_class("drop-target-active")

    file_path = Path(value.get_path())
    self._attach_file(file_path)
    return True
```

##### 6.5: Add Attachment Methods

Add these methods for handling attachments (after the drop methods):

```python
def _on_attach_clicked(self, button: Gtk.Button) -> None:
    """Handle attach button click - open file chooser."""
    dialog = Gtk.FileDialog()
    dialog.set_title("Attach Files")

    # Create filter for supported file types
    all_filter = Gtk.FileFilter()
    all_filter.set_name("All Supported Files")
    for ext in IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS:
        all_filter.add_suffix(ext.lstrip("."))

    image_filter = Gtk.FileFilter()
    image_filter.set_name("Images")
    for ext in IMAGE_EXTENSIONS:
        image_filter.add_suffix(ext.lstrip("."))

    doc_filter = Gtk.FileFilter()
    doc_filter.set_name("Documents")
    for ext in DOCUMENT_EXTENSIONS:
        doc_filter.add_suffix(ext.lstrip("."))

    filters = Gio.ListStore.new(Gtk.FileFilter)
    filters.append(all_filter)
    filters.append(image_filter)
    filters.append(doc_filter)
    dialog.set_filters(filters)
    dialog.set_default_filter(all_filter)

    dialog.open_multiple(self, None, self._on_files_selected)

def _on_files_selected(
    self,
    dialog: Gtk.FileDialog,
    result: Gio.AsyncResult,
) -> None:
    """Handle files selected from file chooser."""
    try:
        files = dialog.open_multiple_finish(result)
        for i in range(files.get_n_items()):
            gfile = files.get_item(i)
            file_path = Path(gfile.get_path())
            self._attach_file(file_path)
    except GLib.Error as e:
        if e.code != Gtk.DialogError.DISMISSED:
            self._show_error(f"Failed to select files: {e.message}")

def _attach_file(self, path: Path) -> None:
    """Attach a file to the pending message."""
    # Validate the file
    is_valid, error = validate_attachment(path)
    if not is_valid:
        self.toast_overlay.add_toast(Adw.Toast(title=f"Cannot attach: {error}"))
        return

    # Create pending attachment
    attachment = create_pending_attachment(path)
    if attachment is None:
        self.toast_overlay.add_toast(Adw.Toast(title="Unsupported file type"))
        return

    # Check for duplicates
    for existing in self._pending_attachments:
        if existing.path == path:
            self.toast_overlay.add_toast(Adw.Toast(title="File already attached"))
            return

    # Add to pending list and UI
    self._pending_attachments.append(attachment)
    self._attachment_preview_bar.add_attachment(attachment)

    # Show toast
    type_label = "image" if attachment.attachment_type == AttachmentType.IMAGE else "document"
    self.toast_overlay.add_toast(Adw.Toast(title=f"Attached {type_label}: {attachment.filename}"))

def _on_attachment_remove(self, attachment: PendingAttachment) -> None:
    """Handle removal of an attachment."""
    if attachment in self._pending_attachments:
        self._pending_attachments.remove(attachment)
    self._attachment_preview_bar.remove_attachment(attachment)

def _clear_attachments(self) -> None:
    """Clear all pending attachments."""
    self._pending_attachments.clear()
    self._attachment_preview_bar.clear()

async def _upload_attachments(self) -> bool:
    """Upload all pending attachments.

    Returns:
        True if all uploads succeeded, False otherwise
    """
    from nanochat.api.client import NanoChatClient

    url = self.settings_manager.settings.server.backend_url
    key = self.secrets_manager.get_api_key()

    if not url or not key:
        return False

    all_success = True

    async with NanoChatClient(url, key) as client:
        for attachment in self._pending_attachments:
            if attachment.is_uploaded:
                continue  # Already uploaded

            try:
                content = attachment.path.read_bytes()
                storage_id, file_url = await client.upload_file(
                    content,
                    attachment.filename,
                    attachment.mime_type,
                )
                attachment.storage_id = storage_id
                attachment.url = file_url
                logger.debug(f"Uploaded {attachment.filename}: {storage_id}")
            except Exception as e:
                attachment.upload_error = str(e)
                logger.error(f"Failed to upload {attachment.filename}: {e}")
                all_success = False

    return all_success
```

##### 6.6: Update Send Method

Modify the `_on_send` method (around line 1264) to include attachments. Replace the entire method:

```python
def _on_send(self, widget: Gtk.Widget) -> None:
    """Handle send button click."""
    if self._is_sending:
        return

    text = self.message_entry.get_text().strip()

    # Must have text or attachments
    if not text and not self._pending_attachments:
        return

    # Get selected model
    selected_idx = self.model_selector.get_selected()
    if selected_idx == Gtk.INVALID_LIST_POSITION or selected_idx >= len(self._model_ids):
        return

    model_id = self._model_ids[selected_idx]

    # Add user message to UI (with attachment indicator if any)
    display_text = text
    if self._pending_attachments:
        attachment_count = len(self._pending_attachments)
        attachment_label = "attachment" if attachment_count == 1 else "attachments"
        if text:
            display_text = f"{text}\n\n📎 {attachment_count} {attachment_label}"
        else:
            display_text = f"📎 {attachment_count} {attachment_label}"

    user_widget = MessageWidget(role="user", content=display_text)
    self.messages_list.append(user_widget)

    # Clear input and disable
    self.message_entry.set_text("")
    self._set_sending_state(True)

    # Capture attachments before clearing
    attachments_to_send = list(self._pending_attachments)
    self._clear_attachments()

    # Start upload and streaming in background
    url = self.settings_manager.settings.server.backend_url
    key = self.secrets_manager.get_api_key()

    def stream_response() -> None:
        import asyncio

        from nanochat.api.client import NanoChatClient
        from nanochat.api.models import (
            GenerateMessageRequest,
            ImageAttachment,
            DocumentAttachment,
        )

        async def do_upload_and_stream() -> None:
            # Upload attachments first
            if attachments_to_send:
                GLib.idle_add(
                    lambda: self.toast_overlay.add_toast(
                        Adw.Toast(title="Uploading attachments...")
                    )
                )

                async with NanoChatClient(url, key) as client:
                    for attachment in attachments_to_send:
                        if attachment.is_uploaded:
                            continue
                        try:
                            content = attachment.path.read_bytes()
                            storage_id, file_url = await client.upload_file(
                                content,
                                attachment.filename,
                                attachment.mime_type,
                            )
                            attachment.storage_id = storage_id
                            attachment.url = file_url
                        except Exception as e:
                            attachment.upload_error = str(e)
                            GLib.idle_add(
                                self._show_error,
                                f"Failed to upload {attachment.filename}: {e}"
                            )

            # Build attachment lists
            images = []
            documents = []

            for attachment in attachments_to_send:
                if not attachment.is_uploaded:
                    continue

                if attachment.attachment_type == AttachmentType.IMAGE:
                    images.append(ImageAttachment(
                        url=attachment.url,
                        storage_id=attachment.storage_id,
                        file_name=attachment.filename,
                    ))
                else:
                    documents.append(DocumentAttachment(
                        url=attachment.url,
                        storage_id=attachment.storage_id,
                        file_name=attachment.filename,
                        file_type=attachment.document_type.value if attachment.document_type else "text",
                    ))

            # Mutable state for accumulating content
            state = {"accumulated_content": "", "conversation_id": None}

            def on_event(event_type: str, event_data: dict) -> None:
                """Handle SSE events from the stream."""
                if event_type == "message_start":
                    conv_id = event_data.get("conversation_id")
                    if conv_id:
                        state["conversation_id"] = conv_id
                        GLib.idle_add(self._set_conversation_id, conv_id)

                elif event_type == "delta":
                    delta_content = event_data.get("content", "")
                    state["accumulated_content"] += delta_content
                    GLib.idle_add(self._update_assistant_message, state["accumulated_content"])

                elif event_type == "message_complete":
                    conv_id = state.get("conversation_id")
                    if conv_id:
                        def schedule_title_refresh() -> bool:
                            def do_refresh() -> bool:
                                self._refresh_conversation_title(conv_id)
                                return False
                            GLib.timeout_add(1000, do_refresh)
                            return False
                        GLib.idle_add(schedule_title_refresh)

                elif event_type == "error":
                    error_msg = event_data.get("error", "Unknown error")
                    GLib.idle_add(self._show_error, error_msg)

            # Build request
            request_kwargs = {
                "message": text if text else None,
                "model_id": model_id,
                "conversation_id": self._current_conversation_id,
            }

            if self._current_assistant_id:
                request_kwargs["assistant_id"] = self._current_assistant_id

            if self._web_search_enabled and self._web_search_mode != "off":
                request_kwargs["web_search_enabled"] = True
                request_kwargs["web_search_mode"] = self._web_search_mode
                request_kwargs["web_search_provider"] = self._web_search_provider

            if images:
                request_kwargs["images"] = images
            if documents:
                request_kwargs["documents"] = documents

            request = GenerateMessageRequest(**request_kwargs)

            try:
                async with NanoChatClient(url, key) as client:
                    await client.stream_generate_message(request, on_event)
            except Exception as e:
                import traceback
                traceback.print_exc()
                GLib.idle_add(self._show_error, str(e))
            finally:
                GLib.idle_add(self._set_sending_state, False)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(do_upload_and_stream())
            loop.close()
        except Exception as e:
            GLib.idle_add(self._show_error, str(e))
            GLib.idle_add(self._set_sending_state, False)

    thread = threading.Thread(target=stream_response, daemon=True)
    thread.start()
```

##### 6.7: Update the `new_conversation` Method

Update the `new_conversation` method (around line 1502) to also clear attachments:

```python
def new_conversation(self) -> None:
    """Start a new conversation."""
    # Clear current conversation
    self._current_conversation_id = None

    # Clear messages
    child = self.messages_list.get_first_child()
    while child is not None:
        next_child = child.get_next_sibling()
        self.messages_list.remove(child)
        child = next_child

    # Clear attachments
    self._clear_attachments()

    # Clear selection in list
    self.conversation_list.unselect_all()
```

---

#### Step 7: Load CSS Styles

**File**: [`src/nanochat/application.py`](src/nanochat/application.py)

Add code to load the attachment CSS when the app starts. Find where other CSS is loaded and add:

```python
# Load attachment styles
attachment_css_path = Path(__file__).parent.parent.parent / "data" / "styles" / "attachments.css"
if attachment_css_path.exists():
    css_provider = Gtk.CssProvider()
    css_provider.load_from_path(str(attachment_css_path))
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
```

---

#### Testing Checklist

After implementation, verify:

- [ ] Attach button opens file chooser
- [ ] File chooser filters show correctly (All, Images, Documents)
- [ ] Selecting files adds thumbnails to preview bar
- [ ] Image thumbnails show actual image preview
- [ ] Document thumbnails show appropriate icon
- [ ] Remove button removes attachment from preview
- [ ] Drag and drop files onto input area adds attachments
- [ ] Drop zone highlights when dragging over
- [ ] Invalid files show error toast
- [ ] Duplicate files show warning toast
- [ ] Sending with attachments uploads files first
- [ ] Upload errors display in UI
- [ ] Message shows attachment indicator
- [ ] Attachments are included in API request
- [ ] New conversation clears pending attachments
- [ ] Large files are rejected with appropriate message

---

## Feature 2: Message Copy Button

### Summary

Add a copy button to message widgets that appears on hover, allowing users to copy the message content to clipboard with a single click.

### Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│ MessageWidget                                                   │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ Header: Role Label              [Copy Button] (on hover)   │ │
│ ├────────────────────────────────────────────────────────────┤ │
│ │                                                            │ │
│ │ Message Content                                            │ │
│ │                                                            │ │
│ └────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### Implementation Steps

---

#### Step 1: Update MessageWidget Class

**File**: [`src/nanochat/ui/message_widget.py`](src/nanochat/ui/message_widget.py)

Replace the entire file with the updated implementation:

```python
"""Widget for displaying a single chat message."""

import re
from collections.abc import Callable
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Pango, Gdk, GLib

# Pre-compiled regex patterns for markdown parsing (performance optimization)
_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"\*([^*]+)\*")

# Security: Only allow safe URL schemes for links
_ALLOWED_URL_SCHEMES = ("http://", "https://", "mailto:")

# Maximum content length to prevent DoS via extremely long messages
_MAX_CONTENT_LENGTH = 5000


class MessageWidget(Adw.Bin):  # type: ignore[misc]
    """Widget for displaying a single chat message with improved styling."""

    def __init__(self, role: str, content: str, **kwargs: object) -> None:
        super().__init__(**kwargs)

        self.role = role
        self.content = content
        self._content_label: Optional[Gtk.Label] = None
        self._copy_btn: Optional[Gtk.Button] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the message UI with improved styling."""
        # Main container with message widget class for CSS targeting
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        container.add_css_class("message-widget")

        # Add role-specific CSS class
        if self.role == "user":
            container.add_css_class("user")
        else:
            container.add_css_class("assistant")

        # Header row with role label and copy button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_hexpand(True)

        # Role label with improved styling
        role_label = Gtk.Label()
        role_label.set_halign(Gtk.Align.START)
        role_label.set_hexpand(True)
        role_label.add_css_class("message-role-label")

        if self.role == "user":
            role_label.set_text("You")
            role_label.add_css_class("user")
        else:
            role_label.set_text("Assistant")
            role_label.add_css_class("assistant")

        header_box.append(role_label)

        # Copy button (hidden by default, shown on hover)
        self._copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        self._copy_btn.add_css_class("flat")
        self._copy_btn.add_css_class("circular")
        self._copy_btn.add_css_class("message-copy-btn")
        self._copy_btn.set_tooltip_text("Copy message")
        self._copy_btn.set_valign(Gtk.Align.CENTER)
        self._copy_btn.set_opacity(0)
        self._copy_btn.connect("clicked", self._on_copy_clicked)
        header_box.append(self._copy_btn)

        container.append(header_box)

        # Content container with card-like styling
        content_frame = Adw.Bin()
        content_frame.add_css_class("message-content")

        # Render content with basic markdown
        # Apply length limit only to user input, not server responses
        content_to_render = self.content
        if self.role == "user" and len(content_to_render) > _MAX_CONTENT_LENGTH:
            content_to_render = content_to_render[:_MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"
        rendered_content = self._render_markdown(content_to_render)

        # Content label with better typography
        self._content_label = Gtk.Label(label=rendered_content)
        self._content_label.set_halign(Gtk.Align.START)
        self._content_label.set_hexpand(True)
        self._content_label.set_wrap(True)
        self._content_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._content_label.set_xalign(0.0)
        self._content_label.set_selectable(True)
        self._content_label.add_css_class("body")

        # Use Pango markup for formatted content
        self._content_label.set_use_markup(True)

        content_frame.set_child(self._content_label)
        container.append(content_frame)

        # Add hover controller for showing/hiding copy button
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("enter", self._on_mouse_enter)
        motion_controller.connect("leave", self._on_mouse_leave)
        container.add_controller(motion_controller)

        self.set_child(container)

    def _on_mouse_enter(
        self,
        controller: Gtk.EventControllerMotion,
        x: float,
        y: float,
    ) -> None:
        """Show copy button on hover."""
        if self._copy_btn:
            self._copy_btn.set_opacity(1)

    def _on_mouse_leave(self, controller: Gtk.EventControllerMotion) -> None:
        """Hide copy button when mouse leaves."""
        if self._copy_btn:
            self._copy_btn.set_opacity(0)

    def _on_copy_clicked(self, button: Gtk.Button) -> None:
        """Copy message content to clipboard."""
        # Get the raw content (without markdown rendering)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(self.content)

        # Show feedback by temporarily changing icon
        button.set_icon_name("object-select-symbolic")
        button.set_tooltip_text("Copied!")

        # Reset icon after delay
        def reset_icon() -> bool:
            button.set_icon_name("edit-copy-symbolic")
            button.set_tooltip_text("Copy message")
            return False  # Don't repeat

        GLib.timeout_add(1500, reset_icon)

        # Also show toast if we can find the toast overlay
        self._show_copy_toast()

    def _show_copy_toast(self) -> None:
        """Try to show a toast notification for copy action."""
        # Walk up the widget hierarchy to find a ToastOverlay
        widget = self.get_parent()
        while widget is not None:
            if hasattr(widget, "toast_overlay"):
                widget.toast_overlay.add_toast(Adw.Toast(title="Copied to clipboard"))
                return
            # Check if this IS a ToastOverlay
            if isinstance(widget, Adw.ToastOverlay):
                widget.add_toast(Adw.Toast(title="Copied to clipboard"))
                return
            widget = widget.get_parent()

    def _render_markdown(self, text: str) -> str:
        """Convert basic markdown to Pango markup.

        Supports:
        - **bold** → <b>
        - *italic* → <i>
        - `inline code` → <tt>
        - ```code blocks``` → formatted blocks
        - [links](url) → clickable links (http/https/mailto only)

        Security: URLs are validated to only allow safe schemes.
        """
        if not text:
            return ""

        # Process in order: code blocks, inline code, links, bold, italic
        # Each replacement returns a list of (text, is_markup) tuples

        parts: list[tuple[str, bool]] = [(text, False)]

        # Helper to process parts list
        def process_parts(
            regex: re.Pattern[str],
            replacer: Callable[[re.Match[str]], str],
        ) -> list[tuple[str, bool]]:
            new_parts: list[tuple[str, bool]] = []
            for part_text, is_markup in parts:
                if is_markup:
                    new_parts.append((part_text, True))
                else:
                    last_end = 0
                    for match in regex.finditer(part_text):
                        # Add text before match
                        if match.start() > last_end:
                            new_parts.append((part_text[last_end:match.start()], False))
                        # Add replacement (markup)
                        new_parts.append((replacer(match), True))
                        last_end = match.end()
                    # Add remaining text
                    if last_end < len(part_text):
                        new_parts.append((part_text[last_end:], False))
            return new_parts

        # Code blocks ```code```
        def replace_code_block(match: re.Match[str]) -> str:
            code = match.group(2)
            escaped = GLib.markup_escape_text(code)
            return f'<span font_family="monospace" bgcolor="alpha(@shade_color,0.2)" padding="8" rise="8">{escaped}</span>'

        parts = process_parts(_CODE_BLOCK_RE, replace_code_block)

        # Inline code `code`
        def replace_inline_code(match: re.Match[str]) -> str:
            code = match.group(1)
            escaped = GLib.markup_escape_text(code)
            return f'<tt font_family="monospace" bgcolor="alpha(@shade_color,0.15)">{escaped}</tt>'

        parts = process_parts(_INLINE_CODE_RE, replace_inline_code)

        # Links [text](url) - with URL scheme validation
        def replace_link(match: re.Match[str]) -> str:
            text_content = match.group(1)
            url = match.group(2)

            # Security: Only allow safe URL schemes
            if not url.lower().startswith(_ALLOWED_URL_SCHEMES):
                # Render as plain text, not a clickable link
                return GLib.markup_escape_text(match.group(0))

            escaped_text = GLib.markup_escape_text(text_content)
            escaped_url = GLib.markup_escape_text(url)
            return f'<a href="{escaped_url}">{escaped_text}</a>'

        parts = process_parts(_LINK_RE, replace_link)

        # Bold **text**
        def replace_bold(match: re.Match[str]) -> str:
            content = match.group(1)
            escaped = GLib.markup_escape_text(content)
            return f"<b>{escaped}</b>"

        parts = process_parts(_BOLD_RE, replace_bold)

        # Italic *text*
        def replace_italic(match: re.Match[str]) -> str:
            content = match.group(1)
            escaped = GLib.markup_escape_text(content)
            return f"<i>{escaped}</i>"

        parts = process_parts(_ITALIC_RE, replace_italic)

        # Combine parts
        result = []
        for part_text, is_markup in parts:
            if is_markup:
                result.append(part_text)
            else:
                result.append(GLib.markup_escape_text(part_text))

        return "".join(result)

    def update_content(self, content: str) -> None:
        """Update message content (for streaming)."""
        self.content = content
        if self._content_label:
            # Apply length limit only to user input, not server responses
            content_to_render = content
            if self.role == "user" and len(content_to_render) > _MAX_CONTENT_LENGTH:
                content_to_render = content_to_render[:_MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"
            self._content_label.set_label(self._render_markdown(content_to_render))
```

---

#### Step 2: Add CSS Styles for Copy Button

**File**: Add these styles to an existing CSS file or create `data/styles/message.css`:

```css
/* Message Copy Button */
.message-copy-btn {
    min-width: 24px;
    min-height: 24px;
    padding: 4px;
    transition: opacity 200ms ease-in-out;
}

.message-copy-btn:hover {
    background-color: alpha(@accent_bg_color, 0.15);
}

/* Ensure button is visible when message is hovered */
.message-widget:hover .message-copy-btn {
    opacity: 1;
}
```

If creating a new file, also load it in [`src/nanochat/application.py`](src/nanochat/application.py) similar to the attachment styles.

---

#### Step 3: Update Window for Toast Access

The copy button needs access to the toast overlay. The current implementation walks up the widget tree to find it, but we can also make it more reliable by ensuring the `NanoChatWindow` class adds itself as a reference.

This is already handled in the `_show_copy_toast` method which walks up the widget hierarchy, so no additional changes are needed to [`window.py`](src/nanochat/ui/window.py).

---

#### Testing Checklist

After implementation, verify:

- [ ] Copy button appears on message hover
- [ ] Copy button hidden when not hovering
- [ ] Clicking copy button copies raw content to clipboard
- [ ] Icon changes to checkmark after copy
- [ ] Icon resets after 1.5 seconds
- [ ] Toast notification appears confirming copy
- [ ] Works for both user and assistant messages
- [ ] Copying long messages works correctly
- [ ] Copying messages with markdown copies raw markdown, not rendered HTML
- [ ] Button styling matches the app theme

---

## Implementation Order

Recommended order for implementing these features:

1. **Message Copy Button** (simpler, fewer files to modify)
   - Update `message_widget.py`
   - Add CSS styles
   - Test

2. **File Attachments** (more complex, multiple new files)
   - Add API client methods
   - Create attachment data structures
   - Create attachment preview widget
   - Add CSS styles
   - Update window.py
   - Test thoroughly

---

## Files Summary

### New Files to Create

| File | Description |
|------|-------------|
| `src/nanochat/ui/attachments.py` | Attachment data classes and utilities |
| `src/nanochat/ui/attachment_preview.py` | Attachment preview bar widget |
| `data/styles/attachments.css` | CSS styles for attachments |

### Files to Modify

| File | Changes |
|------|---------|
| `src/nanochat/api/client.py` | Add `upload_file` and `delete_file` methods |
| `src/nanochat/api/models.py` | Add `ImageAttachment`, `DocumentAttachment` models, update `GenerateMessageRequest` |
| `src/nanochat/ui/message_widget.py` | Add copy button with hover behavior |
| `src/nanochat/ui/window.py` | Add attachment support, drag-drop, file chooser |
| `src/nanochat/application.py` | Load CSS styles |

---

## Notes for Implementation

1. **Error Handling**: All file operations should have proper try/except blocks with user-friendly error messages.

2. **Threading**: File uploads must happen in background threads to avoid blocking the UI.

3. **Memory**: Large image thumbnails should be properly disposed to avoid memory leaks.

4. **Security**: File validation should check both extension and MIME type where possible.

5. **Accessibility**: All buttons should have tooltips and proper labels for screen readers.

6. **Testing**: Test with various file types, sizes, and edge cases (empty files, very long filenames, special characters in filenames).
