from __future__ import annotations

from types import SimpleNamespace

from openai.types.responses import Response

from cyreneAI.core.schema.chat import ChatFinishReason, ChatRequest
from cyreneAI.core.schema.message import (
    ContentPart,
    ContentPartType,
    Message,
    MessageRole,
)
from cyreneAI.core.schema.tool import ToolCall, ToolChoice, ToolDefinition
from cyreneAI.infra.adapters.providers.openai_responses.mapper import (
    map_responses_request,
    map_responses_response,
    map_responses_stream_event,
)


def test_map_responses_request_builds_payload() -> None:
    request = ChatRequest(
        provider_id="provider-1",
        model="test-model",
        messages=[
            Message(
                role=MessageRole.USER,
                content=[
                    ContentPart(type=ContentPartType.TEXT, text="hello"),
                    ContentPart(
                        type=ContentPartType.IMAGE,
                        data="aW1hZ2UtYnl0ZXM=",
                        mime_type="image/png",
                        detail="high",
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

    payload = map_responses_request(request)

    assert payload["model"] == "test-model"
    assert payload["input"] == [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "hello",
                },
                {
                    "type": "input_image",
                    "image_url": "data:image/png;base64,aW1hZ2UtYnl0ZXM=",
                    "detail": "high",
                },
            ],
        }
    ]
    assert payload["temperature"] == 0
    assert payload["max_output_tokens"] == 16
    assert payload["tools"] == [
        {
            "type": "function",
            "name": "lookup",
            "description": "Lookup a value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                },
            },
            "strict": None,
        }
    ]
    assert payload["tool_choice"] == {
        "type": "function",
        "name": "lookup",
    }


def test_map_responses_response_builds_core_response() -> None:
    response = Response(
        id="resp-test",
        created_at=1,
        model="test-model",
        object="response",
        output=[
            {
                "id": "msg-1",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "pong",
                        "annotations": [],
                    }
                ],
                "status": "completed",
            },
            {
                "type": "function_call",
                "call_id": "call-1",
                "name": "lookup",
                "arguments": '{"key":"value"}',
            },
        ],
        parallel_tool_calls=True,
        tool_choice="auto",
        tools=[],
        status="completed",
        usage={
            "input_tokens": 3,
            "input_tokens_details": {
                "cached_tokens": 0,
            },
            "output_tokens": 4,
            "output_tokens_details": {
                "reasoning_tokens": 0,
            },
            "total_tokens": 7,
        },
    )

    mapped = map_responses_response("provider-1", response)

    assert mapped.provider_id == "provider-1"
    assert mapped.model == "test-model"
    assert mapped.finish_reason == ChatFinishReason.TOOL_CALLS
    assert mapped.usage is not None
    assert mapped.usage.prompt_tokens == 3
    assert mapped.usage.completion_tokens == 4
    assert mapped.usage.total_tokens == 7
    assert mapped.message is not None
    assert mapped.message.content is not None
    assert mapped.message.content[0].text == "pong"
    assert mapped.message.tool_calls is not None
    assert mapped.message.tool_calls[0].id == "call-1"
    assert mapped.tool_calls[0].id == "call-1"
    assert mapped.tool_calls[0].name == "lookup"
    assert mapped.tool_calls[0].arguments == '{"key":"value"}'


def test_map_responses_request_ignores_unmappable_image_part() -> None:
    request = ChatRequest(
        provider_id="provider-1",
        model="test-model",
        messages=[
            Message(
                role=MessageRole.USER,
                content=[
                    ContentPart(type=ContentPartType.TEXT, text="hello"),
                    ContentPart(
                        type=ContentPartType.IMAGE,
                        metadata={
                            "qq_attachment_url": "https://qq.example/private.png",
                        },
                    ),
                ],
            )
        ],
    )

    payload = map_responses_request(request)

    assert payload["input"] == [
        {
            "role": "user",
            "content": "hello",
        }
    ]


def test_map_responses_request_preserves_tool_feedback_turn() -> None:
    request = ChatRequest(
        provider_id="provider-1",
        model="test-model",
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

    payload = map_responses_request(request)

    assert payload["input"] == [
        {
            "type": "function_call",
            "call_id": "call-1",
            "name": "lookup",
            "arguments": '{"key":"value"}',
        },
        {
            "type": "function_call_output",
            "call_id": "call-1",
            "output": "found",
        },
    ]


def test_map_responses_request_drops_unanswered_tool_call_history() -> None:
    request = ChatRequest(
        provider_id="provider-1",
        model="test-model",
        messages=[
            Message(
                role=MessageRole.USER,
                content=[ContentPart(type=ContentPartType.TEXT, text="hello")],
            ),
            Message(
                role=MessageRole.ASSISTANT,
                tool_calls=[
                    ToolCall(
                        id="call-orphan",
                        name="lookup",
                        arguments='{"key":"value"}',
                    )
                ],
            ),
            Message(
                role=MessageRole.USER,
                content=[ContentPart(type=ContentPartType.TEXT, text="continue")],
            ),
        ],
    )

    payload = map_responses_request(request)

    assert payload["input"] == [
        {
            "role": "user",
            "content": "hello",
        },
        {
            "role": "user",
            "content": "continue",
        },
    ]


def test_map_responses_response_preserves_tool_only_message() -> None:
    response = Response(
        id="resp-test",
        created_at=1,
        model="test-model",
        object="response",
        output=[
            {
                "type": "function_call",
                "call_id": "call-1",
                "name": "lookup",
                "arguments": '{"key":"value"}',
            },
        ],
        parallel_tool_calls=True,
        tool_choice="auto",
        tools=[],
        status="completed",
    )

    mapped = map_responses_response("provider-1", response)

    assert mapped.message is not None
    assert mapped.message.content is None
    assert mapped.message.tool_calls is not None
    assert mapped.message.tool_calls[0].id == "call-1"


def test_map_responses_stream_event_maps_text_delta() -> None:
    event = SimpleNamespace(
        type="response.output_text.delta",
        delta="Hel",
        response=SimpleNamespace(model="test-model"),
    )

    mapped = map_responses_stream_event("provider-1", event)

    assert mapped is not None
    assert mapped.provider_id == "provider-1"
    assert mapped.model == "test-model"
    assert mapped.delta_text == "Hel"
    assert mapped.finish_reason is None


def test_map_responses_stream_event_maps_reasoning_delta() -> None:
    event = SimpleNamespace(
        type="response.reasoning_text.delta",
        delta="thinking",
        response=SimpleNamespace(model="test-model"),
    )

    mapped = map_responses_stream_event("provider-1", event)

    assert mapped is not None
    assert mapped.reasoning_delta == "thinking"


def test_map_responses_stream_event_maps_function_call_output_item() -> None:
    event = SimpleNamespace(
        type="response.output_item.done",
        output_index=1,
        item=SimpleNamespace(
            type="function_call",
            call_id="call-1",
            name="lookup",
            arguments='{"key":"value"}',
        ),
    )

    mapped = map_responses_stream_event("provider-1", event)

    assert mapped is not None
    assert len(mapped.tool_call_deltas) == 1
    delta = mapped.tool_call_deltas[0]
    assert delta.index == 1
    assert delta.id == "call-1"
    assert delta.name == "lookup"
    assert delta.arguments == '{"key":"value"}'


def test_map_responses_stream_event_maps_completed_response() -> None:
    response = Response(
        id="resp-test",
        created_at=1,
        model="test-model",
        object="response",
        output=[],
        parallel_tool_calls=True,
        tool_choice="auto",
        tools=[],
        status="completed",
        usage={
            "input_tokens": 3,
            "input_tokens_details": {
                "cached_tokens": 0,
            },
            "output_tokens": 4,
            "output_tokens_details": {
                "reasoning_tokens": 0,
            },
            "total_tokens": 7,
        },
    )
    event = SimpleNamespace(type="response.completed", response=response)

    mapped = map_responses_stream_event("provider-1", event)

    assert mapped is not None
    assert mapped.model == "test-model"
    assert mapped.finish_reason == ChatFinishReason.STOP
    assert mapped.usage is not None
    assert mapped.usage.prompt_tokens == 3
    assert mapped.usage.completion_tokens == 4
    assert mapped.usage.total_tokens == 7
