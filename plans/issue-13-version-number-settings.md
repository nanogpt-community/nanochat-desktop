# Issue #13: Add version number to settings screen

**Issue URL**: https://github.com/nanogpt-community/nanochat-desktop/issues/13
**Status**: OPEN
**Priority**: LOW

## Description
Need to add an "about" tab in the settings screen, linking to Github and showing the version number.

## Objective
Add an About section to the settings screen that displays:
- Application version number
- Link to the GitHub repository
- Other relevant application information

## Technical Context
- **File Location**: `src/ui/settings_window.py` or similar
- **Tech Stack**: GTK4/Libadwaita
- **Related Files**: 
  - `flatpak/com.nanogpt.NanoChat.yml` (for version number)
  - Application metadata files

## Implementation Plan

### Step 1: Define Version Constant
**Files to modify**: `src/__init__.py` or `src/version.py`

Create a version constant that can be accessed throughout the application:

```python
# src/version.py
__version__ = "0.2.0"  # Update based on current version
APP_NAME = "NanoChat Desktop"
GITHUB_URL = "https://github.com/nanogpt-community/nanochat-desktop"
```

### Step 2: Create About Dialog/Section
**Files to modify**: `src/ui/settings_window.py`

Add an "About" section to the settings window using Libadwaita's AdwAboutWindow or create a custom section:

**Option A: Use AdwAboutWindow (Recommended)**
```python
from gi.repository import Adw
from nanochat.version import __version__, APP_NAME, GITHUB_URL

def show_about_dialog(parent_window):
    about = Adw.AboutWindow(
        transient_for=parent_window,
        application_name=APP_NAME,
        application_icon="com.nanogpt.NanoChat",
        developer_name="NanoGPT Community",
        version=__version__,
        website=GITHUB_URL,
        issue_url=f"{GITHUB_URL}/issues",
        copyright="© 2024 NanoGPT Community",
        license_type=Gtk.License.MIT_X11,  # Adjust based on actual license
    )
    about.present()
```

**Option B: Add to Settings Window**
Add a new preferences page in the settings window:
```python
# In settings window class
def _create_about_page(self):
    about_page = Adw.PreferencesPage(title="About")
    
    # Version group
    version_group = Adw.PreferencesGroup(title="Version Information")
    
    version_row = Adw.ActionRow(
        title="Version",
        subtitle=__version__
    )
    version_group.add(version_row)
    
    # Links group
    links_group = Adw.PreferencesGroup(title="Links")
    
    github_row = Adw.ActionRow(
        title="GitHub Repository",
        subtitle=GITHUB_URL,
        activatable=True
    )
    github_row.connect("activated", self._on_github_clicked)
    links_group.add(github_row)
    
    about_page.add(version_group)
    about_page.add(links_group)
    
    return about_page

def _on_github_clicked(self, widget):
    Gtk.show_uri(None, GITHUB_URL, Gdk.CURRENT_TIME)
```

### Step 3: Integrate About Section
**Files to modify**: `src/ui/settings_window.py`

Add the About page/button to the settings window:
```python
class SettingsWindow(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ... existing code ...
        
        # Add about page
        about_page = self._create_about_page()
        self.add(about_page)
```

### Step 4: Update Flatpak Metadata
**Files to modify**: `flatpak/com.nanogpt.NanoChat.yml`

Ensure the version in the Flatpak manifest matches the application version:
```yaml
app-id: com.nanogpt.NanoChat
runtime: org.gnome.Platform
runtime-version: '46'  # Update as needed
sdk: org.gnome.Sdk
command: nanochat
finish-args:
  - --share=network
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
modules:
  - name: nanochat
    buildsystem: simple
    build-commands:
      - pip3 install --prefix=/app .
    sources:
      - type: dir
        path: ..
```

### Step 5: Test Implementation

**Manual Testing Checklist**:
- [ ] Open settings window
- [ ] Navigate to About section/page
- [ ] Verify version number is displayed correctly
- [ ] Click GitHub link and verify it opens in browser
- [ ] Verify all information is accurate and up-to-date
- [ ] Test on both X11 and Wayland
- [ ] Verify accessibility (keyboard navigation, screen reader)

## Files to Create/Modify

### New Files
- `src/version.py` - Version constants and metadata

### Modified Files
- `src/ui/settings_window.py` - Add About section/dialog
- `flatpak/com.nanogpt.NanoChat.yml` - Ensure version consistency
- `src/__init__.py` - Import version information if needed

## Dependencies
- No new dependencies required
- Uses existing GTK4/Libadwaita components

## Acceptance Criteria
- [ ] Settings window contains an "About" section or button
- [ ] Version number is displayed and matches the actual application version
- [ ] GitHub repository link is present and functional
- [ ] Link opens in the user's default browser
- [ ] Information is accurate and up-to-date
- [ ] UI follows Libadwaita design patterns
- [ ] Works on both X11 and Wayland

## Potential Issues & Solutions

**Issue**: Version number gets out of sync
**Solution**: Use a single source of truth (version.py) and reference it in Flatpak manifest via build system

**Issue**: Link doesn't open on some systems
**Solution**: Use `Gtk.show_uri()` with proper error handling

## Related Issues
- None

## Estimated Effort
**Time**: 1-2 hours
**Complexity**: Low
**Risk**: Low

## Additional Notes
- Consider adding other information like contributors, license details, or dependencies
- Could expand to include system information for bug reports
- May want to add a "Copy version info" button for easy bug reporting
