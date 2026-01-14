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
    capabilities: ModelCapabilities
    pricing: Optional[ModelPricing] = None
    subscription: Optional[dict[str, Any]] = None


class GenerateMessageRequest(BaseModel):
    """Request to generate a message."""

    message: Optional[str] = None
    model_id: str
    assistant_id: Optional[str] = Field(default=None, alias="assistantId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    conversation_id: Optional[str] = Field(default=None, alias="conversationId")
    web_search_enabled: Optional[bool] = Field(default=None, alias="webSearchEnabled")
    web_search_mode: Optional[str] = Field(default=None, alias="webSearchMode")
    reasoning_effort: Optional[str] = Field(default=None, alias="reasoningEffort")
    temporary: Optional[bool] = None

    model_config = {"populate_by_name": True}
