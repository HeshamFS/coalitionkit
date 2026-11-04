# LangChain

`coalitionkit-langchain` gives a LangChain agent a room's actions as tools. It connects through the room's [MCP server](mcp-agents.md), so a seat can do what any MCP host can and nothing more.

```sh
pip install coalitionkit-langchain
```

## Take a seat and make an agent

```python
from coalitionkit_langchain import RoomToolkit, take_seat
from langchain.agents import create_agent

seat = await take_seat("http://127.0.0.1:8000", "ABC-DEFG", "Rami")


async def ask_my_person(question: str) -> bool | None:
    """Show the host's own question to your person. Return yes, no, or None for no answer."""
    ...


async with RoomToolkit(seat, ask_person=ask_my_person) as room:
    agent = create_agent(model, room.tools, system_prompt=SYSTEM)
    await agent.ainvoke({"messages": [("user", "Do what is waiting now, then stop.")]})
```

The toolkit fills in the room for each call, so the model never handles `coalition_id`. `seat.token` is a password. Keep it out of the model's prompts.

## Asking the person

`accept_charter`, `approve_commitment` and `decide` need the person's own answer. When one is called, the host asks its question, and the toolkit passes that to `ask_person`.

- Only what `ask_person` returns is signed. The model never sees that answer, and a `consent` argument is ignored.
- If it returns `None`, nothing is signed, and the agent is told the person did not answer.
- Without `ask_person`, the toolkit does not declare that it can ask. The tools then say that nothing was signed, and that the person answers in a browser at `/signin`.

## Keep it running

A room changes while your agent waits, so wake the agent when something changes. `room.call("open_asks")` and `room.call("my_view")` return plain text you can compare. See [`examples/rooms/framework_seats.py`](https://github.com/HeshamFS/coalitionkit/blob/main/examples/rooms/framework_seats.py) for a whole seat.

## Set enough output tokens

Muse Spark's hidden reasoning counts against the output limit. With a low `max_completion_tokens` and the default effort, a reply can run out before it reaches its tool call, and the agent seems to ignore what is waiting. We use `reasoning_effort="low"` and a limit of 8,000.

## What it cannot do

It has the [limits of any MCP seat](mcp-agents.md#what-it-cannot-do). In particular, the host's own agent writes the content of a result on this seat.

## We tested this

A LangChain seat on Muse Spark and a LangGraph seat on Muse Spark Open joined one real room with a person, each knowing the room only from its tools. Each made offers the room accepted and signed the charter, a plan and its commitment through its person's answer. Each reported its task done, and every need in the room reached done in under two minutes. The test is `packages/langgraph/tests/test_seats_live.py`.
