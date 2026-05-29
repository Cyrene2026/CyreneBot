from __future__ import annotations

from inspect import Parameter, Signature
from typing import Any

from cyreneAI.api._depends import PluginDependency, _resolve_dependency
from cyreneAI.core.errors.plugin import PluginConfigurationError, PluginInputError
from cyreneAI.core.schema.plugin import (
    PluginCommandRequest,
    PluginEventRequest,
    PluginTaskRequest,
)


def _default_usage(path: str) -> str:
    normalized = _normalize_command_path(path)
    if not normalized:
        return ""
    return f"/{normalized}"


def _usage_from_arguments(
    path: str,
    arguments: list[dict[str, Any]],
) -> str:
    base_usage = _default_usage(path)
    parts = [base_usage] if base_usage else []
    for argument in arguments:
        parts.append(_usage_argument(argument))
    return " ".join(parts)


def _usage_argument(argument: dict[str, Any]) -> str:
    name = str(argument["name"])
    argument_type = str(argument["type"])
    type_suffix = "" if argument_type == "str" else f":{argument_type}"
    if argument["required"]:
        return f"<{name}{type_suffix}>"
    default = _format_usage_default(argument.get("default"))
    if default is None:
        return f"[{name}{type_suffix}]"
    return f"[{name}{type_suffix}={default}]"


def _format_usage_default(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _handler_description(handler: Any) -> str:
    doc = getattr(handler, "__doc__", None)
    if not doc:
        return ""
    return doc.strip().splitlines()[0].strip()


def _command_arguments_metadata(
    handler_signature: Signature,
) -> list[dict[str, Any]]:
    arguments: list[dict[str, Any]] = []
    for parameter in handler_signature.parameters.values():
        if not _is_command_argument_parameter(parameter):
            continue

        argument_type = _command_argument_type_for_parameter(parameter)
        if argument_type is None:
            continue

        item: dict[str, Any] = {
            "name": parameter.name,
            "type": argument_type.__name__,
            "required": parameter.default is _empty,
        }
        if parameter.default is not _empty:
            item["default"] = _metadata_default(parameter.default)
        arguments.append(item)
    return arguments


def _metadata_default(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _build_handler_arguments(
    handler_signature: Signature,
    request: PluginCommandRequest | PluginTaskRequest | PluginEventRequest,
    runtime_context: Any,
    *,
    usage: str | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    slot_index = 0
    command_arg_index = 0
    has_command_arguments = False

    for parameter in handler_signature.parameters.values():
        if parameter.kind in {
            Parameter.VAR_POSITIONAL,
            Parameter.VAR_KEYWORD,
        }:
            raise PluginConfigurationError("插件命令 handler 不支持 *args 或 **kwargs")

        value = _resolve_handler_parameter(
            parameter,
            request,
            runtime_context,
            slot_index,
            command_arg_index,
            usage,
        )
        if value is _UNSET:
            continue

        is_command_argument = _is_command_argument_value(parameter, request)
        if is_command_argument:
            command_arg_index += 1
            has_command_arguments = True

        if parameter.default is _empty and not is_command_argument:
            slot_index = _advance_slot_index(
                slot_index,
                value,
                request,
                runtime_context,
            )

        if parameter.kind is Parameter.POSITIONAL_ONLY:
            args.append(value)
        else:
            kwargs[parameter.name] = value

    if (
        has_command_arguments
        and isinstance(request, PluginCommandRequest)
        and command_arg_index < len(request.command.args)
    ):
        raise PluginInputError(
            _format_command_input_error(
                f"插件命令 {request.command.name} 参数过多: "
                f"{' '.join(request.command.args[command_arg_index:])}",
                usage,
            )
        )

    return args, kwargs


def _validate_handler_signature(
    handler_signature: Signature,
    runtime_context: Any,
    handler_label: str = "插件命令",
) -> None:
    slot_index = 0
    for parameter in handler_signature.parameters.values():
        if parameter.kind in {
            Parameter.VAR_POSITIONAL,
            Parameter.VAR_KEYWORD,
        }:
            raise PluginConfigurationError(
                f"{handler_label} handler 不支持 *args 或 **kwargs"
            )
        if isinstance(parameter.default, PluginDependency):
            _resolve_dependency(parameter.default, runtime_context)
            continue
        if (
            handler_label == "插件命令"
            and _command_argument_type_for_parameter(parameter) is not None
        ):
            continue
        if parameter.default is not _empty:
            continue
        if parameter.name == "request":
            slot_index = max(slot_index, 1)
            continue
        if parameter.name in {"ctx", "context"}:
            slot_index = max(slot_index, 2)
            continue
        if slot_index < 2:
            slot_index += 1
            continue
        raise PluginConfigurationError(
            f"{handler_label} handler 参数 {parameter.name} 无法注入"
        )


def _resolve_handler_parameter(
    parameter: Parameter,
    request: PluginCommandRequest | PluginTaskRequest | PluginEventRequest,
    runtime_context: Any,
    slot_index: int,
    command_arg_index: int,
    usage: str | None,
) -> Any:
    if isinstance(parameter.default, PluginDependency):
        return _resolve_dependency(parameter.default, runtime_context, request)

    if parameter.name == "request":
        return request
    if parameter.name == "event" and isinstance(request, PluginEventRequest):
        return request.event
    if parameter.name in {"ctx", "context"}:
        return runtime_context
    if _is_command_argument_value(parameter, request):
        return _resolve_command_argument(
            parameter,
            request,
            command_arg_index,
            usage,
        )
    if parameter.default is not _empty:
        return _UNSET

    positional_slots = (request, runtime_context)
    if slot_index >= len(positional_slots):
        raise PluginConfigurationError(
            f"插件命令 handler 参数 {parameter.name} 无法注入"
        )
    return positional_slots[slot_index]


def _resolve_command_argument(
    parameter: Parameter,
    request: PluginCommandRequest,
    command_arg_index: int,
    usage: str | None,
) -> Any:
    argument_type = _command_argument_type_for_parameter(parameter)
    if argument_type is None:
        raise PluginConfigurationError(
            f"插件命令 handler 参数 {parameter.name} 不支持从命令参数解析"
        )
    if command_arg_index >= len(request.command.args):
        if parameter.default is not _empty:
            return _UNSET
        raise PluginInputError(
            _format_command_input_error(
                f"插件命令 {request.command.name} 缺少参数 {parameter.name}",
                usage,
            )
        )

    raw_value = request.command.args[command_arg_index]
    try:
        return _parse_command_argument(raw_value, argument_type)
    except ValueError as exc:
        raise PluginInputError(
            _format_command_input_error(
                f"插件命令 {request.command.name} 参数 {parameter.name} "
                f"应为 {argument_type.__name__}，收到 {raw_value!r}",
                usage,
            )
        ) from exc


def _format_command_input_error(message: str, usage: str | None) -> str:
    if not usage:
        return message
    return f"{message}；用法: {usage}"


def _parse_command_argument(raw_value: str, argument_type: type) -> Any:
    if argument_type is str:
        return raw_value
    if argument_type is int:
        return int(raw_value)
    if argument_type is float:
        return float(raw_value)
    if argument_type is bool:
        return _parse_bool_argument(raw_value)
    raise ValueError(f"unsupported argument type: {argument_type}")


def _parse_bool_argument(raw_value: str) -> bool:
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"invalid bool value: {raw_value}")


def _is_command_argument_value(
    parameter: Parameter,
    request: PluginCommandRequest | PluginTaskRequest | PluginEventRequest,
) -> bool:
    return (
        isinstance(request, PluginCommandRequest)
        and _is_command_argument_parameter(parameter)
    )


def _is_command_argument_parameter(parameter: Parameter) -> bool:
    return (
        _command_argument_type_for_parameter(parameter) is not None
        and not isinstance(parameter.default, PluginDependency)
        and parameter.kind
        in {
            Parameter.POSITIONAL_ONLY,
            Parameter.POSITIONAL_OR_KEYWORD,
            Parameter.KEYWORD_ONLY,
        }
    )


def _command_argument_type_for_parameter(parameter: Parameter) -> type | None:
    if parameter.name in {"request", "ctx", "context"}:
        return None
    return _command_argument_type(
        parameter.annotation
    ) or _command_argument_type_from_default(parameter) or str


def _command_argument_type(annotation: Any) -> type | None:
    if annotation in {str, int, float, bool}:
        return annotation
    if isinstance(annotation, str):
        return {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
        }.get(annotation.strip())
    return None


def _command_argument_type_from_default(parameter: Parameter) -> type | None:
    if parameter.default is _empty:
        return None
    if isinstance(parameter.default, bool):
        return bool
    if isinstance(parameter.default, int):
        return int
    if isinstance(parameter.default, float):
        return float
    if isinstance(parameter.default, str):
        return str
    return str


def _normalize_command_path(value: str) -> str:
    stripped = value.strip().removeprefix("/")
    if not stripped:
        return ""
    return " ".join(stripped.replace("/", " ").split()).lower()


def _advance_slot_index(
    slot_index: int,
    value: Any,
    request: PluginCommandRequest | PluginTaskRequest | PluginEventRequest,
    runtime_context: Any,
) -> int:
    if value is request:
        return max(slot_index, 1)
    if value is runtime_context:
        return max(slot_index, 2)
    return slot_index + 1


class _Unset:
    pass


_UNSET = _Unset()
_empty = Signature.empty
