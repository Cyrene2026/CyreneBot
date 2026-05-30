from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from contextlib import suppress
from pathlib import Path
from types import ModuleType

import pytest

from cyreneAI.api import PluginTestClient
from cyreneAI.api.cli import PluginInitError, init_plugin_project, main


def test_init_plugin_project_creates_minimal_runnable_plugin(tmp_path: Path) -> None:
    project_path = init_plugin_project(tmp_path / "my_plugin", author="Tester")

    manifest = json.loads((project_path / "plugin.json").read_text("utf-8"))
    assert manifest == {
        "plugin_id": "my_plugin",
        "name": "My Plugin",
        "version": "0.1.0",
        "description": "A CyreneAI plugin.",
        "entrypoint": "main.py",
        "author": "Tester",
        "license": "MIT",
        "keywords": [],
        "capabilities": ["bot_command"],
        "permissions": [],
    }
    assert (project_path / "pyproject.toml").is_file()
    assert (project_path / "tests" / "test_plugin.py").is_file()

    plugin_module = _load_generated_main(project_path)

    async def run() -> None:
        client = PluginTestClient(getattr(plugin_module, "plugin"))
        result = await client.command("/hello Cyrene")

        assert result.has_text("Hello, Cyrene!")

    asyncio.run(run())


def test_init_plugin_project_refuses_to_overwrite_existing_files(
    tmp_path: Path,
) -> None:
    project_path = init_plugin_project(tmp_path / "my_plugin")

    with pytest.raises(PluginInitError):
        init_plugin_project(project_path)


def test_init_plugin_project_can_force_overwrite(tmp_path: Path) -> None:
    project_path = init_plugin_project(tmp_path / "my_plugin")
    (project_path / "main.py").write_text("broken", encoding="utf-8")

    init_plugin_project(project_path, force=True)

    assert "CyreneBot" in (project_path / "main.py").read_text("utf-8")


def test_cli_init_command_reports_created_project(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_path = tmp_path / "cli_plugin"

    exit_code = main(["init", str(project_path), "--plugin-id", "demo.cli"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"Initialized CyreneAI plugin at {project_path}" in captured.out
    assert json.loads((project_path / "plugin.json").read_text("utf-8"))[
        "plugin_id"
    ] == "demo.cli"


def test_cli_init_command_returns_error_for_existing_project(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_path = init_plugin_project(tmp_path / "my_plugin")

    exit_code = main(["init", str(project_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "target files already exist" in captured.err


def _load_generated_main(project_path: Path) -> ModuleType:
    module_name = "_generated_cyrene_plugin_main"
    spec = importlib.util.spec_from_file_location(module_name, project_path / "main.py")
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(project_path))
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
        with suppress(ValueError):
            sys.path.remove(str(project_path))
    return module
