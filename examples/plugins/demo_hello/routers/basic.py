from cyreneAI.api import CyreneRouter, Depends

router = CyreneRouter()


@router.command
def hello(name: str = "world"):
    return f"Hello, {name}!"


@router.command
def providers(list_providers=Depends("providers")):
    names = ", ".join(provider.name for provider in list_providers())
    return names or "No providers"


@router.command
async def asset(assets=Depends("assets")):
    content = await assets.read_text("prompts/hello.txt")
    return content.strip()
