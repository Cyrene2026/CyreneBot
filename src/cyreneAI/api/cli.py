from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from textwrap import dedent
from typing import Sequence


class PluginInitError(ValueError):
    """Raised when a plugin project cannot be initialized safely."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        try:
            project_path = init_plugin_project(
                args.path,
                plugin_id=args.plugin_id,
                name=args.name,
                description=args.description,
                author=args.author,
                force=args.force,
            )
        except PluginInitError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print(f"Initialized CyreneAI plugin at {project_path}")
        return 0

    parser.print_help()
    return 2


def init_plugin_project(
    path: str | Path,
    *,
    plugin_id: str | None = None,
    name: str | None = None,
    description: str | None = None,
    author: str | None = None,
    force: bool = False,
) -> Path:
    project_path = Path(path)
    project_name = project_path.resolve().name
    if not project_name:
        raise PluginInitError("plugin path must include a directory name")

    resolved_plugin_id = plugin_id or _normalize_plugin_id(project_name)
    resolved_name = name or _humanize_name(project_name)
    resolved_description = description or "A CyreneAI plugin."

    files = {
        "pyproject.toml": _pyproject_text(resolved_plugin_id),
        "plugin.json": _manifest_text(
            plugin_id=resolved_plugin_id,
            name=resolved_name,
            description=resolved_description,
            author=author,
        ),
        "main.py": _main_text(),
        "tests/test_plugin.py": _test_text(),
        "README.md": _readme_text(resolved_name),
    }

    _ensure_writable(project_path, files, force=force)
    project_path.mkdir(parents=True, exist_ok=True)
    for relative_path, content in files.items():
        target = project_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")

    return project_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cyrene-plugin",
        description="CyreneAI plugin SDK helper commands.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="create a minimal CyreneAI plugin project",
    )
    init_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="target plugin directory; defaults to the current directory",
    )
    init_parser.add_argument(
        "--plugin-id",
        help="plugin id for plugin.json; defaults to a normalized directory name",
    )
    init_parser.add_argument(
        "--name",
        help="display name for plugin.json; defaults to a humanized directory name",
    )
    init_parser.add_argument(
        "--description",
        help="description for plugin.json",
    )
    init_parser.add_argument(
        "--author",
        help="author field for plugin.json",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite generated files if they already exist",
    )
    return parser


def _ensure_writable(
    project_path: Path,
    files: dict[str, str],
    *,
    force: bool,
) -> None:
    existing = [
        str(project_path / relative_path)
        for relative_path in files
        if (project_path / relative_path).exists()
    ]
    if existing and not force:
        joined = ", ".join(existing)
        raise PluginInitError(f"target files already exist: {joined}")


def _normalize_plugin_id(value: str) -> str:
    plugin_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip()).strip("._-")
    plugin_id = plugin_id.replace("-", "_").lower()
    if not plugin_id:
        raise PluginInitError("plugin id cannot be empty")
    return plugin_id


def _humanize_name(value: str) -> str:
    words = re.split(r"[\s_.-]+", value.strip())
    return " ".join(word.capitalize() for word in words if word) or "CyreneAI Plugin"


def _manifest_text(
    *,
    plugin_id: str,
    name: str,
    description: str,
    author: str | None,
) -> str:
    manifest: dict[str, object] = {
        "plugin_id": plugin_id,
        "name": name,
        "version": "0.1.0",
        "description": description,
        "entrypoint": "main.py",
        "author": author,
        "license": "MIT",
        "keywords": [],
        "capabilities": ["bot_command"],
        "permissions": [],
    }
    if author is None:
        manifest.pop("author")
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def _main_text() -> str:
    return dedent(
        f'''\
        from cyreneAI.api import CyreneBot


        plugin = CyreneBot()


        @plugin.command
        async def hello(name: str = "world") -> str:
            return f"Hello, {{name}}!"
        '''
    )


def _test_text() -> str:
    return dedent(
        '''\
        import asyncio

        from main import plugin
        from cyreneAI.api import PluginTestClient


        def test_hello_command() -> None:
            async def run() -> None:
                client = PluginTestClient(plugin)
                result = await client.command("/hello Cyrene")

                assert result.has_text("Hello, Cyrene!")

            asyncio.run(run())
        '''
    )


def _readme_text(name: str) -> str:
    return dedent(
        f'''\
        # {name}

        Minimal CyreneAI plugin project.

        ```bash
        pytest
        ```
        '''
    )


def _pyproject_text(plugin_id: str) -> str:
    package_name = plugin_id.replace("_", "-")
    return dedent(
        f'''\
        [project]
        name = "{package_name}"
        version = "0.1.0"
        requires-python = ">=3.12"
        dependencies = ["cyreneai-plugin-sdk"]

        [dependency-groups]
        dev = ["pytest"]

        [tool.pytest.ini_options]
        pythonpath = ["."]
        '''
    )


if __name__ == "__main__":
    raise SystemExit(main())
