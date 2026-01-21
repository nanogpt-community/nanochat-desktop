# Issue #9: Remove "Retrieving Messages" banner

**Issue URL**: https://github.com/nanogpt-community/nanochat-desktop/issues/9
**Status**: OPEN
**Priority**: LOW

## Description
Remove the "Retrieving Messages" banner. We only need to show the banner if there's a delay or error.

## Objective
Improve UX by:
- Removing the constant "Retrieving Messages" banner that appears on every conversation load
- Only showing a loading indicator when there's an actual delay (e.g., > 500ms)
- Showing error messages when message retrieval fails
- Making the loading experience feel more responsive

## Technical Context
- **File Location**: `src/ui/chat_view.py` or `src/ui/main_window.py`
- **Tech Stack**: GTK4/Libadwaita
- **Current Issue**: Banner shows up immediately and constantly, which is annoying when messages load quickly from cache

## Implementation Plan

### Step 1: Identify Current Banner Implementation
**Files to analyze**: `src/ui/chat_view.py`, `src/ui/conversation_view.py`

Find where the "Retrieving Messages" banner is currently shown:
```python
# Current (problematic) implementation - TO BE CHANGED
async def load_messages(self, conversation_id: str):
    self.banner.set_revealed(True)  # Shows immediately
    self.banner.set_title("Retrieving Messages")
    
    messages = await self.api_client.get_messages(conversation_id)
    
    self.banner.set_revealed(False)
```

### Step 2: Implement Delayed Loading Indicator
**Files to modify**: `src/ui/chat_view.py`

Only show loading banner after a delay:
```python
import asyncio
from gi.repository import GLib

class ChatView(Gtk.Box):
    def __init__(self):
        super().__init__()
        self._loading_timeout_id = None
        self._is_loading = False
        
        # Create banner (initially hidden)
        self.banner = Adw.Banner()
        self.banner.set_revealed(False)
    
    async def load_messages(self, conversation_id: str):
        """Load messages with delayed loading indicator"""
        self._is_loading = True
        
        # Start a timer - only show banner if loading takes > 500ms
        self._loading_timeout_id = GLib.timeout_add(
            500,  # 500ms delay
            self._show_loading_banner
        )
        
        try:
            # Load messages (try cache first, then network)
            messages = await self._load_messages_with_cache(conversation_id)
            
            # Display messages
            for msg in messages:
                self._display_message(msg)
            
        except Exception as e:
            # Show error banner
            self._show_error_banner(f"Failed to load messages: {e}")
        finally:
            # Cancel the loading timeout if it hasn't fired yet
            if self._loading_timeout_id:
                GLib.source_remove(self._loading_timeout_id)
                self._loading_timeout_id = None
            
            self._is_loading = False
            
            # Hide banner
            self.banner.set_revealed(False)
    
    def _show_loading_banner(self):
        """Show loading banner (called after timeout)"""
        if self._is_loading:
            self.banner.set_title("Loading messages...")
            self.banner.set_revealed(True)
        
        # Return False to stop the timeout from repeating
        self._loading_timeout_id = None
        return False
    
    def _show_error_banner(self, message: str):
        """Show error banner with action button"""
        self.banner.set_title(message)
        self.banner.set_button_label("Retry")
        self.banner.set_revealed(True)
        
        # Connect retry button
        self.banner.connect("button-clicked", self._on_retry_clicked)
    
    async def _load_messages_with_cache(self, conversation_id: str):
        """Load messages from cache first, then sync with server"""
        # Try cache first (fast!)
        cached = await self.db.get_messages_by_conversation(conversation_id)
        if cached:
            return cached
        
        # Cache miss - load from server
        return await self.api_client.get_messages(conversation_id)
```

### Step 3: Add Smart Loading States
**Files to modify**: `src/ui/chat_view.py`

Different loading states for different scenarios:
```python
class LoadingState:
    IDLE = "idle"
    LOADING_CACHE = "loading_cache"  # Fast, no banner
    LOADING_NETWORK = "loading_network"  # May show banner
    ERROR = "error"

class ChatView(Gtk.Box):
    def __init__(self):
        super().__init__()
        self._loading_state = LoadingState.IDLE
        
    async def load_messages(self, conversation_id: str):
        """Load with smart state management"""
        # Try cache first (no loading indicator needed)
        self._loading_state = LoadingState.LOADING_CACHE
        cached = await self.db.get_messages_by_conversation(conversation_id)
        
        if cached:
            # Fast path - display immediately
            for msg in cached:
                self._display_message(msg)
            self._loading_state = LoadingState.IDLE
            
            # Sync in background (no banner)
            asyncio.create_task(self._background_sync(conversation_id))
        else:
            # Slow path - need to fetch from network
            await self._load_from_network(conversation_id)
    
    async def _load_from_network(self, conversation_id: str):
        """Load from network with delayed banner"""
        self._loading_state = LoadingState.LOADING_NETWORK
        
        # Set up delayed banner
        self._loading_timeout_id = GLib.timeout_add(500, self._show_loading_banner)
        
        try:
            messages = await self.api_client.get_messages(conversation_id)
            for msg in messages:
                self._display_message(msg)
                await self.db.insert_message(msg)  # Cache for next time
        except Exception as e:
            self._loading_state = LoadingState.ERROR
            self._show_error_banner(str(e))
        finally:
            if self._loading_timeout_id:
                GLib.source_remove(self._loading_timeout_id)
                self._loading_timeout_id = None
            
            if self._loading_state != LoadingState.ERROR:
                self._loading_state = LoadingState.IDLE
                self.banner.set_revealed(False)
```

### Step 4: Add Spinner for Long Operations
**Files to modify**: `src/ui/chat_view.py`

Instead of just a banner, use a subtle spinner:
```python
class ChatView(Gtk.Box):
    def __init__(self):
        super().__init__()
        
        # Create spinner in header (more subtle than banner)
        self.loading_spinner = Gtk.Spinner()
        self.loading_spinner.set_visible(False)
        # Add to header bar or status area
    
    def _show_loading_indicator(self):
        """Show subtle loading indicator instead of banner"""
        self.loading_spinner.set_visible(True)
        self.loading_spinner.start()
    
    def _hide_loading_indicator(self):
        """Hide loading indicator"""
        self.loading_spinner.stop()
        self.loading_spinner.set_visible(False)
```

### Step 5: Remove Unnecessary Banner Calls
**Files to modify**: All files that call the banner

Search for all instances of:
```python
banner.set_revealed(True)
banner.set_title("Retrieving Messages")
```

And replace with the new delayed loading logic.

### Step 6: Test Implementation

**Manual Testing Checklist**:
- [ ] Fast loads (from cache) show no banner
- [ ] Slow loads (network) show banner after 500ms delay
- [ ] Very fast loads complete before banner appears
- [ ] Error state shows error message in banner
- [ ] Retry button works in error state
- [ ] Banner doesn't flicker on/off
- [ ] Loading state is clear but not annoying
- [ ] Works on both fast and slow connections

**Performance Testing**:
- Test with throttled network connection
- Test with cache populated vs empty
- Measure time from click to first message display

## Files to Create/Modify

### Modified Files
- `src/ui/chat_view.py` - Implement delayed loading indicator
- `src/ui/conversation_view.py` - Update to use new loading pattern
- `src/ui/main_window.py` - Remove immediate banner calls

### New Files
None required

## Dependencies
- No new dependencies required
- Uses existing GTK4/Libadwaita components

## Acceptance Criteria
- [ ] "Retrieving Messages" banner does NOT appear on fast loads
- [ ] Loading indicator only appears after 500ms delay
- [ ] Error banner appears when message loading fails
- [ ] Error banner includes retry button
- [ ] No banner flicker or UI jank
- [ ] Loading state is communicated clearly but subtly
- [ ] Cached messages load instantly without any loading indicator

## Potential Issues & Solutions

**Issue**: 500ms delay still feels slow
**Solution**: Make delay configurable, consider 300ms or use adaptive timing based on connection speed

**Issue**: Banner appears briefly then disappears (flicker)
**Solution**: Ensure banner stays visible for minimum time (e.g., 200ms) once shown

**Issue**: User doesn't know if app is working when no banner
**Solution**: Add subtle cursor change or very small spinner in corner

**Issue**: Race condition between timeout and message load
**Solution**: Properly cancel timeout when loading completes, use state machine

## Related Issues
- Issue #12 - Local DB caching (this will make loads faster, reducing need for banner)

## Estimated Effort
**Time**: 2-3 hours
**Complexity**: Low-Medium
**Risk**: Low

## Additional Notes
- This is a polish issue that improves perceived performance
- Works best in combination with Issue #12 (local caching)
- Consider adding a preference for loading delay threshold
- Could show skeleton UI instead of banner for better UX
- Future: Progressive loading (show cached, then update with server data)
