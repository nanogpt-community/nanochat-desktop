"""HTTP client for NanoChat API."""

import httpx
import json
from typing import Callable, Optional

from .models import (
    Conversation,
    Message,
    Model,
    Assistant,
    CreateAssistantRequest,
    UpdateAssistantRequest,
    GenerateMessageRequest,
    ImageAttachment,
    DocumentAttachment,
    SSEMessageStart,
    SSEDelta,
    SSEMessageComplete,
    SSEError,
)
from .exceptions import (
    NanoChatAPIError,
    AuthenticationError,
    ConnectionError as APIConnectionError,
    RateLimitError,
)


class NanoChatClient:
    """Async client for NanoChat API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def __aenter__(self) -> "NanoChatClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(30.0, read=300.0),
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: object) -> dict[str, object]:
        """Make an API request with error handling."""
        try:
            response = await self._client.request(method, path, **kwargs)  # type: ignore[arg-type]
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key") from e
            if e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded") from e
            raise NanoChatAPIError(f"API error: {e.response.status_code}") from e
        except httpx.NetworkError as e:
            raise APIConnectionError("Cannot connect to server") from e

    # Conversations
    async def get_conversations(self, project_id: Optional[str] = None) -> list[Conversation]:
        """Get all conversations."""
        params = {}
        if project_id:
            params["projectId"] = project_id
        data = await self._request("GET", "/api/db/conversations", params=params)
        return [Conversation.model_validate(c) for c in data]

    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Get a single conversation by ID."""
        data = await self._request(
            "GET",
            "/api/db/conversations",
            params={"id": conversation_id},
        )
        return Conversation.model_validate(data)

    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation."""
        await self._request("DELETE", "/api/db/conversations", params={"id": conversation_id})

    # Messages
    async def get_messages(self, conversation_id: str) -> list[Message]:
        """Get messages for a conversation."""
        data = await self._request(
            "GET",
            "/api/db/messages",
            params={"conversationId": conversation_id},
        )
        return [Message.model_validate(m) for m in data]

    # Models
    async def get_models(self) -> list[Model]:
        """Get available models."""
        data = await self._request("GET", "/api/models")
        return [Model.model_validate(m) for m in data]

    async def favorite_model(self, model_id: str) -> bool:
        """Favorite a model."""
        try:
            await self._request("POST", f"/api/models/{model_id}/favorite")
            return True
        except Exception:
            return False

    async def unfavorite_model(self, model_id: str) -> bool:
        """Unfavorite a model."""
        try:
            await self._request("DELETE", f"/api/models/{model_id}/favorite")
            return True
        except Exception:
            return False

    # Assistants
    async def get_assistants(self) -> list[Assistant]:
        """Get all assistants for the current user."""
        data = await self._request("GET", "/api/assistants")
        return [Assistant.model_validate(a) for a in data]

    async def get_assistant(self, assistant_id: str) -> Assistant:
        """Get a single assistant by ID."""
        data = await self._request("GET", f"/api/assistants/{assistant_id}")
        return Assistant.model_validate(data)

    async def create_assistant(self, request: CreateAssistantRequest) -> Assistant:
        """Create a new assistant."""
        data = await self._request(
            "POST",
            "/api/assistants",
            json=request.model_dump(exclude_none=True, by_alias=True),
        )
        return Assistant.model_validate(data)

    async def update_assistant(
        self, assistant_id: str, request: UpdateAssistantRequest
    ) -> Assistant:
        """Update an assistant."""
        await self._request(
            "PATCH",
            f"/api/assistants/{assistant_id}",
            json=request.model_dump(exclude_none=True, by_alias=True),
        )
        # API returns {"success": True} for updates, re-fetch all assistants to get updated data
        assistants = await self.get_assistants()
        for assistant in assistants:
            if assistant.id == assistant_id:
                return assistant
        raise NanoChatAPIError(f"Updated assistant {assistant_id} not found in list")

    async def delete_assistant(self, assistant_id: str) -> None:
        """Delete an assistant."""
        await self._request("DELETE", f"/api/assistants/{assistant_id}")

    async def set_default_assistant(self, assistant_id: str) -> None:
        """Set an assistant as the default."""
        await self._request(
            "POST",
            f"/api/assistants/{assistant_id}",
            json={"action": "setDefault"},
        )

    # Connection test
    async def test_connection(self) -> bool:
        """Test API connection."""
        try:
            await self.get_models()
            return True
        except NanoChatAPIError:
            return False

    # File storage
    async def upload_file(
        self,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> tuple[str, str]:
        """Upload a file to storage.

        Args:
            content: Binary file content
            filename: Original filename
            mime_type: MIME type of the file

        Returns:
            Tuple of (storage_id, url)

        Raises:
            NanoChatAPIError: If upload fails
        """
        if not self._client:
            raise NanoChatAPIError("Client not initialized")

        try:
            response = await self._client.post(
                "/api/storage",
                content=content,
                headers={
                    "Content-Type": mime_type,
                    "x-filename": filename,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["storageId"], data["url"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key") from e
            raise NanoChatAPIError(f"Upload failed: {e.response.status_code}") from e
        except httpx.NetworkError as e:
            raise APIConnectionError("Cannot connect to server") from e

    async def delete_file(self, storage_id: str) -> bool:
        """Delete a file from storage.

        Args:
            storage_id: The storage ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            await self._request("DELETE", "/api/storage", params={"id": storage_id})
            return True
        except Exception:
            return False

    async def toggle_star(self, message_id: str, starred: bool) -> bool:
        """Toggle the starred status of a message.

        Args:
            message_id: The message ID to star/unstar
            starred: True to star, False to unstar

        Returns:
            True if successful, False otherwise

        Raises:
            AuthenticationError: If authentication fails
            NanoChatAPIError: If the API returns an error
            APIConnectionError: If network connection fails
        """
        try:
            await self._request(
                "POST",
                "/api/db/messages",
                json={
                    "action": "setStarred",
                    "messageId": message_id,
                    "starred": starred,
                },
            )
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key") from e
            raise NanoChatAPIError(f"Failed to toggle star: {e.response.status_code}") from e
        except httpx.NetworkError as e:
            raise APIConnectionError("Cannot connect to server") from e

    # Streaming message generation
    async def stream_generate_message(
        self,
        request: GenerateMessageRequest,
        on_event: Callable[[str, dict], None],
    ) -> None:
        """Generate a message with SSE streaming using callbacks.

        Calls on_event for each SSE event with (event_type, event_data) where event_type is:
        - "message_start": SSEMessageStart data
        - "delta": SSEDelta data
        - "message_complete": SSEMessageComplete data
        - "error": SSEError data

        Args:
            request: Generation request parameters
            on_event: Callback function receiving (event_type, event_data)

        Raises:
            NanoChatAPIError: If the API returns an error
            AuthenticationError: If authentication fails
            APIConnectionError: If network connection fails
        """
        received_complete = False

        # Get the JSON payload that will be sent
        # Use by_alias=True to properly serialize field aliases (camelCase)
        json_payload = request.model_dump(exclude_none=True, by_alias=True)

        try:
            async with self._client.stream(  # type: ignore[union-attr]
                "POST",
                "/api/generate-message/stream",
                json=json_payload,
            ) as response:
                response.raise_for_status()

                # Parse SSE stream - track event type across lines
                current_event = None

                try:
                    async for line in response.aiter_lines():
                        # If we've already received a terminal event, just consume and ignore
                        if received_complete:
                            continue

                        line = line.strip()

                        # Skip empty lines
                        if not line:
                            continue

                        # Parse event type (precedes data)
                        if line.startswith("event: "):
                            current_event = line[7:].strip()
                            continue

                        # Parse data (follows event)
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            try:
                                data = json.loads(data_str)
                                if current_event:
                                    on_event(current_event, data)
                                    # If terminal event, mark as complete
                                    if current_event in ("message_complete", "error"):
                                        received_complete = True
                                    current_event = None  # Reset for next event
                            except json.JSONDecodeError:
                                # Invalid JSON, skip
                                continue
                except httpx.RemoteProtocolError:
                    # Server closed the connection - this is expected after message_complete
                    if not received_complete:
                        raise  # Re-raise if we didn't receive a complete event

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key") from e
            if e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded") from e
            raise NanoChatAPIError(f"API error: {e.response.status_code}") from e
        except httpx.RemoteProtocolError:
            # Server closed the connection - expected after message_complete
            if not received_complete:
                raise APIConnectionError("Server closed connection unexpectedly")
        except httpx.NetworkError as e:
            raise APIConnectionError("Cannot connect to server") from e
