"""Keyboard shortcuts help window."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk


def create_shortcuts_window(parent: Gtk.Window) -> Gtk.ShortcutsWindow:
    """Create and return a shortcuts help window."""
    window = Gtk.ShortcutsWindow(transient_for=parent, modal=True)

    section = Gtk.ShortcutsSection(section_name="shortcuts", title="All Shortcuts")
    section.set_visible(True)

    # Global shortcuts group
    global_group = Gtk.ShortcutsGroup(title="Global")
    global_group.set_visible(True)

    shortcuts = [
        ("<Control>n", "New conversation"),
        ("<Control>q", "Quit"),
        ("<Control>comma", "Settings"),
        ("<Control><Shift>c", "Copy last response"),
        ("F1", "Show this help"),
    ]

    for accel, title in shortcuts:
        shortcut = Gtk.ShortcutsShortcut(
            shortcut_type=Gtk.ShortcutType.ACCELERATOR,
            accelerator=accel,
            title=title,
        )
        shortcut.set_visible(True)
        global_group.append(shortcut)

    section.append(global_group)

    # Chat shortcuts group
    chat_group = Gtk.ShortcutsGroup(title="Chat")
    chat_group.set_visible(True)

    chat_shortcuts = [
        ("<Control>Return", "Send message"),
        ("Escape", "Cancel/close dialogs"),
    ]

    for accel, title in chat_shortcuts:
        shortcut = Gtk.ShortcutsShortcut(
            shortcut_type=Gtk.ShortcutType.ACCELERATOR,
            accelerator=accel,
            title=title,
        )
        shortcut.set_visible(True)
        chat_group.append(shortcut)

    section.append(chat_group)

    # Sidebar shortcuts group
    sidebar_group = Gtk.ShortcutsGroup(title="Sidebar")
    sidebar_group.set_visible(True)

    sidebar_shortcuts = [
        ("<Control>k", "Focus search"),
        ("Up", "Navigate to previous conversation"),
        ("Down", "Navigate to next conversation"),
        ("Return", "Load selected conversation"),
        ("F2", "Rename conversation"),
    ]

    for accel, title in sidebar_shortcuts:
        shortcut = Gtk.ShortcutsShortcut(
            shortcut_type=Gtk.ShortcutType.ACCELERATOR,
            accelerator=accel,
            title=title,
        )
        shortcut.set_visible(True)
        sidebar_group.append(shortcut)

    section.append(sidebar_group)

    window.add_section(section)

    return window
