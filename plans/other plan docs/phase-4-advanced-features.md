# Phase 4: Advanced Features

**Version**: v0.4.0  
**Branch**: `v0.4.0`  
**Prerequisites**: Phase 3 complete (v0.3.0)

---

## Overview

Phase 4 adds power-user features: web search integration, file attachments, starred messages, model analytics, and balance display. These features bring the desktop app closer to feature parity with the web version.

---

## Pre-Phase Tasks

### Human Tasks

1. **Create branch from v0.3.0**
   ```bash
   git checkout v0.3.0
   git checkout -b v0.4.0
   git push -u origin v0.4.0
   ```

2. **Review API docs** for web search providers and file handling

---

## API Reference

### Web Search

Message generation supports web search:
```json
{
  "message": "What's the latest news about AI?",
  "model_id": "gpt-4o",
  "web_search_enabled": true,
  "web_search_mode": "standard",  // off, standard, deep
  "web_search_provider": "tavily"  // linkup, tavily, exa, kagi
}
```

### File Attachments

Images and documents can be attached:
```json
{
  "message": "What's in this image?",
  "model_id": "gpt-4o",
  "images": [
    {
      "url": "https://storage.url/image.png",
      "storage_id": "store_abc123",
      "fileName": "screenshot.png"
    }
  ],
  "documents": [
    {
      "url": "https://storage.url/doc.pdf",
      "storage_id": "store_xyz789",
      "fileName": "document.pdf",
      "fileType": "pdf"
    }
  ]
}
```

### File Upload

```
POST /api/storage
Headers:
  Content-Type: image/png (or appropriate mime type)
  x-filename: filename.png

Body: Binary file content

Response:
{
  "storageId": "string",
  "url": "string"
}
```

### Starred Messages

```
POST /api/db/messages
{
  "action": "setStarred",
  "messageId": "string",
  "starred": true
}

GET /api/starred-messages
```

### NanoGPT Balance

```
POST /api/nano-gpt/balance
Response: { "balance": number, "currency": "string" }

GET /api/nano-gpt/subscription-usage
Response: { "used": number, "limit": number, "resetDate": "date" }
```

### Model Analytics

```
GET /api/analytics
Response: {
  "stats": [...],
  "insights": {
    "totalMessages": number,
    "totalCost": number,
    "mostUsedModel": {...},
    "bestRatedModel": {...}
  }
}
```

---

## Implementation Tasks

### Task 4.1: Web Search Toggle

**Goal**: Add web search toggle to chat input

**Implementation:**

1. Add toggle button to input area:
```python
def _create_input_area(self) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    
    # Web search toggle
    self.web_search_btn = Gtk.ToggleButton()
    self.web_search_btn.set_icon_name("edit-find-symbolic")
    self.web_search_btn.set_tooltip_text("Enable web search")
    self.web_search_btn.connect("toggled", self._on_web_search_toggled)
    box.append(self.web_search_btn)
    
    # ... rest of input area ...
```

2. Update message generation:
```python
async def _send_message(self, text: str):
    request = GenerateMessageRequest(
        message=text,
        model_id=self._get_selected_model_id(),
        assistant_id=self._get_selected_assistant_id(),
        conversation_id=self._current_conversation_id,
        web_search_enabled=self.web_search_btn.get_active(),
        web_search_mode="standard" if self.web_search_btn.get_active() else "off"
    )
```

**Acceptance Criteria:**
- [ ] Web search toggle button in input area
- [ ] Visual feedback when enabled
- [ ] Web search included in request when enabled
- [ ] Toggle state persists during session

---

### Task 4.2: Web Search Configuration

**Goal**: Allow users to configure web search provider and mode

**Files to create:**
- `src/nanochat/ui/web_search_config.py`

**Implementation:**

```python
class WebSearchConfigPopover(Gtk.Popover):
    """Popover for web search configuration."""
    
    def __init__(self):
        super().__init__()
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # Mode selector
        mode_label = Gtk.Label(label="Search Mode", xalign=0)
        self.mode_dropdown = Gtk.DropDown.new_from_strings([
            "Standard", "Deep"
        ])
        
        # Provider selector
        provider_label = Gtk.Label(label="Provider", xalign=0)
        self.provider_dropdown = Gtk.DropDown.new_from_strings([
            "Tavily", "Linkup", "Exa", "Kagi"
        ])
        
        box.append(mode_label)
        box.append(self.mode_dropdown)
        box.append(provider_label)
        box.append(self.provider_dropdown)
        
        self.set_child(box)
    
    def get_config(self) -> tuple[str, str]:
        """Get current configuration."""
        modes = ["standard", "deep"]
        providers = ["tavily", "linkup", "exa", "kagi"]
        return (
            modes[self.mode_dropdown.get_selected()],
            providers[self.provider_dropdown.get_selected()]
        )
```

Long-press or right-click on web search button to show config.

**Acceptance Criteria:**
- [ ] Config popover accessible from web search button
- [ ] Can select search mode
- [ ] Can select provider
- [ ] Settings used in message generation

---

### Task 4.3: Image Attachments

**Goal**: Allow attaching images to messages

**Implementation:**

1. Add attach button:
```python
# In _create_input_area()
self.attach_btn = Gtk.Button(icon_name="mail-attachment-symbolic")
self.attach_btn.set_tooltip_text("Attach file")
self.attach_btn.connect("clicked", self._on_attach_clicked)
box.append(self.attach_btn)
```

2. File chooser dialog:
```python
def _on_attach_clicked(self, button):
    dialog = Gtk.FileChooserDialog(
        title="Attach Image",
        transient_for=self,
        action=Gtk.FileChooserAction.OPEN,
    )
    dialog.add_buttons(
        "_Cancel", Gtk.ResponseType.CANCEL,
        "_Open", Gtk.ResponseType.ACCEPT
    )
    
    # Filter for images
    filter_images = Gtk.FileFilter()
    filter_images.set_name("Images")
    filter_images.add_mime_type("image/*")
    dialog.add_filter(filter_images)
    
    dialog.connect("response", self._on_file_chosen)
    dialog.present()
```

3. Upload file:
```python
async def _upload_file(self, path: Path) -> tuple[str, str]:
    """Upload file and return (storage_id, url)."""
    mime_type, _ = mimetypes.guess_type(str(path))
    
    async with httpx.AsyncClient() as client:
        with open(path, "rb") as f:
            response = await client.post(
                f"{self._base_url}/api/storage",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": mime_type or "application/octet-stream",
                    "x-filename": path.name
                },
                content=f.read()
            )
        data = response.json()
        return data["storageId"], data["url"]
```

4. Show attachment preview:
```python
def _show_attachment_preview(self, path: Path, storage_id: str, url: str):
    """Show thumbnail of attached image."""
    preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    preview_box.add_css_class("attachment-preview")
    
    # Thumbnail
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), 60, 60, True)
    image = Gtk.Image.new_from_pixbuf(pixbuf)
    preview_box.append(image)
    
    # Remove button
    remove_btn = Gtk.Button(icon_name="window-close-symbolic")
    remove_btn.add_css_class("circular")
    remove_btn.connect("clicked", lambda _: self._remove_attachment(storage_id))
    preview_box.append(remove_btn)
    
    self._attachments_box.append(preview_box)
    self._pending_attachments.append({
        "storage_id": storage_id,
        "url": url,
        "fileName": path.name
    })
```

**Acceptance Criteria:**
- [ ] Attach button opens file chooser
- [ ] Can select image files
- [ ] Image uploaded to server
- [ ] Thumbnail preview shown
- [ ] Can remove attachment
- [ ] Attachment sent with message

---

### Task 4.4: Document Attachments

**Goal**: Support PDF and document attachments

**Implementation:**

Extend image attachment to support documents:

```python
# In file chooser
filter_docs = Gtk.FileFilter()
filter_docs.set_name("Documents")
filter_docs.add_mime_type("application/pdf")
filter_docs.add_mime_type("text/markdown")
filter_docs.add_mime_type("text/plain")
filter_docs.add_mime_type("application/epub+zip")
dialog.add_filter(filter_docs)

# Combined filter
filter_all = Gtk.FileFilter()
filter_all.set_name("Images & Documents")
filter_all.add_mime_type("image/*")
filter_all.add_mime_type("application/pdf")
filter_all.add_mime_type("text/*")
dialog.add_filter(filter_all)
```

Document preview with icon instead of thumbnail:

```python
def _get_document_icon(self, file_type: str) -> str:
    icons = {
        "pdf": "x-office-document-symbolic",
        "markdown": "text-x-generic-symbolic",
        "text": "text-x-generic-symbolic",
        "epub": "x-office-document-symbolic"
    }
    return icons.get(file_type, "text-x-generic-symbolic")
```

**Acceptance Criteria:**
- [ ] Can attach PDF files
- [ ] Can attach text/markdown files
- [ ] Document icon shown in preview
- [ ] File type sent correctly in request

---

### Task 4.5: Starred Messages

**Goal**: Allow starring/bookmarking important messages

**Implementation:**

1. Add star button to message widget:
```python
class MessageWidget(Gtk.Box):
    def _setup_actions(self):
        # ... existing actions ...
        
        # Star button
        self.star_btn = Gtk.ToggleButton()
        self.star_btn.set_icon_name("starred-symbolic")
        self.star_btn.add_css_class("flat")
        self.star_btn.set_active(self._message.starred or False)
        self.star_btn.connect("toggled", self._on_star_toggled)
        self._action_box.append(self.star_btn)
    
    def _on_star_toggled(self, button):
        starred = button.get_active()
        # Run async
        self._run_async(self._set_starred(starred))
    
    async def _set_starred(self, starred: bool):
        await self._api_client.set_message_starred(
            self._message.id, 
            starred
        )
```

2. API client method:
```python
async def set_message_starred(self, message_id: str, starred: bool) -> None:
    """Set message starred status."""
    await self._request(
        "POST", "/api/db/messages",
        json={
            "action": "setStarred",
            "messageId": message_id,
            "starred": starred
        }
    )

async def get_starred_messages(self) -> list[Message]:
    """Get all starred messages."""
    data = await self._request("GET", "/api/starred-messages")
    return [Message.model_validate(m) for m in data]
```

3. Starred messages view (optional):
```python
class StarredMessagesDialog(Adw.PreferencesWindow):
    """Dialog showing all starred messages."""
    # List starred messages grouped by conversation
    pass
```

**Acceptance Criteria:**
- [ ] Star button on each message
- [ ] Visual feedback when starred
- [ ] Star status persists
- [ ] Can unstar messages
- [ ] (Optional) Starred messages dialog

---

### Task 4.6: Model Analytics View

**Goal**: Show usage statistics and insights

**Files to create:**
- `src/nanochat/ui/analytics_dialog.py`

**Implementation:**

```python
class AnalyticsDialog(Adw.PreferencesWindow):
    """Dialog showing model analytics and insights."""
    
    def __init__(self, parent):
        super().__init__()
        self.set_transient_for(parent)
        self.set_title("Analytics")
        self.set_default_size(600, 500)
        
        self._setup_ui()
        self._load_analytics()
    
    def _setup_ui(self):
        # Insights page
        insights_page = Adw.PreferencesPage()
        insights_page.set_title("Insights")
        insights_page.set_icon_name("chart-line-symbolic")
        self.add(insights_page)
        
        # Summary group
        summary_group = Adw.PreferencesGroup()
        summary_group.set_title("Summary")
        
        self.total_messages_row = Adw.ActionRow()
        self.total_messages_row.set_title("Total Messages")
        summary_group.add(self.total_messages_row)
        
        self.total_cost_row = Adw.ActionRow()
        self.total_cost_row.set_title("Total Cost")
        summary_group.add(self.total_cost_row)
        
        insights_page.add(summary_group)
        
        # Top models group
        self.models_group = Adw.PreferencesGroup()
        self.models_group.set_title("Model Usage")
        insights_page.add(self.models_group)
    
    async def _load_analytics(self):
        async with NanoChatClient(url, key) as client:
            analytics = await client.get_analytics()
        
        GLib.idle_add(self._update_ui, analytics)
    
    def _update_ui(self, analytics):
        insights = analytics.get("insights", {})
        
        self.total_messages_row.set_subtitle(
            str(insights.get("totalMessages", 0))
        )
        self.total_cost_row.set_subtitle(
            f"${insights.get('totalCost', 0):.4f}"
        )
        
        # Populate model stats
        for stat in analytics.get("stats", [])[:5]:
            row = Adw.ActionRow()
            row.set_title(stat["modelId"])
            row.set_subtitle(f"{stat['totalMessages']} messages")
            self.models_group.add(row)
```

**Acceptance Criteria:**
- [ ] Analytics dialog accessible from menu
- [ ] Shows total messages count
- [ ] Shows total cost
- [ ] Shows top models by usage
- [ ] Data loads from API

---

### Task 4.7: Balance Display

**Goal**: Show NanoGPT account balance in UI

**Implementation:**

1. Add balance to header bar:
```python
# In window.py
self.balance_label = Gtk.Label()
self.balance_label.add_css_class("dim-label")
header.pack_end(self.balance_label)
```

2. Fetch and display balance:
```python
async def _load_balance(self):
    async with NanoChatClient(url, key) as client:
        balance = await client.get_balance()
        subscription = await client.get_subscription_usage()
    
    GLib.idle_add(
        self._update_balance, 
        balance, 
        subscription
    )

def _update_balance(self, balance, subscription):
    if balance:
        text = f"${balance.get('balance', 0):.2f}"
    if subscription and subscription.get('limit'):
        used = subscription.get('used', 0)
        limit = subscription.get('limit', 0)
        text += f" | {used}/{limit}"
    self.balance_label.set_text(text)
```

3. Refresh periodically:
```python
# Refresh every 5 minutes
GLib.timeout_add_seconds(300, self._refresh_balance)
```

**Acceptance Criteria:**
- [ ] Balance shown in header
- [ ] Subscription usage shown (if applicable)
- [ ] Updates periodically
- [ ] Handles missing data gracefully

---

### Task 4.8: API Client Extensions

**Files to modify:**
- `src/nanochat/api/client.py`

Add new methods:

```python
# Balance and subscription
async def get_balance(self) -> dict:
    """Get NanoGPT balance."""
    return await self._request("POST", "/api/nano-gpt/balance")

async def get_subscription_usage(self) -> dict:
    """Get subscription usage."""
    return await self._request("GET", "/api/nano-gpt/subscription-usage")

# Analytics
async def get_analytics(self, recalculate: bool = True) -> dict:
    """Get model analytics."""
    params = {"recalculate": "true" if recalculate else "false"}
    return await self._request("GET", "/api/analytics", params=params)

# Storage
async def upload_file(
    self, 
    content: bytes, 
    filename: str, 
    mime_type: str
) -> tuple[str, str]:
    """Upload a file and return (storage_id, url)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{self.base_url}/api/storage",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": mime_type,
                "x-filename": filename
            },
            content=content
        )
        response.raise_for_status()
        data = response.json()
        return data["storageId"], data["url"]

async def delete_file(self, storage_id: str) -> None:
    """Delete an uploaded file."""
    await self._request(
        "DELETE", "/api/storage",
        params={"id": storage_id}
    )
```

**Acceptance Criteria:**
- [ ] Balance endpoint works
- [ ] Subscription endpoint works
- [ ] Analytics endpoint works
- [ ] File upload works
- [ ] File delete works

---

### Task 4.9: Annotation Display

**Goal**: Show web search results and other annotations in messages

**Implementation:**

Messages can have annotations (web search results, images, etc.):

```python
class MessageWidget(Gtk.Box):
    def _setup_annotations(self):
        if not self._message.annotations:
            return
        
        annotations_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, 
            spacing=8
        )
        annotations_box.add_css_class("message-annotations")
        
        for annotation in self._message.annotations:
            if annotation.type == "web-search":
                widget = self._create_web_search_annotation(annotation.data)
                annotations_box.append(widget)
        
        self.append(annotations_box)
    
    def _create_web_search_annotation(self, data: dict) -> Gtk.Widget:
        """Create web search results card."""
        frame = Gtk.Frame()
        frame.add_css_class("card")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        
        # Sources header
        header = Gtk.Label(label="Sources", xalign=0)
        header.add_css_class("heading")
        box.append(header)
        
        # Source links
        for source in data.get("sources", [])[:5]:
            link = Gtk.LinkButton.new_with_label(
                source["url"], 
                source["title"]
            )
            link.set_halign(Gtk.Align.START)
            box.append(link)
        
        frame.set_child(box)
        return frame
```

**Acceptance Criteria:**
- [ ] Web search results shown below message
- [ ] Source links clickable
- [ ] Clean presentation

---

## Definition of Done - Phase 4

- [ ] All tasks completed
- [ ] Manual testing checklist:
  - [ ] Web search toggle works
  - [ ] Web search config works
  - [ ] Image upload works
  - [ ] Document upload works
  - [ ] Star messages works
  - [ ] Analytics displays correctly
  - [ ] Balance shows in header
  - [ ] Annotations display correctly
- [ ] Code reviewed
- [ ] Branch merged and tagged as `v0.4.0`
- [ ] Release created with binaries

---

## Release Checklist

```bash
# Update version to 0.4.0
git checkout v0.4.0
git tag -a v0.4.0 -m "Release v0.4.0 - Advanced Features"
git push origin v0.4.0 --tags

# Build and release
```

---

## Notes for LLM

When implementing Phase 4:

1. **File uploads** require proper error handling for large files
2. **Web search** is optional - toggle should be clear
3. **Balance refresh** should not be too frequent
4. **Annotations** may have different types - handle unknown types gracefully
5. **Analytics** may be slow - show loading state
6. **File types** - validate before upload
