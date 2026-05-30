from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cyreneAI.core.errors.base import ConflictError
from cyreneAI.core.errors.plugin import PluginInputError
from cyreneAI.core.plugin.install_policy import (
    PluginInstallPolicy,
    compare_plugin_versions,
)
from cyreneAI.core.schema.plugin import (
    PluginDefinition,
    PluginIsolationMode,
    PluginManifest,
    PluginSignatureStatus,
    PluginSourceInfo,
    PluginSourceType,
)


def test_compare_plugin_versions_handles_numeric_segments() -> None:
    assert compare_plugin_versions("1.10.0", "1.2.0") > 0
    assert compare_plugin_versions("1.0.0", "1.0") == 0
    assert compare_plugin_versions("1.0.0", "2.0.0") < 0


def test_plugin_install_policy_rejects_duplicate_install() -> None:
    policy = PluginInstallPolicy()

    with pytest.raises(ConflictError, match="already installed"):
        policy.validate_install(
            manifest=_manifest(version="1.0.0"),
            source=_source(version="1.0.0", content_hash="hash-1"),
            installed_definitions=[_definition(version="1.0.0")],
            installed_sources=[_source(version="1.0.0", content_hash="hash-1")],
        )


def test_plugin_install_policy_rejects_mutable_same_version_install() -> None:
    policy = PluginInstallPolicy()

    with pytest.raises(ConflictError, match="different content_hash"):
        policy.validate_install(
            manifest=_manifest(version="1.0.0"),
            source=_source(version="1.0.0", content_hash="hash-2"),
            installed_definitions=[_definition(version="1.0.0")],
            installed_sources=[_source(version="1.0.0", content_hash="hash-1")],
        )


def test_plugin_install_policy_requires_reload_for_upgrade_install() -> None:
    policy = PluginInstallPolicy()

    with pytest.raises(ConflictError, match="use reload"):
        policy.validate_install(
            manifest=_manifest(version="1.1.0"),
            source=_source(version="1.1.0", content_hash="hash-2"),
            installed_definitions=[_definition(version="1.0.0")],
            installed_sources=[_source(version="1.0.0", content_hash="hash-1")],
        )


def test_plugin_install_policy_rejects_unsupported_isolation() -> None:
    policy = PluginInstallPolicy()

    with pytest.raises(PluginInputError, match="isolation mode subprocess"):
        policy.validate_install(
            manifest=_manifest(version="1.0.0"),
            source=_source(
                version="1.0.0",
                content_hash="hash-1",
                isolation_mode=PluginIsolationMode.SUBPROCESS,
            ),
            installed_definitions=[],
            installed_sources=[],
        )


def test_plugin_install_policy_can_require_signed_sources() -> None:
    policy = PluginInstallPolicy(allow_unsigned=False)

    with pytest.raises(PluginInputError, match="must be signed"):
        policy.validate_install(
            manifest=_manifest(version="1.0.0"),
            source=_source(version="1.0.0", content_hash="hash-1"),
            installed_definitions=[],
            installed_sources=[],
        )


def test_plugin_install_policy_rejects_reload_downgrade() -> None:
    policy = PluginInstallPolicy()

    with pytest.raises(ConflictError, match="downgrade rejected"):
        policy.validate_reload(
            plugin_id="demo.plugin",
            old_definition=_definition(version="1.1.0"),
            old_source=_source(version="1.1.0", content_hash="hash-2"),
            new_manifest=_manifest(version="1.0.0"),
            new_source=_source(version="1.0.0", content_hash="hash-1"),
        )


def test_plugin_install_policy_audits_reload_changes() -> None:
    policy = PluginInstallPolicy()

    audit = policy.validate_reload(
        plugin_id="demo.plugin",
        old_definition=_definition(version="1.0.0"),
        old_source=_source(version="1.0.0", content_hash="hash-1"),
        new_manifest=_manifest(version="1.1.0"),
        new_source=_source(
            version="1.1.0",
            content_hash="hash-2",
            signature_status=PluginSignatureStatus.VALID,
        ),
    )

    assert audit["previous_version"] == "1.0.0"
    assert audit["version"] == "1.1.0"
    assert audit["version_changed"] is True
    assert audit["previous_content_hash"] == "hash-1"
    assert audit["content_hash"] == "hash-2"
    assert audit["content_hash_changed"] is True
    assert audit["signature_status_changed"] is True


def _manifest(*, version: str) -> PluginManifest:
    return PluginManifest(
        plugin_id="demo.plugin",
        name="Demo",
        description="Demo plugin.",
        entrypoint="main.py",
        version=version,
    )


def _definition(*, version: str) -> PluginDefinition:
    return PluginDefinition(
        plugin_id="demo.plugin",
        name="Demo",
        description="Demo plugin.",
        version=version,
    )


def _source(
    *,
    version: str,
    content_hash: str,
    isolation_mode: PluginIsolationMode = PluginIsolationMode.IN_PROCESS,
    signature_status: PluginSignatureStatus = PluginSignatureStatus.UNSIGNED,
) -> PluginSourceInfo:
    return PluginSourceInfo(
        plugin_id="demo.plugin",
        source_type=PluginSourceType.FILESYSTEM,
        path="/plugins/demo",
        manifest_path="/plugins/demo/plugin.json",
        entrypoint="/plugins/demo/main.py",
        version=version,
        content_hash=content_hash,
        loaded_at=datetime.now(UTC),
        isolation_mode=isolation_mode,
        signature_status=signature_status,
    )
