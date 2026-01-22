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
            # Use simple gray background (#f0f0f0) - alpha() and padding not supported in Pango
            return f'<span font_family="monospace" bgcolor="#f0f0f0">{escaped}</span>'

        parts = process_parts(_CODE_BLOCK_RE, replace_code_block)

        # Inline code `code`
        def replace_inline_code(match: re.Match[str]) -> str:
            code = match.group(1)
            escaped = GLib.markup_escape_text(code)
            # Use <span> instead of <tt> because <tt> doesn't support attributes
            # Use simple gray background (#f5f5f5) - alpha() not supported in Pango
            return f'<span font_family="monospace" bgcolor="#f5f5f5">{escaped}</span>'

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
