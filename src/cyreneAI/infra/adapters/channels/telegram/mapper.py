from __future__ import annotations

from typing import Any, cast

from cyreneAI.core.errors.bot import BotActionError, BotInputError
from cyreneAI.core.schema.bot import (
    BotAction,
    BotActionType,
    BotEvent,
    BotEventType,
    BotMessage,
)
from cyreneAI.core.schema.message import ContentPart, ContentPartType


def map_telegram_update_to_bot_event(
    update: dict[str, Any],
    *,
    channel_id: str = "telegram",
) -> BotEvent:
    """
    将 Telegram update 映射为标准 BotEvent。
    """
    update_id = str(update.get("update_id", ""))
    message = update.get("message")
    if not isinstance(message, dict):
        return BotEvent(
            event_id=update_id,
            event_type=BotEventType.UNKNOWN,
            channel_id=channel_id,
            session_id=f"{channel_id}:unknown:{update_id}",
            metadata={"telegram_update_id": update_id},
        )
    message_data = cast(dict[str, Any], message)

    chat: Any = message_data.get("chat")
    if not isinstance(chat, dict) or chat.get("id") is None:
        raise BotInputError("Telegram message update must include chat.id")
    chat_data = cast(dict[str, Any], chat)

    chat_id = str(chat_data["id"])
    sender: Any = message_data.get("from")
    sender_data = cast(dict[str, Any], sender) if isinstance(sender, dict) else None
    user_id = (
        str(sender_data["id"])
        if sender_data is not None and sender_data.get("id") is not None
        else None
    )
    text = _message_text(message_data)
    event_type = (
        BotEventType.COMMAND
        if text is not None and text.strip().startswith("/")
        else BotEventType.MESSAGE
    )
    message_id = (
        str(message_data["message_id"])
        if message_data.get("message_id") is not None
        else None
    )

    return BotEvent(
        event_id=update_id,
        event_type=event_type,
        channel_id=channel_id,
        session_id=f"{channel_id}:{chat_id}",
        user_id=user_id,
        thread_id=chat_id,
        message=BotMessage(
            message_id=message_id,
            sender_id=user_id,
            content=_message_content_parts(message_data, text),
            metadata={
                "telegram_chat_id": chat_id,
                "telegram_chat_type": str(chat_data.get("type") or ""),
            },
        ),
        metadata={
            "telegram_update_id": update_id,
            "telegram_chat_id": chat_id,
            "telegram_chat_type": str(chat_data.get("type") or ""),
        },
    )


def map_bot_action_to_send_message_payload(action: BotAction) -> dict[str, Any]:
    """
    将标准 BotAction 映射为 Telegram sendMessage payload。
    """
    if action.action_type != BotActionType.SEND_MESSAGE:
        raise BotActionError(
            f"Telegram channel does not support action {action.action_type}"
        )

    chat_id = _resolve_chat_id(action)
    text = _action_text(action)
    if not text:
        raise BotActionError("Telegram sendMessage action must include text")

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if action.thread_id and action.thread_id != chat_id:
        payload["message_thread_id"] = action.thread_id
    return payload


def _message_text(message: dict[str, Any]) -> str | None:
    text = message.get("text")
    if isinstance(text, str):
        return text
    caption = message.get("caption")
    if isinstance(caption, str):
        return caption
    return None


def _message_content_parts(
    message: dict[str, Any],
    text: str | None,
) -> list[ContentPart]:
    parts: list[ContentPart] = [
        ContentPart(
            type=ContentPartType.TEXT,
            text=text or "",
        )
    ]
    parts.extend(_image_content_parts(message))
    return parts


def _image_content_parts(message: dict[str, Any]) -> list[ContentPart]:
    photo = message.get("photo")
    if isinstance(photo, list) and photo:
        photo_items = [
            cast(dict[str, Any], item) for item in photo if isinstance(item, dict)
        ]
        if photo_items:
            item = photo_items[-1]
            return [
                ContentPart(
                    type=ContentPartType.IMAGE,
                    mime_type="image/jpeg",
                    metadata={
                        "telegram_file_id": str(item.get("file_id") or ""),
                        "telegram_file_unique_id": str(
                            item.get("file_unique_id") or ""
                        ),
                        "telegram_width": str(item.get("width") or ""),
                        "telegram_height": str(item.get("height") or ""),
                    },
                )
            ]

    document = message.get("document")
    if isinstance(document, dict):
        document_data = cast(dict[str, Any], document)
        mime_type = document_data.get("mime_type")
        if isinstance(mime_type, str) and mime_type.startswith("image/"):
            return [
                ContentPart(
                    type=ContentPartType.IMAGE,
                    mime_type=mime_type,
                    metadata={
                        "telegram_file_id": str(document_data.get("file_id") or ""),
                        "telegram_file_unique_id": str(
                            document_data.get("file_unique_id") or ""
                        ),
                        "telegram_file_name": str(document_data.get("file_name") or ""),
                    },
                )
            ]

    return []


def _resolve_chat_id(action: BotAction) -> str:
    telegram_chat_id = action.metadata.get("telegram_chat_id")
    if telegram_chat_id:
        return str(telegram_chat_id)
    if action.thread_id:
        return action.thread_id
    if action.recipient_id:
        return action.recipient_id
    prefix = f"{action.channel_id}:"
    if action.session_id.startswith(prefix):
        return action.session_id.removeprefix(prefix)
    raise BotActionError("Telegram action must include chat id")


def _action_text(action: BotAction) -> str:
    if action.message is None:
        return ""
    chunks = [
        part.text
        for part in action.message.content
        if part.type == ContentPartType.TEXT and part.text
    ]
    return "\n".join(chunks)
