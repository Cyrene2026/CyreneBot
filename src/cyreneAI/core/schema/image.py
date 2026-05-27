from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from cyreneAI.core.schema.base import CyreneAISchema


class ImageGenerationRequest(CyreneAISchema):
    """
    图片生成请求schema
    """

    provider_id: str
    model: str
    prompt: str
    count: int = Field(default=1, ge=1)
    size: str | None = None
    quality: str | None = None
    response_format: Literal["url", "b64_json"] = "b64_json"
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedImage(CyreneAISchema):
    """
    生成图片schema
    """

    index: int = Field(ge=0)
    url: str | None = None
    b64_json: str | None = None
    mime_type: str | None = None
    revised_prompt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageGenerationResponse(CyreneAISchema):
    """
    图片生成响应schema
    """

    provider_id: str
    model: str | None = None
    images: list[GeneratedImage] = Field(default_factory=list)
    raw: dict[str, Any] | None = None
