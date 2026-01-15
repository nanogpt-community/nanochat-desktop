"""Widget for displaying a single chat message."""

import re
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Pango, Gdk, GLib


class MessageWidget(Adw.Bin):  # type: ignore[misc]
    """Widget for displaying a single chat message with improved styling."""

    def __init__(self, role: str, content: str, **kwargs: object) -> None:
        super().__init__(**kwargs)

        self.role = role
        self.content = content
        self._content_label: Optional[Gtk.Label] = None

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

        # Role label with improved styling
        role_label = Gtk.Label()
        role_label.set_halign(Gtk.Align.START)
        role_label.add_css_class("message-role-label")

        if self.role == "user":
            role_label.set_text("You")
            role_label.add_css_class("user")
        else:
            role_label.set_text("Assistant")
            role_label.add_css_class("assistant")

        container.append(role_label)

        # Content container with card-like styling
        content_frame = Adw.Bin()
        content_frame.add_css_class("message-content")

        # Render content with basic markdown
        rendered_content = self._render_markdown(self.content)

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

        self.set_child(container)

    def _render_markdown(self, text: str) -> str:
        """Convert basic markdown to Pango markup.

        Supports:
        - **bold** → <b>
        - *italic* → <i>
        - `inline code` → <tt>
        - ```code blocks``` → formatted blocks
        - [links](url) → clickable links
        """
        if not text:
            return ""

        # Process in order: code blocks, inline code, links, bold, italic
        # Each replacement returns a list of (text, is_markup) tuples

        parts = [(text, False)]

        # Helper to process parts list
        def process_parts(regex: re.Pattern[str], replacer: object) -> None:
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
            parts.clear()
            parts.extend(new_parts)

        # Code blocks ```code```
        def replace_code_block(match: re.Match[str]) -> str:
            code = match.group(2)
            escaped = GLib.markup_escape_text(code)
            return f'<span font_family="monospace" bgcolor="alpha(@shade_color,0.2)" padding="8" rise="8">{escaped}</span>'

        process_parts(re.compile(r"```(\w*)\n(.*?)```", re.DOTALL), replace_code_block)

        # Inline code `code`
        def replace_inline_code(match: re.Match[str]) -> str:
            code = match.group(1)
            escaped = GLib.markup_escape_text(code)
            return f'<tt font_family="monospace" bgcolor="alpha(@shade_color,0.15)">{escaped}</tt>'

        process_parts(re.compile(r"`([^`]+)`"), replace_inline_code)

        # Links [text](url)
        def replace_link(match: re.Match[str]) -> str:
            text_content = match.group(1)
            url = match.group(2)
            escaped_text = GLib.markup_escape_text(text_content)
            escaped_url = GLib.markup_escape_text(url)
            return f'<a href="{escaped_url}">{escaped_text}</a>'

        process_parts(re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), replace_link)

        # Bold **text**
        def replace_bold(match: re.Match[str]) -> str:
            content = match.group(1)
            escaped = GLib.markup_escape_text(content)
            return f"<b>{escaped}</b>"

        process_parts(re.compile(r"\*\*([^*]+)\*\*"), replace_bold)

        # Italic *text*
        def replace_italic(match: re.Match[str]) -> str:
            content = match.group(1)
            escaped = GLib.markup_escape_text(content)
            return f"<i>{escaped}</i>"

        process_parts(re.compile(r"\*([^*]+)\*"), replace_italic)

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
            self._content_label.set_label(self._render_markdown(content))
