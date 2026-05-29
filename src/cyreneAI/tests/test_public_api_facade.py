from __future__ import annotations

from cyreneAI.api import (
    CyreneBot,
    CyreneRouter,
    Depends,
    PluginTestClient,
    PluginTestCommandResult,
    PluginTestEventResult,
    PluginTestTaskResult,
    text,
)
from cyreneAI.api.plugin import (
    CyreneBot as PluginCyreneBot,
    CyreneRouter as PluginCyreneRouter,
    Depends as plugin_depends,
    text as plugin_text,
)
from cyreneAI.api.testing import (
    PluginTestClient as TestingPluginTestClient,
    PluginTestCommandResult as TestingPluginTestCommandResult,
    PluginTestEventResult as TestingPluginTestEventResult,
    PluginTestTaskResult as TestingPluginTestTaskResult,
)


def test_public_api_facade_exports_plugin_dsl() -> None:
    assert CyreneBot is PluginCyreneBot
    assert CyreneRouter is PluginCyreneRouter
    assert Depends is plugin_depends
    assert text is plugin_text
    assert PluginTestClient is TestingPluginTestClient
    assert PluginTestCommandResult is TestingPluginTestCommandResult
    assert PluginTestEventResult is TestingPluginTestEventResult
    assert PluginTestTaskResult is TestingPluginTestTaskResult
