"""Widget for displaying a single message."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Pango


class MessageWidget(Adw.Bin):  # type: ignore[misc]
    """Widget for displaying a single chat message."""

    def __init__(self, role: str, content: str, **kwargs: object) -> None:
        super().__init__(**kwargs)

        self.role = role
        self.content = content

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the message UI."""
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        # Role label
        role_label = Gtk.Label()
        role_label.set_halign(Gtk.Align.START)
        role_label.add_css_class("caption")
        role_label.add_css_class("dim-label")

        if self.role == "user":
            role_label.set_text("You")
            role_label.add_css_class("accent")
        else:
            role_label.set_text("Assistant")

        container.append(role_label)

        # Content label
        content_label = Gtk.Label(label=self.content)
        content_label.set_halign(Gtk.Align.START)
        content_label.set_hexpand(True)
        content_label.set_wrap(True)
        content_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        content_label.set_xalign(0.0)
        content_label.set_margin_start(8)
        content_label.set_margin_end(8)
        content_label.add_css_class("body")

        # Content in a styled frame
        content_frame = Adw.Bin()
        content_frame.set_child(content_label)

        if self.role == "user":
            content_frame.add_css_class("card")
        else:
            content_frame.add_css_class("card")

        container.append(content_frame)

        self.set_child(container)

    def update_content(self, content: str) -> None:
        """Update message content (for streaming)."""
        self.content = content
        # Rebuild UI
        child = self.get_child()
        if child:
            self.set_child(None)
        self._build_ui()
