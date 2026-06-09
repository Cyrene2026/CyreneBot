from proactive_routes.proactive import router as proactive_router

from cyreneAI.api import CyreneBot

plugin = CyreneBot()
plugin.include_router(proactive_router)
