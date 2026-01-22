"""Streaming manager for SSE message generation with cancellation and timeout.

Inspired by nanochat-android's StreamingManager.kt.
Provides cancellable streams with timeout handling and UI update throttling.
"""

import asyncio
import threading
import time
from collections.abc import Callable
from typing import Any, Optional

from gi.repository import GLib

from nanochat.api.client import NanoChatClient
from nanochat.api.models import GenerateMessageRequest


class StreamCancelledError(Exception):
    """Exception raised when streaming is cancelled by user."""

    pass


class StreamingManager:
    """Manages SSE streaming with cancellation and timeout support.

    Features:
    - Cancellable streaming operations
    - 5-minute timeout protection
    - UI update throttling (max 20 updates/second)
    - Automatic cleanup on completion/error

    Usage:
        manager = StreamingManager(backend_url, api_key)
        await manager.stream_message(
            request,
            on_content_delta=lambda c: update_ui(c),
            on_reasoning_delta=lambda r: update_reasoning(r),
            on_message_start=lambda cid, mid: handle_start(cid, mid),
            on_complete=lambda data: handle_complete(data),
            on_error=lambda e: show_error(e),
        )

        # To cancel from anywhere:
        manager.cancel()
    """

    STREAM_TIMEOUT_SECONDS = 300  # 5 minutes
    UI_UPDATE_THROTTLE_MS = 50  # Don't update UI more than 20x/second

    def __init__(self, backend_url: str, api_key: str) -> None:
        """Initialize the streaming manager.

        Args:
            backend_url: NanoChat API base URL
            api_key: NanoChat API key
        """
        self._backend_url = backend_url
        self._api_key = api_key
        self._current_task: Optional[asyncio.Task[None]] = None
        self._cancelled = False
        self._cancel_event = threading.Event()  # Thread-safe cancellation signal
        self._last_ui_update = 0
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def cancel(self) -> None:
        """Cancel the current streaming operation.

        Thread-safe: can be called from any thread.
        """
        self._cancelled = True
        self._cancel_event.set()  # Signal all waiting threads

        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

        if self._loop and self._loop.is_running():
            # Schedule cancellation on the event loop
            self._loop.call_soon_threadsafe(lambda: None)

    def is_streaming(self) -> bool:
        """Check if a stream is currently active.

        Returns:
            True if a stream is in progress
        """
        return self._current_task is not None and not self._current_task.done()

    async def stream_message(
        self,
        request: GenerateMessageRequest,
        on_content_delta: Callable[[str], None],
        on_reasoning_delta: Callable[[str], None],
        on_message_start: Callable[[str, str], None],
        on_complete: Callable[[dict[str, Any]], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Stream a message with proper event handling.

        Args:
            request: Message generation request
            on_content_delta: Callback for content updates (receives accumulated content)
            on_reasoning_delta: Callback for reasoning updates (receives accumulated reasoning)
            on_message_start: Callback for message start (receives conversation_id, message_id)
            on_complete: Callback for completion (receives metadata dict)
            on_error: Callback for errors (receives error message)

        Events emitted:
            message_start: {conversation_id, message_id}
            delta: {content?, reasoning?}
            message_complete: {token_count, cost_usd, response_time_ms}
            error: {error}
        """
        self._cancelled = False
        self._cancel_event.clear()  # Reset cancellation event for new stream
        self._loop = asyncio.get_running_loop()
        accumulated_content = ""
        accumulated_reasoning = ""

        # Thread-safe cancellation checker
        def is_cancelled() -> bool:
            return self._cancel_event.is_set()

        def handle_event(event_type: str, data: dict[str, Any]) -> None:
            """Handle SSE events from the API."""
            nonlocal accumulated_content, accumulated_reasoning

            # Check for cancellation at the start of each event
            if self._cancelled:
                raise StreamCancelledError("Stream cancelled by user")

            if event_type == "message_start":
                conversation_id = data.get("conversation_id", "")
                message_id = data.get("message_id", "")
                GLib.idle_add(on_message_start, conversation_id, message_id)

            elif event_type == "delta":
                content = data.get("content", "")
                reasoning = data.get("reasoning", "")

                if content:
                    accumulated_content += content
                    # Throttle UI updates for performance
                    if self._should_update_ui():
                        GLib.idle_add(on_content_delta, accumulated_content)

                if reasoning:
                    accumulated_reasoning += reasoning
                    if self._should_update_ui():
                        GLib.idle_add(on_reasoning_delta, accumulated_reasoning)

            elif event_type == "message_complete":
                # Final UI update with complete content
                GLib.idle_add(on_content_delta, accumulated_content)

                # Update reasoning if present
                if accumulated_reasoning:
                    GLib.idle_add(on_reasoning_delta, accumulated_reasoning)

                # Send completion event with metadata
                GLib.idle_add(on_complete, data)

            elif event_type == "error":
                error_msg = data.get("error", "Unknown error")
                GLib.idle_add(on_error, error_msg)

        try:
            # Create the API client
            async with NanoChatClient(self._backend_url, self._api_key) as client:
                self._current_task = asyncio.current_task()

                # Pass cancellation flag to client
                def is_cancelled() -> bool:
                    return self._cancelled

                await asyncio.wait_for(
                    client.stream_generate_message(request, handle_event, is_cancelled),
                    timeout=self.STREAM_TIMEOUT_SECONDS,
                )

        except StreamCancelledError:
            # User explicitly cancelled - this is expected, not an error
            pass  # Don't show error notification

        except asyncio.TimeoutError:
            GLib.idle_add(on_error, f"Stream timeout after {self.STREAM_TIMEOUT_SECONDS // 60} minutes")

        except asyncio.CancelledError:
            if not self._cancelled:
                # If we weren't explicitly cancelled, this is an unexpected cancellation
                GLib.idle_add(on_error, "Generation was cancelled unexpectedly")

        except Exception as e:
            # Let other specific errors bubble up from the client
            GLib.idle_add(on_error, str(e))

        finally:
            self._current_task = None

    def _should_update_ui(self) -> bool:
        """Check if enough time has passed to update the UI.

        Throttles UI updates to prevent lag during rapid streaming.

        Returns:
            True if UI should be updated, False if throttled
        """
        now = time.time() * 1000  # Convert to milliseconds
        if now - self._last_ui_update > self.UI_UPDATE_THROTTLE_MS:
            self._last_ui_update = now
            return True
        return False
