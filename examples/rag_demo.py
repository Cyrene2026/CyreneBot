from __future__ import annotations

import asyncio
import os
from datetime import timedelta
from pathlib import Path

from cyreneAI.adapters.documents import FileSystemDocumentLoader
from cyreneAI.adapters.vector_stores import create_memory_vector_store
from cyreneAI.application.chat.rag_orchestrator import RAGChatOrchestrator
from cyreneAI.application.knowledge.indexing_orchestrator import IndexingOrchestrator
from cyreneAI.bootstrap import build_cyrene_ai_runtime
from cyreneAI.core.schema.application import (
    ApplicationIndexingRequest,
    ApplicationRAGChatRequest,
    ChunkStrategy,
    RAGContextFormat,
)
from cyreneAI.core.schema.message import (
    ContentPart,
    ContentPartType,
    Message,
    MessageRole,
)
from cyreneAI.core.schema.provider import ProviderConfig, ProviderType

DOCUMENT_PATH = Path("docs")
PROVIDER_ID = "openai-compatible"


async def main() -> None:
    api_key = _required_env("OPENAI_COMPATIBLE_API_KEY", "OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    chat_model = _required_env("OPENAI_COMPATIBLE_MODEL", "OPENAI_MODEL")
    embedding_model = _required_env(
        "OPENAI_COMPATIBLE_EMBEDDING_MODEL",
        "OPENAI_EMBEDDING_MODEL",
    )

    runtime = await build_cyrene_ai_runtime(
        provider_configs=[
            ProviderConfig(
                provider_id=PROVIDER_ID,
                provider_type=ProviderType.OPENAI_COMPATIBLE,
                api_key=api_key,
                base_url=base_url,
                timeout=timedelta(seconds=30),
            )
        ],
        vector_store=create_memory_vector_store(),
    )

    try:
        documents = FileSystemDocumentLoader(DOCUMENT_PATH).load()
        if not documents:
            raise RuntimeError(
                "Add at least one non-empty .md or .txt file under docs/."
            )

        await IndexingOrchestrator(runtime).index(
            ApplicationIndexingRequest(
                provider_id=PROVIDER_ID,
                model=embedding_model,
                documents=documents,
                chunk_size=500,
                chunk_strategy=ChunkStrategy.PARAGRAPH,
                collection_id="docs",
                metadata={"purpose": "readme-rag"},
            )
        )

        result = await RAGChatOrchestrator(runtime).chat(
            ApplicationRAGChatRequest(
                session_id="readme-session",
                provider_id=PROVIDER_ID,
                model=chat_model,
                retrieval_provider_id=PROVIDER_ID,
                retrieval_model=embedding_model,
                messages=[
                    Message(
                        role=MessageRole.USER,
                        content=[
                            ContentPart(
                                type=ContentPartType.TEXT,
                                text="Where should provider SDK calls live?",
                            )
                        ],
                    )
                ],
                retrieval_top_k=3,
                collection_id="docs",
                retrieval_context_format=RAGContextFormat.SOURCE_TAGGED,
                include_retrieval_metadata=True,
                temperature=0,
                max_tokens=128,
            )
        )

        message = result.chat_result.response.message
        if message is not None and message.content:
            print(message.content[0].text or "")
    finally:
        await runtime.close()


def _required_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    joined_names = " or ".join(names)
    raise RuntimeError(f"Set {joined_names} before running this demo.")


if __name__ == "__main__":
    asyncio.run(main())
