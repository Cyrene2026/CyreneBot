from __future__ import annotations

from types import SimpleNamespace

from anthropic.types import Message as AnthropicMessage

from cyreneAI.core.schema.chat import ChatFinishReason, ChatRequest
from cyreneAI.core.schema.message import (
    ContentPart,
    ContentPartType,
    Message,
    MessageRole,
)
from cyreneAI.core.schema.tool import ToolCall, ToolChoice, ToolDefinition
from cyreneAI.infra.adapters.providers.anthropic.mapper import (
    map_anthropic_request,
    map_anthropic_response,
    map_anthropic_stream_event,
)


def test_map_anthropic_request_builds_payload() -> None:
    request = ChatRequest(
        provider_id="provider-1",
        model="claude-test",
        messages=[
            Message(
                role=MessageRole.SYSTEM,
                content=[ContentPart(type=ContentPartType.TEXT, text="be brief")],
            ),
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
            ),
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

    payload = map_anthropic_request(request)

    assert payload["model"] == "claude-test"
    assert payload["system"] == "be brief"
    assert payload["messages"] == [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "hello",
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": "aW1hZ2UtYnl0ZXM=",
                    },
                },
            ],
        }
    ]
    assert payload["temperature"] == 0
    assert payload["max_tokens"] == 16
    assert payload["tools"] == [
        {
            "name": "lookup",
            "description": "Lookup a value.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                },
            },
        }
    ]
    assert payload["tool_choice"] == {"type": "tool", "name": "lookup"}


def test_map_anthropic_response_builds_core_response() -> None:
    anthropic_response = AnthropicMessage.model_validate(
        {
            "id": "msg-1",
            "type": "message",
            "role": "assistant",
            "model": "claude-test",
            "content": [
                {
                    "type": "text",
                    "text": "pong",
                },
                {
                    "type": "tool_use",
                    "id": "toolu-1",
                    "name": "lookup",
                    "input": {"key": "value"},
                },
            ],
            "stop_reason": "tool_use",
            "usage": {
                "input_tokens": 3,
                "output_tokens": 4,
            },
        }
    )

    response = map_anthropic_response("provider-1", anthropic_response)

    assert response.provider_id == "provider-1"
    assert response.model == "claude-test"
    assert response.finish_reason == ChatFinishReason.TOOL_CALLS
    assert response.usage is not None
    assert response.usage.prompt_tokens == 3
    assert response.usage.completion_tokens == 4
    assert response.usage.total_tokens == 7
    assert response.message is not None
    assert response.message.content is not None
    assert response.message.content[0].text == "pong"
    assert response.message.tool_calls is not None
    assert response.message.tool_calls[0].id == "toolu-1"
    assert response.tool_calls[0].id == "toolu-1"
    assert response.tool_calls[0].name == "lookup"
    assert response.tool_calls[0].arguments == '{"key": "value"}'


def test_map_anthropic_request_preserves_tool_feedback_turn() -> None:
    request = ChatRequest(
        provider_id="provider-1",
        model="claude-test",
        messages=[
            Message(
                role=MessageRole.ASSISTANT,
                tool_calls=[
                    ToolCall(
                        id="toolu-1",
                        name="lookup",
                        arguments='{"key":"value"}',
                    )
                ],
            ),
            Message(
                role=MessageRole.TOOL,
                name="lookup",
                tool_call_id="toolu-1",
                content=[ContentPart(type=ContentPartType.TEXT, text="found")],
            ),
        ],
    )

    payload = map_anthropic_request(request)

    assert payload["messages"] == [
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu-1",
                    "name": "lookup",
                    "input": {"key": "value"},
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu-1",
                    "content": "found",
                }
            ],
        },
    ]


def test_map_anthropic_response_preserves_tool_only_message() -> None:
    anthropic_response = AnthropicMessage.model_validate(
        {
            "id": "msg-1",
            "type": "message",
            "role": "assistant",
            "model": "claude-test",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu-1",
                    "name": "lookup",
                    "input": {"key": "value"},
                },
            ],
            "stop_reason": "tool_use",
            "usage": {
                "input_tokens": 3,
                "output_tokens": 4,
            },
        }
    )

    response = map_anthropic_response("provider-1", anthropic_response)

    assert response.message is not None
    assert response.message.content is None
    assert response.message.tool_calls is not None
    assert response.message.tool_calls[0].id == "toolu-1"


def test_map_anthropic_stream_event_maps_text_delta() -> None:
    event = SimpleNamespace(
        type="content_block_delta",
        index=0,
        delta=SimpleNamespace(type="text_delta", text="Hel"),
    )

    chunk = map_anthropic_stream_event("provider-1", event)

    assert chunk is not None
    assert chunk.provider_id == "provider-1"
    assert chunk.delta_text == "Hel"
    assert chunk.finish_reason is None


def test_map_anthropic_stream_event_maps_tool_call_deltas() -> None:
    start = SimpleNamespace(
        type="content_block_start",
        index=1,
        content_block=SimpleNamespace(
            type="tool_use",
            id="toolu-1",
            name="lookup",
            input={},
        ),
    )
    delta = SimpleNamespace(
        type="content_block_delta",
        index=1,
        delta=SimpleNamespace(type="input_json_delta", partial_json='{"key"'),
    )

    start_chunk = map_anthropic_stream_event("provider-1", start)
    delta_chunk = map_anthropic_stream_event("provider-1", delta)

    assert start_chunk is not None
    assert len(start_chunk.tool_call_deltas) == 1
    assert start_chunk.tool_call_deltas[0].index == 1
    assert start_chunk.tool_call_deltas[0].id == "toolu-1"
    assert start_chunk.tool_call_deltas[0].name == "lookup"
    assert delta_chunk is not None
    assert delta_chunk.tool_call_deltas[0].arguments == '{"key"'


def test_map_anthropic_stream_event_maps_message_delta() -> None:
    event = SimpleNamespace(
        type="message_delta",
        delta=SimpleNamespace(stop_reason="tool_use"),
        usage=SimpleNamespace(input_tokens=3, output_tokens=4),
    )

    chunk = map_anthropic_stream_event("provider-1", event)

    assert chunk is not None
    assert chunk.finish_reason == ChatFinishReason.TOOL_CALLS
    assert chunk.usage is not None
    assert chunk.usage.prompt_tokens == 3
    assert chunk.usage.completion_tokens == 4
    assert chunk.usage.total_tokens == 7
