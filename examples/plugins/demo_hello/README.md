# Demo Hello Plugin

Minimal CyreneBot plugin project.

```text
demo_hello/
  plugin.json
  main.py
  routers/
  assets/
```

`plugin.json` declares the plugin project metadata. `main.py` declares local bot routes.

```python
from cyreneAI.api import CyreneBot
from routers.basic import router as basic_router

plugin = CyreneBot()
plugin.include_router(basic_router)
```

Routers hold commands:

```python
from cyreneAI.api import CyreneRouter

router = CyreneRouter()

@router.command("/hello", aliases=["hi"])
async def hello(name="world"):
    """Say hello."""
    return f"Hello, {name}!"
```

Command handlers can return plain text. The host turns `return "..."` into a
standard bot text reply.

Required arguments without annotations are parsed as text:

```python
@router.command("/hello")
async def hello(name):
    return f"Hello, {name}!"
```

Simple command arguments can be declared with Python type annotations. Supported
types are `str`, `int`, `float`, and `bool`.

```python
@router.command("/repeat")
async def repeat(word: str, count: int = 1, excited: bool = False):
    suffix = "!" if excited else "."
    return " ".join([word] * count) + suffix
```

If an argument has no annotation, the default value is used to infer the type:

```python
@router.command("/repeat")
async def repeat(word="hi", count=1, excited=False):
    suffix = "!" if excited else "."
    return " ".join([word] * count) + suffix
```

The command signature is also used to generate usage and command metadata. For
the `repeat` command above, the route exposes:

```text
/repeat [word=hi] [count:int=1] [excited:bool=false]
```

and stores an `arguments` list in command metadata for management APIs and tests.

Handlers can also yield multiple replies:

```python
@router.command("/story")
async def story(request, ctx):
    yield "Once."
    yield "Then."
```

Complex plugins can split routes with prefixes:

```python
from cyreneAI.api import CyreneRouter, Depends

admin_router = CyreneRouter(prefix="/sf", admin_required=True)

@admin_router.command("/ban", aliases=["b"])
async def ban(request, store=Depends("storage")):
    ...
```

Handlers can declare host-managed dependencies when they need runtime abilities:

```python
from cyreneAI.api import CyreneBot, Depends, text

plugin = CyreneBot()

@plugin.command("/providers")
async def providers(request, list_providers=Depends("providers")):
    """List providers."""
    provider_names = ", ".join(provider.name for provider in list_providers())
    return text(request, provider_names or "No providers")
```

Dependencies are permission checked by the host. For example, `Depends("providers")`
requires the plugin manifest to declare `provider_read`.

Plugin assets are read-only files packaged with the plugin project:

```python
@plugin.command("/asset")
async def asset(request, assets=Depends("assets")):
    content = await assets.read_text("prompts/hello.txt")
    return text(request, content.strip())
```

`Depends("assets")` requires the plugin manifest to declare `assets`.

LLM access is exposed as `Depends("llm")`:

```python
from cyreneAI.api import Depends

@router.command("/ask")
async def ask(request, llm=Depends("llm")):
    return await llm.chat(request.command.args_text)
```

Local plugin tests can run without starting the server:

```python
from cyreneAI.api import PluginTestClient


async def test_hello_command():
    client = PluginTestClient(plugin)

    result = await client.command("/hello Cyrene")

    assert result.texts == ["Hello, Cyrene!"]
```

The same test client can dispatch events and run declared tasks:

```python
result = await client.event("message", text="hello", session_id="s1")
task_result = await client.task("cleanup", payload={"target": "cache"})
```
