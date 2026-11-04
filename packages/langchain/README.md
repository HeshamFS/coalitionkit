# coalitionkit-langchain

A CoalitionKit room's actions as LangChain tools, over the room's own MCP server.

```python
from coalitionkit_langchain import RoomToolkit, take_seat

seat = await take_seat("http://127.0.0.1:8000", "ABC-DEFG", "Rami")
async with RoomToolkit(seat, ask_person=my_person) as room:
    agent = create_agent(model, room.tools)
```

`ask_person` shows the host's own question to the person and returns their answer. The model never sees it and cannot supply one.

See the [LangChain guide](https://github.com/HeshamFS/coalitionkit/blob/main/docs/guides/langchain.md).

Part of [CoalitionKit](https://github.com/HeshamFS/coalitionkit).
