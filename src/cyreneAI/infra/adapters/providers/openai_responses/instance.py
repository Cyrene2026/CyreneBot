from typing import Any, AsyncIterator, cast

from openai import AsyncOpenAI

from cyreneAI.core.errors.provider import (
    ProviderConfigurationError,
    ProviderError,
    ProviderResponseError,
)
from cyreneAI.core.schema.chat import ChatRequest, ChatResponse, ChatStreamChunk
from cyreneAI.core.schema.image import ImageGenerationRequest, ImageGenerationResponse
from cyreneAI.core.schema.provider import ProviderConfig, ProviderInfo, ProviderModel
from cyreneAI.infra.adapters.providers.model_mapper import map_provider_model
from cyreneAI.infra.adapters.providers.openai_responses.errors import raise_openai_error
from cyreneAI.infra.adapters.providers.openai_responses.mapper import (
    map_image_generation_request,
    map_image_generation_response,
    map_responses_request,
    map_responses_response,
    map_responses_stream_event,
)


class OpenAIResponsesProviderInstance:
    def __init__(
        self,
        config: ProviderConfig,
        info: ProviderInfo,
        client: Any | None = None,
    ) -> None:
        if not config.api_key:
            raise ProviderConfigurationError(
                "openai-responses provider 必需提供api_key"
            )

        self.config = config
        self.info = info
        self.timeout = config.timeout.total_seconds() if config.timeout else None
        self._client = client or AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=self.timeout,
        )

    async def close(self) -> None:
        await self._client.close()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        try:
            payload = map_responses_request(request)
            response = cast(Any, await self._client.responses.create(**payload))
            return map_responses_response(
                provider_id=self.config.provider_id,
                response=response,
            )
        except Exception as exc:
            raise_openai_error(exc)

    async def chat_stream(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatStreamChunk]:
        try:
            payload = map_responses_request(request)
            payload["stream"] = True
            stream = cast(Any, await self._client.responses.create(**payload))
        except Exception as exc:
            raise_openai_error(exc)

        try:
            async for event in stream:
                _raise_stream_event_error(event)
                chunk = map_responses_stream_event(
                    provider_id=self.config.provider_id,
                    event=event,
                )
                if chunk is not None:
                    yield chunk
        except ProviderError:
            raise
        except Exception as exc:
            raise_openai_error(exc)

    async def list_models(self) -> list[ProviderModel]:
        try:
            response = await self._client.models.list()
            return [
                model
                for model in (map_provider_model(item) for item in response.data)
                if model is not None
            ]
        except Exception as exc:
            raise_openai_error(exc)

    async def generate_image(
        self,
        request: ImageGenerationRequest,
    ) -> ImageGenerationResponse:
        try:
            payload = map_image_generation_request(request)
            response = cast(Any, await self._client.images.generate(**payload))
            return map_image_generation_response(
                provider_id=self.config.provider_id,
                model=request.model,
                response=response,
            )
        except Exception as exc:
            raise_openai_error(exc)


def _raise_stream_event_error(event: Any) -> None:
    event_type = getattr(event, "type", None)
    if event_type == "error":
        raise ProviderResponseError(message=_stream_error_message(event))
    if event_type == "response.failed":
        response = getattr(event, "response", None)
        error = getattr(response, "error", None)
        if error is not None:
            raise ProviderResponseError(message=_stream_error_message(error))
        raise ProviderResponseError(message="OpenAI Responses stream failed")


def _stream_error_message(error: Any) -> str:
    message = getattr(error, "message", None)
    code = getattr(error, "code", None)
    if isinstance(message, str) and message:
        if isinstance(code, str) and code:
            return f"{message} ({code})"
        return message
    return str(error)
