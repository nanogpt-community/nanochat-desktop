"""HTTP client for NanoChat API."""

import httpx
import json
from typing import AsyncGenerator, Optional

from .models import Conversation, Message, Model, GenerateMessageRequest
from .exceptions import (
    NanoChatAPIError,
    AuthenticationError,
    ConnectionError as APIConnectionError,
    RateLimitError,
)


class StreamEvent:
    """Base class for streaming events."""

    pass


class TokenEvent(StreamEvent):
    """Token received during streaming."""

    def __init__(self, token: str) -> None:
        self.token = token


class ContentEvent(StreamEvent):
    """Content delta received."""

    def __init__(self, content: str) -> None:
        self.content = content


class ReasoningEvent(StreamEvent):
    """Reasoning content received."""

    def __init__(self, reasoning: str) -> None:
        self.reasoning = reasoning


class ConversationCreatedEvent(StreamEvent):
    """New conversation created."""

    def __init__(self, conversation_id: str, title: str) -> None:
        self.conversation_id = conversation_id
        self.title = title


class StreamCompleteEvent(StreamEvent):
    """Stream completed."""

    pass


class StreamErrorEvent(StreamEvent):
    """Stream error occurred."""

    def __init__(self, error: str) -> None:
        self.error = error


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

    async def stream_message(
        self, request: GenerateMessageRequest
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream a message generation."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate-message",
                headers=headers,
                json=request.model_dump(exclude_none=True, by_alias=True),
            ) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        raise AuthenticationError("Invalid API key") from e
                    if e.response.status_code == 429:
                        raise RateLimitError("Rate limit exceeded") from e
                    raise

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            yield StreamCompleteEvent()
                            break

                        try:
                            event_data = json.loads(data)
                            yield self._parse_sse_event(event_data)
                        except json.JSONDecodeError:
                            continue

    def _parse_sse_event(self, data: dict[str, object]) -> StreamEvent:
        """Parse SSE event data into appropriate event type."""
        if "conversationId" in data and "conversationTitle" in data:
            conv_id = str(data["conversationId"])
            title = str(data["conversationTitle"])
            return ConversationCreatedEvent(conv_id, title)
        if "token" in data:
            return TokenEvent(str(data["token"]))
        if "content" in data:
            return ContentEvent(str(data["content"]))
        if "reasoning" in data:
            return ReasoningEvent(str(data["reasoning"]))
        if "error" in data:
            return StreamErrorEvent(str(data["error"]))
        return StreamEvent()

    # Models
    async def get_models(self) -> list[Model]:
        """Get available models."""
        data = await self._request("GET", "/api/models")
        return [Model.model_validate(m) for m in data]

    # Connection test
    async def test_connection(self) -> bool:
        """Test API connection."""
        try:
            await self.get_models()
            return True
        except NanoChatAPIError:
            return False
