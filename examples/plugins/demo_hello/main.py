from routers.basic import router as basic_router

from cyreneAI.api import CyreneBot

plugin = CyreneBot()
plugin.include_router(basic_router)
