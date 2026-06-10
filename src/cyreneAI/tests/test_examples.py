from __future__ import annotations

import runpy
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
RAG_DEMO_PATH = PROJECT_ROOT / "examples" / "rag_demo.py"


def test_rag_demo_exists() -> None:
    assert RAG_DEMO_PATH.is_file()


def test_rag_demo_loads_without_running_main() -> None:
    namespace = runpy.run_path(str(RAG_DEMO_PATH), run_name="cyrene_rag_demo_test")

    assert callable(namespace["main"])
    assert callable(namespace["_required_env"])


def test_rag_demo_reports_missing_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    namespace = runpy.run_path(str(RAG_DEMO_PATH), run_name="cyrene_rag_demo_test")
    required_env = namespace["_required_env"]

    with pytest.raises(
        RuntimeError,
        match="Set OPENAI_COMPATIBLE_API_KEY or OPENAI_API_KEY before running this demo",
    ):
        required_env("OPENAI_COMPATIBLE_API_KEY", "OPENAI_API_KEY")
