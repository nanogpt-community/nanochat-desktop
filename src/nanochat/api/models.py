"""Pydantic models for NanoChat API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """Conversation model."""

    id: str
    title: str
    user_id: str = Field(alias="userId")
    assistant_id: Optional[str] = Field(default=None, alias="assistantId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    model_id: Optional[str] = Field(default=None, alias="modelId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    message_count: int = Field(default=0, alias="messageCount")
    pinned: bool = False
    generating: bool = False
    cost_usd: Optional[float] = Field(default=None, alias="costUsd")

    model_config = {"populate_by_name": True}


class Message(BaseModel):
    """Message model."""

    id: str
    conversation_id: str = Field(alias="conversationId")
    role: str  # user | assistant | system
    content: str
    reasoning: Optional[str] = None
    model_id: Optional[str] = Field(default=None, alias="modelId")
    created_at: datetime = Field(alias="createdAt")
    token_count: Optional[int] = Field(default=None, alias="tokenCount")
    cost_usd: Optional[float] = Field(default=None, alias="costUsd")
    starred: Optional[bool] = None

    model_config = {"populate_by_name": True}


class ModelCapabilities(BaseModel):
    """Model capabilities."""

    vision: bool = False
    reasoning: bool = False
    images: bool = False
    video: bool = False


class ModelPricing(BaseModel):
    """Model pricing information."""

    prompt: Optional[str] = None
    completion: Optional[str] = None
    image: Optional[str] = None
    request: Optional[str] = None


class Model(BaseModel):
    """AI Model information."""

    id: str
    name: str
    description: Optional[str] = None
    enabled: bool
    pinned: bool
    is_favorite: bool = Field(default=False, alias="isFavorite")
    capabilities: ModelCapabilities
    pricing: Optional[ModelPricing] = None
    subscription: Optional[dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class Assistant(BaseModel):
    """Assistant model."""

    id: str
    name: str
    description: Optional[str] = None
    system_prompt: str = Field(alias="systemPrompt")
    is_default: bool = Field(default=False, alias="isDefault")
    default_model_id: Optional[str] = Field(default=None, alias="defaultModelId")
    default_web_search_mode: Optional[str] = Field(default=None, alias="defaultWebSearchMode")
    default_web_search_provider: Optional[str] = Field(default=None, alias="defaultWebSearchProvider")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class CreateAssistantRequest(BaseModel):
    """Request to create a new assistant."""

    name: str
    system_prompt: str = Field(alias="systemPrompt")
    description: Optional[str] = None
    default_model_id: Optional[str] = Field(default=None, alias="defaultModelId")
    default_web_search_mode: Optional[str] = Field(default=None, alias="defaultWebSearchMode")
    default_web_search_provider: Optional[str] = Field(default=None, alias="defaultWebSearchProvider")

    model_config = {"populate_by_name": True}


class UpdateAssistantRequest(BaseModel):
    """Request to update an assistant."""

    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")
    default_model_id: Optional[str] = Field(default=None, alias="defaultModelId")
    default_web_search_mode: Optional[str] = Field(default=None, alias="defaultWebSearchMode")
    default_web_search_provider: Optional[str] = Field(default=None, alias="defaultWebSearchProvider")

    model_config = {"populate_by_name": True}


class ImageAttachment(BaseModel):
    """Image attachment for message generation."""

    url: str
    storage_id: str = Field(alias="storageId")
    file_name: Optional[str] = Field(default=None, alias="fileName")

    model_config = {"populate_by_name": True}


class DocumentAttachment(BaseModel):
    """Document attachment for message generation."""

    url: str
    storage_id: str = Field(alias="storageId")
    file_name: Optional[str] = Field(default=None, alias="fileName")
    file_type: str = Field(alias="fileType")  # pdf, markdown, text, epub

    model_config = {"populate_by_name": True}


class GenerateMessageRequest(BaseModel):
    """Request to generate a message."""

    message: Optional[str] = None
    model_id: str = Field(alias="modelId")
    assistant_id: Optional[str] = Field(default=None, alias="assistantId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    conversation_id: Optional[str] = Field(default=None, alias="conversationId")
    web_search_enabled: Optional[bool] = Field(default=None, alias="webSearchEnabled")
    web_search_mode: Optional[str] = Field(default=None, alias="webSearchMode")
    web_search_provider: Optional[str] = Field(default=None, alias="webSearchProvider")
    reasoning_effort: Optional[str] = Field(default=None, alias="reasoningEffort")
    temporary: Optional[bool] = None
    # File attachments
    images: Optional[list[ImageAttachment]] = None
    documents: Optional[list[DocumentAttachment]] = None

    model_config = {"populate_by_name": True}


class SSEMessageStart(BaseModel):
    """SSE message_start event data."""

    conversation_id: str
    message_id: str


class SSEDelta(BaseModel):
    """SSE delta event data."""

    content: str
    reasoning: Optional[str] = None


class SSEMessageComplete(BaseModel):
    """SSE message_complete event data."""

    token_count: Optional[int] = None
    cost_usd: Optional[float] = None
    response_time_ms: Optional[int] = None


class SSEError(BaseModel):
    """SSE error event data."""

    error: str
