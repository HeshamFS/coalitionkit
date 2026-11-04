# Google ADK and LangGraph members

The repository has example member agents on Google ADK and on LangGraph, and a run that puts them with a hosted agent in one Coalition over A2A.

- [`examples/members/adk_member`](https://github.com/HeshamFS/coalitionkit/tree/main/examples/members/adk_member): an `LlmAgent` with three function tools.
- [`examples/members/langgraph_member`](https://github.com/HeshamFS/coalitionkit/tree/main/examples/members/langgraph_member): a two-node graph of model and tools.
- [`examples/members/kit`](https://github.com/HeshamFS/coalitionkit/tree/main/examples/members/kit): what they share, such as identity, signing, and answering from a local vault.

## Run them

```sh
uv --directory examples run python -m interop.run --scripted
COALITIONKIT_META_API_KEY=... uv --directory examples run python -m interop.run --live
```

`--scripted` needs no key. It prints a scorecard as JSON: goal, validity, refusals, latency, tokens and cost.

!!! note "What this run is"
    This is a small organizer written for the example, driving three neutral tasks over A2A. It does not use the room engine. To put an agent in a real room, follow [Connect an agent over A2A](a2a-business-agent.md).
