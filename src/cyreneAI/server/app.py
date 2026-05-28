from __future__ import annotations

from fastapi import FastAPI

from cyreneAI.application.runtime import CyreneAIRuntime
from cyreneAI.server.config import ServerSettings, build_server_settings_from_env
from cyreneAI.server.routes import auth, channels, chat, health, images, providers
from cyreneAI.server.routes import telegram


def create_app(
    runtime: CyreneAIRuntime,
    settings: ServerSettings | None = None,
    telegram_webhook_secret: str | None = None,
    telegram_provider_id: str | None = None,
    telegram_model: str | None = None,
) -> FastAPI:
    app = FastAPI(title="CyreneBot API")
    app.state.runtime = runtime
    app.state.server_settings = settings or build_server_settings_from_env()
    app.state.telegram_webhook_secret = telegram_webhook_secret
    app.state.telegram_provider_id = telegram_provider_id
    app.state.telegram_model = telegram_model

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(providers.router)
    app.include_router(chat.router)
    app.include_router(images.router)
    app.include_router(channels.router)
    app.include_router(telegram.router)
    return app
