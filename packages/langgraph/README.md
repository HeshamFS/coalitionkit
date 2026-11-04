# coalitionkit-langgraph

Run a LangGraph graph as a seat in a CoalitionKit room. The graph pauses with an `interrupt` where a person must consent, and only their resumed answer is signed.

```python
from coalitionkit_langchain import take_seat
from coalitionkit_langgraph import GraphSeat, seat_graph

seat = await take_seat("http://127.0.0.1:8000", "ABC-DEFG", "Rami")
async with GraphSeat(seat) as held:
    graph = seat_graph(chat, held)
```

See the [LangGraph guide](https://github.com/HeshamFS/coalitionkit/blob/main/docs/guides/langgraph.md).

Part of [CoalitionKit](https://github.com/HeshamFS/coalitionkit).
