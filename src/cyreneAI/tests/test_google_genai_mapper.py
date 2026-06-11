from __future__ import annotations

from google.genai.types import GenerateContentResponse

from cyreneAI.core.schema.chat import ChatFinishReason, ChatRequest
from cyreneAI.core.schema.image import ImageGenerationRequest
from cyreneAI.core.schema.message import (
    ContentPart,
    ContentPartType,
    Message,
    MessageRole,
)
from cyreneAI.core.schema.tool import ToolCall, ToolChoice, ToolDefinition
from cyreneAI.infra.adapters.providers.google_genai.mapper import (
    map_google_content_image_generation_request,
    map_google_genai_request,
    map_google_genai_response,
    map_google_genai_stream_chunk,
    should_use_google_generate_images,
)


def test_map_google_genai_request_builds_payload() -> None:
    request = ChatRequest(
        provider_id="provider-1",
        model="gemini-test",
        messages=[
            Message(
                role=MessageRole.USER,
                content=[
                    ContentPart(type=ContentPartType.TEXT, text="hello"),
                    ContentPart(
                        type=ContentPartType.IMAGE,
                        data="aW1hZ2UtYnl0ZXM=",
                        mime_type="image/png",
                    ),
                ],
            )
        ],
        temperature=0,
        max_tokens=16,
        tools=[
            ToolDefinition(
                name="lookup",
                description="Lookup a value.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                    },
                },
            )
        ],
        tool_choice=ToolChoice(mode="tool", name="lookup"),
    )

    payload = map_google_genai_request(request)

    assert payload["model"] == "gemini-test"
    assert payload["contents"] == [
        {
            "role": "user",
            "parts": [
                {"text": "hello"},
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": "aW1hZ2UtYnl0ZXM=",
                    }
                },
            ],
        }
    ]
    assert payload["config"]["temperature"] == 0
    assert payload["config"]["max_output_tokens"] == 16
    assert payload["config"]["tools"] == [
        {
            "function_declarations": [
                {
                    "name": "lookup",
                    "description": "Lookup a value.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                        },
                    },
                }
            ]
        }
    ]
    assert payload["config"]["tool_config"] == {
        "function_calling_config": {
            "mode": "ANY",
            "allowed_function_names": ["lookup"],
        }
    }


def test_map_google_genai_response_builds_core_response() -> None:
    google_response = GenerateContentResponse.model_validate(
        {
            "model_version": "gemini-test",
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {"text": "pong"},
                            {
                                "function_call": {
                                    "name": "lookup",
                                    "args": {"key": "value"},
                                }
                            },
                        ],
                    },
                    "finish_reason": "STOP",
                }
            ],
            "usage_metadata": {
                "prompt_token_count": 3,
                "candidates_token_count": 4,
                "total_token_count": 7,
            },
        }
    )

    response = map_google_genai_response("provider-1", google_response)

    assert response.provider_id == "provider-1"
    assert response.model == "gemini-test"
    assert response.finish_reason == ChatFinishReason.TOOL_CALLS
    assert response.usage is not None
    assert response.usage.prompt_tokens == 3
    assert response.usage.completion_tokens == 4
    assert response.usage.total_tokens == 7
    assert response.message is not None
    assert response.message.content is not None
    assert response.message.content[0].text == "pong"
    assert response.message.tool_calls is not None
    assert response.message.tool_calls[0].id == "lookup"
    assert response.tool_calls[0].id == "lookup"
    assert response.tool_calls[0].name == "lookup"
    assert response.tool_calls[0].arguments == '{"key": "value"}'


def test_map_google_genai_request_preserves_tool_feedback_turn() -> None:
    request = ChatRequest(
        provider_id="provider-1",
        model="gemini-test",
        messages=[
            Message(
                role=MessageRole.ASSISTANT,
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="lookup",
                        arguments='{"key":"value"}',
                    )
                ],
            ),
            Message(
                role=MessageRole.TOOL,
                name="lookup",
                tool_call_id="call-1",
                content=[ContentPart(type=ContentPartType.TEXT, text="found")],
            ),
        ],
    )

    payload = map_google_genai_request(request)

    assert payload["contents"] == [
        {
            "role": "model",
            "parts": [
                {
                    "function_call": {
                        "id": "call-1",
                        "name": "lookup",
                        "args": {"key": "value"},
                    }
                }
            ],
        },
        {
            "role": "user",
            "parts": [
                {
                    "function_response": {
                        "name": "lookup",
                        "response": {
                            "result": "found",
                        },
                    }
                }
            ],
        },
    ]


def test_map_google_genai_response_preserves_tool_only_message() -> None:
    google_response = GenerateContentResponse.model_validate(
        {
            "model_version": "gemini-test",
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {
                                "function_call": {
                                    "name": "lookup",
                                    "args": {"key": "value"},
                                }
                            },
                        ],
                    },
                    "finish_reason": "STOP",
                }
            ],
        }
    )

    response = map_google_genai_response("provider-1", google_response)

    assert response.message is not None
    assert response.message.content is None
    assert response.message.tool_calls is not None
    assert response.message.tool_calls[0].id == "lookup"


def test_map_google_genai_stream_chunk_maps_text_delta() -> None:
    google_response = GenerateContentResponse.model_validate(
        {
            "model_version": "gemini-test",
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [{"text": "Hel"}],
                    },
                }
            ],
        }
    )

    chunk = map_google_genai_stream_chunk("provider-1", google_response)

    assert chunk.provider_id == "provider-1"
    assert chunk.model == "gemini-test"
    assert chunk.delta_text == "Hel"
    assert chunk.finish_reason is None


def test_map_google_genai_stream_chunk_maps_reasoning_delta() -> None:
    google_response = GenerateContentResponse.model_validate(
        {
            "model_version": "gemini-test",
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [{"text": "thinking", "thought": True}],
                    },
                }
            ],
        }
    )

    chunk = map_google_genai_stream_chunk("provider-1", google_response)

    assert chunk.delta_text is None
    assert chunk.reasoning_delta == "thinking"


def test_map_google_genai_stream_chunk_maps_function_call_delta() -> None:
    google_response = GenerateContentResponse.model_validate(
        {
            "model_version": "gemini-test",
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {
                                "function_call": {
                                    "id": "call-1",
                                    "name": "lookup",
                                    "args": {"key": "value"},
                                }
                            }
                        ],
                    },
                    "finish_reason": "STOP",
                }
            ],
        }
    )

    chunk = map_google_genai_stream_chunk("provider-1", google_response)

    assert chunk.finish_reason == ChatFinishReason.TOOL_CALLS
    assert len(chunk.tool_call_deltas) == 1
    delta = chunk.tool_call_deltas[0]
    assert delta.id == "call-1"
    assert delta.name == "lookup"
    assert delta.arguments == '{"key": "value"}'


def test_map_google_genai_stream_chunk_maps_finish_and_usage() -> None:
    google_response = GenerateContentResponse.model_validate(
        {
            "model_version": "gemini-test",
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [],
                    },
                    "finish_reason": "MAX_TOKENS",
                }
            ],
            "usage_metadata": {
                "prompt_token_count": 3,
                "candidates_token_count": 4,
                "total_token_count": 7,
            },
        }
    )

    chunk = map_google_genai_stream_chunk("provider-1", google_response)

    assert chunk.finish_reason == ChatFinishReason.LENGTH
    assert chunk.usage is not None
    assert chunk.usage.prompt_tokens == 3
    assert chunk.usage.completion_tokens == 4
    assert chunk.usage.total_tokens == 7


def test_google_image_generation_route_selection() -> None:
    assert should_use_google_generate_images(
        ImageGenerationRequest(
            provider_id="google",
            model="imagen-4.0-generate-preview",
            prompt="hello",
        )
    )
    assert not should_use_google_generate_images(
        ImageGenerationRequest(
            provider_id="google",
            model="gemini-2.5-flash-image",
            prompt="hello",
        )
    )
    assert not should_use_google_generate_images(
        ImageGenerationRequest(
            provider_id="google",
            model="imagen-proxy",
            prompt="hello",
            metadata={"google_api_type": "generate_content"},
        )
    )


def test_map_google_content_image_generation_request_builds_payload() -> None:
    payload = map_google_content_image_generation_request(
        ImageGenerationRequest(
            provider_id="google",
            model="gemini-2.5-flash-image",
            prompt="draw a small robot",
            count=1,
            size="1:1",
            metadata={
                "mime_type": "image/png",
            },
        )
    )

    assert payload == {
        "model": "gemini-2.5-flash-image",
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "draw a small robot",
                    }
                ],
            }
        ],
        "config": {
            "response_modalities": ["IMAGE"],
            "image_config": {
                "aspect_ratio": "1:1",
                "output_mime_type": "image/png",
            },
        },
    }
