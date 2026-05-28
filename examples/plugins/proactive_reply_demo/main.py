from cyreneAI.plugin_api import CyreneBot

from proactive_routes.proactive import router as proactive_router


plugin = CyreneBot()
plugin.include_router(proactive_router)
