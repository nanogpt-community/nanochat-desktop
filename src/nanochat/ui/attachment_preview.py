"""Attachment preview widgets for the input area."""

from pathlib import Path
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
        self._thumbnails: dict[Path, tuple[PendingAttachment, AttachmentThumbnail]] = {}

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
        self._thumbnails[attachment.path] = (attachment, thumbnail)
        self._box.append(thumbnail)
        self.set_visible(True)

    def remove_attachment(self, attachment: PendingAttachment) -> None:
        """Remove an attachment from the preview bar."""
        if attachment.path in self._thumbnails:
            _, thumbnail = self._thumbnails.pop(attachment.path)
            self._box.remove(thumbnail)

        # Hide if empty
        if not self._thumbnails:
            self.set_visible(False)

    def clear(self) -> None:
        """Remove all attachments."""
        for _, thumbnail in list(self._thumbnails.values()):
            self._box.remove(thumbnail)
        self._thumbnails.clear()
        self.set_visible(False)

    def update_attachment(self, attachment: PendingAttachment) -> None:
        """Update display for an attachment (e.g., after upload)."""
        if attachment.path in self._thumbnails:
            # Rebuild the thumbnail
            _, old_thumbnail = self._thumbnails[attachment.path]
            new_thumbnail = AttachmentThumbnail(attachment, self._on_remove)
            self._thumbnails[attachment.path] = (attachment, new_thumbnail)

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
        return [attachment for attachment, _ in self._thumbnails.values()]
