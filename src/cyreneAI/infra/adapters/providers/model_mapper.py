from __future__ import annotations

from typing import Any, cast

from cyreneAI.core.schema.provider import ProviderModel


def map_provider_model(item: Any) -> ProviderModel | None:
    if isinstance(item, str):
        model_id = item.strip()
        if not model_id:
            return None
        return ProviderModel(model_id=model_id)

    model_id = _first_string_attr(item, "id", "name", "model")
    if not model_id:
        return None

    name = _first_string_attr(item, "display_name", "name", "id")
    metadata: dict[str, str] = {}
    owned_by = _first_string_attr(item, "owned_by")
    if owned_by:
        metadata["owned_by"] = owned_by

    return ProviderModel(
        model_id=model_id,
        name=name if name != model_id else None,
        metadata=metadata,
    )


def _first_string_attr(item: Any, *names: str) -> str | None:
    for name in names:
        value = getattr(item, name, None)
        if isinstance(value, str) and value:
            return value
        if isinstance(item, dict):
            value = cast(dict[str, Any], item).get(name)
            if isinstance(value, str) and value:
                return value
    return None
