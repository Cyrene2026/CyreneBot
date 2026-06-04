from __future__ import annotations

from cyreneAI.core.schema.message import ContentPart, ContentPartType, MessageRole
from cyreneAI.core.schema.server import HTTPMessage


def test_http_message_preserves_content_parts() -> None:
    message = HTTPMessage(
        role=MessageRole.USER,
        content="ignored when content_parts is set",
        content_parts=[
            ContentPart(type=ContentPartType.TEXT, text="what is this?"),
            ContentPart(
                type=ContentPartType.IMAGE,
                url="https://example.test/image.png",
                mime_type="image/png",
            ),
        ],
    ).to_core_message()

    assert message.content is not None
    assert message.content[0].text == "what is this?"
    assert message.content[1].type == ContentPartType.IMAGE
    assert message.content[1].url == "https://example.test/image.png"
