# Future Enhancements Roadmap

**Post v1.0.0 Features**

This document tracks potential features for future development beyond the initial v1.0.0 release.

---

## High Priority - v1.1.0+

### 1. Text-to-Speech (TTS)

**Description**: Read assistant responses aloud using NanoGPT TTS API

**API Endpoint**:
```
POST /api/tts
{
  "text": "string",
  "model": "tts-1",
  "voice": "alloy",
  "speed": 1.0
}
Response: audio/mpeg binary
```

**Implementation Notes**:
- Use GStreamer for audio playback in GTK4
- Add speaker button to assistant messages
- Support voice and speed selection
- Consider caching generated audio

**UI Mock**:
```
┌────────────────────────────────────────────────┐
│ Assistant: Hello! How can I help you today?   │
│                                    [🔊] [📋]  │
└────────────────────────────────────────────────┘
```

---

### 2. Speech-to-Text (STT)

**Description**: Voice input for messages using NanoGPT STT API

**API Endpoint**:
```
POST /api/stt
FormData:
  audio: binary (webm, mp4, etc.)
  model: "Whisper-Large-V3"
  language: "auto"

Response:
{
  "transcription": "string",
  "text": "string"
}
```

**Implementation Notes**:
- Use PipeWire/PulseAudio for microphone access
- Add microphone button next to send
- Show recording indicator
- Consider push-to-talk vs toggle

**UI Mock**:
```
┌──────────────────────────────────────────────────┐
│ [Attach] [Web 🔍] [🎤 Recording...] [Type...] [📤] │
└──────────────────────────────────────────────────┘
```

---

### 3. Conversation Export

**Description**: Export conversations to various formats

**Formats to support**:
- Markdown (.md)
- Plain text (.txt)
- JSON (full data export)
- PDF (formatted)

**Implementation**:
```python
class ConversationExporter:
    def export_markdown(self, conversation, messages) -> str:
        # Format as markdown with proper headers
        pass
    
    def export_json(self, conversation, messages) -> str:
        # Full JSON export
        pass
    
    def export_pdf(self, conversation, messages) -> bytes:
        # Use weasyprint or reportlab
        pass
```

---

### 4. Multi-Account Support

**Description**: Support multiple backend configurations/accounts

**Implementation**:
- Store multiple accounts in config
- Account switcher in settings
- Isolated data per account

```toml
# config.toml
[[accounts]]
name = "Personal"
backend_url = "https://personal.nanochat.com"
default = true

[[accounts]]
name = "Work"
backend_url = "https://work.nanochat.com"
```

---

### 5. System Prompt Quick Edits

**Description**: Edit system prompt per-conversation without full assistant

**Implementation**:
- Add "Customize" button in chat header
- Temporary system prompt override
- Option to save as new assistant

---

## Medium Priority - v1.2.0+

### 6. Conversation Branching

**Description**: Branch from any message to explore alternative responses

**API Endpoint**:
```
POST /api/db/conversations
{
  "action": "branch",
  "conversationId": "string",
  "fromMessageId": "string"
}
```

**UI Mock**:
```
Message context menu:
├── Copy
├── Star
├── Branch from here  <-- New
└── Delete
```

---

### 7. Pinned Conversations

**Description**: Pin important conversations to top of list

**API Endpoint**:
```
POST /api/db/conversations
{
  "action": "togglePin",
  "conversationId": "string"
}
```

**Implementation**:
- Pin icon on conversation rows
- Pinned section at top of list
- Persist via API

---

### 8. Message Regeneration

**Description**: Regenerate the last assistant response

**API Endpoint**:
```
POST /api/generate-message
{
  "conversation_id": "string"
  // No message - regenerates last
}
```

**UI Mock**:
```
┌────────────────────────────────────────────────┐
│ Assistant: [Previous response]                 │
│                              [🔄] [📋] [⭐]   │
└────────────────────────────────────────────────┘
```

---

### 9. Image Generation Display

**Description**: Display generated images inline in chat

**Implementation Notes**:
- Detect image model responses
- Display images with download option
- Support image gallery for multiple images

---

### 10. Drag and Drop Attachments

**Description**: Drag files directly into chat input

**Implementation**:
```python
def _setup_drop_target(self):
    drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
    drop_target.connect("drop", self._on_file_dropped)
    self.add_controller(drop_target)

def _on_file_dropped(self, target, value, x, y):
    file = value
    path = Path(file.get_path())
    self._attach_file(path)
```

---

## Lower Priority - v1.3.0+

### 11. MCP (Model Context Protocol) Support

**Description**: Execute MCP tools from the desktop client

**API Endpoints**:
```
GET /api/mcp - Check MCP status
POST /api/mcp - Execute tool
{
  "tool": "string",
  "args": {}
}
```

**Implementation Notes**:
- Display available tools
- Tool execution results in chat
- Error handling for tool failures

---

### 12. Project Files Management

**Description**: Manage project files from desktop

**API Endpoints**:
```
GET    /api/projects/:id/files
POST   /api/projects/:id/files   (upload)
DELETE /api/projects/:id/files?fileId=...
```

**UI Mock**:
```
┌─────────────────────────────────────────┐
│ Project: My Research          [+ File]  │
├─────────────────────────────────────────┤
│ 📄 document.pdf               [🗑]      │
│ 📄 notes.md                   [🗑]      │
│ 📄 data.csv                   [🗑]      │
└─────────────────────────────────────────┘
```

---

### 13. Shared Projects

**Description**: View shared projects and collaborate

**API Endpoints**:
```
GET    /api/projects/:id/members
POST   /api/projects/:id/members
DELETE /api/projects/:id/members?userId=...
```

---

### 14. Custom Rules Support

**Description**: Manage user rules for AI behavior

**API Endpoints**:
```
GET    /api/db/user-rules
POST   /api/db/user-rules
DELETE /api/db/user-rules?id=...
```

---

### 15. Provider Preferences

**Description**: Configure preferred AI providers per model

**API Endpoints**:
```
GET   /api/provider-preferences
PATCH /api/provider-preferences
```

---

### 16. Video Generation Support

**Description**: Support video model workflows

**API Endpoints**:
```
POST /api/video/generate
GET  /api/video/status?runId=...
```

---

### 17. Notification Support

**Description**: System notifications for long-running tasks

**Implementation**:
```python
def _send_notification(self, title: str, body: str):
    notification = Gio.Notification.new(title)
    notification.set_body(body)
    self.get_application().send_notification(None, notification)
```

---

### 18. Session Persistence

**Description**: Resume last session on startup

**Implementation**:
- Remember last conversation
- Restore scroll position
- Restore unsent message draft

---

### 19. Message Search

**Description**: Search within message content

**Implementation**:
```python
# Full-text search in local database
def search_messages(self, query: str) -> list[Message]:
    return self._conn.execute(
        "SELECT * FROM messages WHERE content LIKE ?",
        (f"%{query}%",)
    ).fetchall()
```

---

### 20. Plugin System

**Description**: Allow custom extensions

**Very low priority** - complex implementation

---

## Experimental Features

### E1. Local LLM Support

**Description**: Connect to local Ollama or llama.cpp

**Implementation Notes**:
- Alternative backend URL
- Local model selection
- No auth required

---

### E2. Multiple Chat Windows

**Description**: Open conversations in separate windows

---

### E3. Chat Templates

**Description**: Start conversations from templates

---

## Feature Request Process

To request a new feature:

1. Check this list first
2. Create GitHub issue with:
   - Clear description
   - Use case
   - Proposed UI (if applicable)
3. Label as `enhancement`
4. Discuss in issue before implementation

---

## Priority Criteria

Features are prioritized by:

1. **User demand** - How many users request it
2. **API availability** - Is the backend API ready
3. **Complexity** - Implementation effort
4. **Impact** - How much it improves the app
5. **Dependencies** - Does it require other features

---

## Version Planning

| Version | Focus |
|---------|-------|
| v1.1.0 | TTS, STT, Export |
| v1.2.0 | Branching, Regeneration, Pinning |
| v1.3.0 | MCP, Project Files, Advanced Features |
| v2.0.0 | Major UI refresh, Plugin System |
