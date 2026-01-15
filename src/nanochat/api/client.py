"""HTTP client for NanoChat API."""

import httpx
import json
from typing import Optional

from .models import Conversation, Message, Model, GenerateMessageRequest
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

    # Connection test
    async def test_connection(self) -> bool:
        """Test API connection."""
        try:
            await self.get_models()
            return True
        except NanoChatAPIError:
            return False
