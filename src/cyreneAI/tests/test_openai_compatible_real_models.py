# ----------------------------------------------------
# 此测试旨在测试能不能在真实情况跑通，不做强制要求
# ----------------------------------------------------
from __future__ import annotations

import asyncio
import os
from datetime import timedelta

import pytest
from dotenv import load_dotenv

from cyreneAI.core.errors.provider import ProviderError
from cyreneAI.core.provider.factory import ProviderFactory
from cyreneAI.core.provider.manager import ProviderManager
from cyreneAI.core.provider.registry import ProviderRegistry
from cyreneAI.core.schema.provider import ProviderConfig, ProviderType
from cyreneAI.infra.bootstrap.registrations.openai_compatible import (
    register_openai_compatible_provider,
)


def _skip(reason: str) -> None:
    print(f"openai-compatible real models skipped: {reason}")
    pytest.skip(reason)


async def _run_real_models() -> None:
    load_dotenv()

    api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL") or os.getenv("OPENAI_BASE_URL")

    if not api_key:
        _skip("OPENAI_COMPATIBLE_API_KEY or OPENAI_API_KEY is required")

    registry = ProviderRegistry()
    factory = ProviderFactory()
    register_openai_compatible_provider(registry, factory)

    manager = ProviderManager(factory)
    config = ProviderConfig(
        provider_id="real-openai-compatible-models",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        api_key=api_key,
        base_url=base_url,
        timeout=timedelta(seconds=30),
    )

    try:
        await manager.add(config)
        models = await manager.list_models(config.provider_id)
        if not models:
            _skip("configured endpoint returned no models")

        print()
        print("openai-compatible real models response:")
        print(f"  count: {len(models)}")
        print(f"  first_models: {[model.model_id for model in models[:5]]}")
    except ProviderError as exc:
        _skip(f"configured endpoint rejected model listing: {exc}")
    finally:
        await manager.close_all()


def test_openai_compatible_real_models() -> None:
    asyncio.run(_run_real_models())
