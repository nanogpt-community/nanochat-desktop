# Issue #11: Add text about NanoChat server required

**Issue URL**: https://github.com/nanogpt-community/nanochat-desktop/issues/11
**Status**: OPEN
**Priority**: MEDIUM

## Description
In the settings screen where you input the server URL and API key, we need to add a note about this being for a self-hosted or public instance of NanoChat (https://github.com/nanogpt-community/nanochat). This will prevent confusion about what URL to use.

Also need to update the README with the GitHub URL and update the About section as well.

## Objective
Improve documentation and user guidance by:
- Adding explanatory text in the settings screen about the NanoChat server requirement
- Updating the README with clear setup instructions
- Updating the About section with GitHub repository link
- Providing examples of valid server URLs

## Technical Context
- **File Location**: 
  - `src/ui/settings_window.py` - Settings UI
  - `README.md` - Project documentation
  - About section (from Issue #13)
- **Tech Stack**: GTK4/Libadwaita for UI
- **Related Resources**:
  - NanoChat server repo: https://github.com/nanogpt-community/nanochat
  - Desktop client repo: https://github.com/nanogpt-community/nanochat-desktop

## Implementation Plan

### Step 1: Update Settings Screen UI
**Files to modify**: `src/ui/settings_window.py`

Add informative text and help content to the server settings section:

```python
class SettingsWindow(Adw.PreferencesWindow):
    def _create_server_settings_page(self):
        server_page = Adw.PreferencesPage(title="Server")
        
        # Information group with explanation
        info_group = Adw.PreferencesGroup(
            title="Server Configuration",
            description="NanoChat Desktop requires a NanoChat server instance. "
                       "You can use a self-hosted server or connect to a public instance."
        )
        
        # Add info row with link to server repo
        server_info_row = Adw.ActionRow(
            title="About NanoChat Server",
            subtitle="Learn how to set up your own server",
            activatable=True
        )
        server_info_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        server_info_row.connect("activated", self._on_server_info_clicked)
        info_group.add(server_info_row)
        
        # Server URL input
        server_group = Adw.PreferencesGroup(title="Connection Settings")
        
        server_url_row = Adw.EntryRow(
            title="Server URL",
        )
        server_url_row.set_text(self.settings.get_server_url())
        server_url_row.connect("changed", self._on_server_url_changed)
        
        # Add help text below the entry
        server_url_help = Gtk.Label(
            label="Example: https://nanochat.example.com or http://localhost:3000",
            wrap=True,
            xalign=0,
        )
        server_url_help.add_css_class("dim-label")
        server_url_help.add_css_class("caption")
        
        server_group.add(server_url_row)
        
        # API Key input
        api_key_row = Adw.PasswordEntryRow(
            title="API Key",
        )
        api_key_row.set_text(self.settings.get_api_key())
        api_key_row.connect("changed", self._on_api_key_changed)
        
        api_key_help = Gtk.Label(
            label="Get your API key from the server's settings page",
            wrap=True,
            xalign=0,
        )
        api_key_help.add_css_class("dim-label")
        api_key_help.add_css_class("caption")
        
        server_group.add(api_key_row)
        
        # Test connection button
        test_button = Gtk.Button(label="Test Connection")
        test_button.add_css_class("suggested-action")
        test_button.connect("clicked", self._on_test_connection)
        
        button_row = Adw.ActionRow()
        button_row.add_suffix(test_button)
        server_group.add(button_row)
        
        server_page.add(info_group)
        server_page.add(server_group)
        
        return server_page
    
    def _on_server_info_clicked(self, widget):
        """Open NanoChat server repository in browser"""
        Gtk.show_uri(
            None,
            "https://github.com/nanogpt-community/nanochat",
            Gdk.CURRENT_TIME
        )
```

### Step 2: Add Welcome/First Run Dialog
**Files to create**: `src/ui/welcome_dialog.py`

Create a first-run experience that explains the server requirement:

```python
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

class WelcomeDialog(Adw.Window):
    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            modal=True,
            default_width=500,
            default_height=400
        )
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Header
        header = Adw.HeaderBar()
        
        # Content
        content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            margin_top=48,
            margin_bottom=48,
            margin_start=48,
            margin_end=48
        )
        
        # Welcome message
        title = Gtk.Label(
            label="Welcome to NanoChat Desktop",
            wrap=True
        )
        title.add_css_class("title-1")
        
        subtitle = Gtk.Label(
            label="A native Linux client for NanoChat",
            wrap=True
        )
        subtitle.add_css_class("title-3")
        subtitle.add_css_class("dim-label")
        
        # Server requirement explanation
        info = Gtk.Label(
            label="To use NanoChat Desktop, you need access to a NanoChat server. "
                  "This can be either:\\n\\n"
                  "• A self-hosted instance (recommended for privacy)\\n"
                  "• A public instance provided by someone else\\n\\n"
                  "The server handles all AI model interactions and stores your conversations.",
            wrap=True,
            justify=Gtk.Justification.LEFT
        )
        
        # Link to server repo
        server_link = Gtk.LinkButton(
            uri="https://github.com/nanogpt-community/nanochat",
            label="Learn how to set up a NanoChat server"
        )
        
        # Action buttons
        button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            halign=Gtk.Align.CENTER
        )
        
        setup_button = Gtk.Button(label="Set Up Server Connection")
        setup_button.add_css_class("suggested-action")
        setup_button.add_css_class("pill")
        setup_button.connect("clicked", self._on_setup_clicked)
        
        button_box.append(setup_button)
        
        # Layout
        content_box.append(title)
        content_box.append(subtitle)
        content_box.append(info)
        content_box.append(server_link)
        content_box.append(button_box)
        
        # Main container
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(content_box)
        
        self.set_content(toolbar_view)
    
    def _on_setup_clicked(self, button):
        self.emit("setup-requested")
        self.close()
```

### Step 3: Update README.md
**Files to modify**: `README.md`

Add comprehensive setup instructions:

```markdown
# NanoChat Desktop

A native Linux desktop application for [NanoChat](https://github.com/nanogpt-community/nanochat), built with GTK4 and Libadwaita.

## Features

- Native GTK4/Libadwaita interface
- Real-time message streaming
- Offline conversation caching
- Multiple model support
- Markdown rendering
- Light and dark theme support

## Prerequisites

⚠️ **Important**: NanoChat Desktop requires a NanoChat server to function.

You need access to a NanoChat server instance. You can either:

1. **Self-host a server** (recommended for privacy):
   - Follow the setup instructions at: https://github.com/nanogpt-community/nanochat
   - Requires Node.js and a database (PostgreSQL/SQLite)
   
2. **Use a public instance**:
   - Ask the server administrator for the server URL and an API key
   - Public instances may have usage limits or require registration

## Installation

### Via Flatpak (Recommended)

Download the latest `.flatpak` file from [Releases](https://github.com/nanogpt-community/nanochat-desktop/releases):

```bash
flatpak install --user nanochat-desktop-v0.2.0.flatpak
flatpak run com.nanogpt.NanoChat
```

### From Source

Requirements:
- Python 3.11+
- GTK 4.0+
- Libadwaita 1.0+

```bash
git clone https://github.com/nanogpt-community/nanochat-desktop.git
cd nanochat-desktop
pip install -e .
python -m nanochat
```

## Configuration

On first run, you'll need to configure:

1. **Server URL**: The URL of your NanoChat server
   - Example: `https://nanochat.example.com`
   - Or for local development: `http://localhost:3000`

2. **API Key**: Your authentication key from the server
   - Generate this in your NanoChat server's settings

To access settings:
- Click the menu button (☰) → Settings
- Or press `Ctrl+,`

## Usage

1. Launch the application
2. Create a new conversation or select an existing one
3. Type your message and press Enter or click Send
4. View AI responses in real-time

### Keyboard Shortcuts

- `Ctrl+N` - New conversation
- `Ctrl+,` - Settings
- `Ctrl+Q` - Quit

## Development

See [CLAUDE.md](CLAUDE.md) for development instructions and architecture documentation.

## Support

- Report issues: https://github.com/nanogpt-community/nanochat-desktop/issues
- NanoChat server: https://github.com/nanogpt-community/nanochat

## License

MIT License - see [LICENSE](LICENSE) file for details
```

### Step 4: Integration Testing

**Manual Testing Checklist**:
- [ ] Settings screen shows clear explanation text
- [ ] Server info link opens correct GitHub repository
- [ ] Example URLs are helpful and accurate
- [ ] Welcome dialog appears on first run (if implemented)
- [ ] README is clear and comprehensive
- [ ] All GitHub links are correct and working
- [ ] Documentation covers both self-hosted and public instances

### Step 5: User Experience Validation

Test with someone unfamiliar with the project:
- Can they understand what a "NanoChat server" is?
- Do they know how to get started?
- Is it clear where to get an API key?
- Are the example URLs helpful?

## Files to Create/Modify

### New Files
- `src/ui/welcome_dialog.py` - First-run welcome experience (optional)

### Modified Files
- `src/ui/settings_window.py` - Add explanatory text and help
- `README.md` - Complete setup instructions
- `src/ui/about_dialog.py` - Update GitHub links (related to Issue #13)

## Dependencies
- No new dependencies required
- Uses existing GTK4/Libadwaita components

## Acceptance Criteria
- [ ] Settings screen clearly explains NanoChat server requirement
- [ ] Link to NanoChat server repository is present and functional
- [ ] Example server URLs are shown
- [ ] README has comprehensive setup instructions
- [ ] README links to both desktop and server repositories
- [ ] Documentation explains self-hosted vs public instance options
- [ ] First-time users understand what they need to do

## Potential Issues & Solutions

**Issue**: Users still confused about what server URL to use
**Solution**: Add more specific examples, maybe a "Quick Start" guide

**Issue**: Link doesn't open on some systems
**Solution**: Use `Gtk.show_uri()` with proper error handling

**Issue**: Users don't read the documentation
**Solution**: Add inline help, tooltips, and a welcome dialog on first run

## Related Issues
- Issue #13 - Add version number to settings screen (About section)

## Estimated Effort
**Time**: 2-3 hours
**Complexity**: Low
**Risk**: Low

## Additional Notes
- Consider adding a "Getting Started" guide in the app itself
- Could add a server connectivity test before allowing configuration save
- May want to add common server URL suggestions/templates
- Future: Add server discovery mechanism (if feasible)
- Consider adding screenshots to README
