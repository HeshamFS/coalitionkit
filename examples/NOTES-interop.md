# Interop run: where the protocol and our packages made a real framework's life hard

Found while building acceptance test 1 (`examples/interop/run.py`). Nothing in `packages/` was
changed. The one root change is `known-third-party = ["examples"]` in the root `pyproject.toml`
(ruff otherwise treats the new `examples/` folder as the first-party owner of the contracts
tests' helper module `examples.py`, and `tools/check.py` fails).

## Protocol

1. No "plan decided" or task-status notification. A member can only infer that a plan is decided
   by counting other deciders' `decide` events, which forces `decide` on a plan to be scoped
   `coalition` (every member sees every consent). The A2A edge has no read call (MCP has
   `my_view`).
2. Members cannot verify other members' originals. An envelope names its sender's card URL, but
   only the host pins that key; a member gets no peer keys. Members check schema only
   (counted as `peer_originals_unverified` in the scorecard).
3. The invitation is undefined. A non-member's replay of the charter is empty (audience
   `coalition` resolves to current members), so the charter must reach a joining member out of
   band; the run delivers the host-signed charter directly.
4. A charter without a role marked `required: true` never leaves Germinate (the runtime moves to
   Gather only when required roles are filled), and the spec has no message for "the organizer
   starts it". Read from the runtime code; the no-required-role case was not run.
5. A `commit` scoped `host` is acknowledged with the receipt only, so the member never sees the
   revision the host assigned; the member assumes 1, as the spec says for a new commitment.
6. Host to member delivery is specified in prose only. The edges package has just the member to
   host direction.

## Packages

1. `coalitionkit_edges`: no member server or host delivery client. Written here:
   `members/kit/server.py` (signed member card, bearer middleware, executor) and
   `interop/delivery.py`. The edge's bearer middleware and sender context builder are private,
   so the member server duplicates them. `RunningServer` (real sockets, one thread per app) is in
   `a2a/testing.py` because in-process ASGI hangs with a2a-sdk 1.3.0.
2. `HostPort` takes a card URL string; `CoalitionHost` wants `AuthenticatedSender(card_url,
   participant)`. Every embedder writes the same adapter (`interop/coalition.py::_EdgePort`).
3. `CoalitionHost.accept`, `host_emit` and `replay` are blocking; each call needs
   `asyncio.to_thread`.
4. A2A data parts are protobuf `Value`, so every number returns as a float; `wire.restore_ints`
   exists for this and the member side needed it too (it is applied inside `envelope_parts`).
5. Each delivery or send is a new A2A task in the Coalition's context, and the SDK's
   `InMemoryTaskStore` keeps all of them.
6. `coalitionkit_models.ModelGateway` returns text only: no tool calls, no reasoning-token
   count, no finish reason. The hosted member therefore speaks a JSON call protocol, and that is
   measurably less reliable than native tool calling (see the live history in the report).
   `RawCompletion` is not exported from the package root, which a scripted `Transport` needs.
   The default Meta base URL is wrong (known; the run passes `https://api.meta.ai/v1`).
7. The Gardener was not used: `generate_plans` returns non-dominated plans and has no way to
   require one task per member, so the run uses a ten-line planner (cheapest assignment giving
   each member exactly one task).
8. The Steward is the runtime's default fake, so C-12 (Steward before delivery) is not exercised.

## Frameworks on Python 3.15 (google-adk 2.13.0, langgraph 1.2.18)

1. `zstandard` (via langsmith via langchain-core) and `pyyaml` have no 3.15 wheels. The sdist
   build also fails here because the `vcvarsall.bat` call exceeds the Windows command-line
   limit with a long PATH. Workarounds: `override-dependencies = ["zstandard; python_version <
   '3.15'"]` in `examples/pyproject.toml`; PyYAML built pure Python with a short PATH and
   `PYYAML_FORCE_LIBYAML=0`.
2. `litellm` caps `python <3.15`, so ADK's `LiteLlm` hook is unavailable. ADK 2.13 ships
   `google.adk.integrations.openai.OpenAILlm`; reasoning effort goes through
   `OpenAIGenerateContentConfig(effort=...)`. Meta accepted `minimal`.
3. `langchain-openai` shares one cached async httpx client per process. It binds to the first
   event loop that used it, so a second run in the same process failed live with `Event loop is
   closed` (scorecard kept in `out/kept/`). Fix: pass an own `http_async_client` per model.
4. Both frameworks emit DeprecationWarnings on 3.15 (`asyncio.iscoroutinefunction` in langsmith,
   `_UnionGenericAlias` in google-genai). The root pytest config uses `filterwarnings = error`,
   so the examples have their own pytest config and are not part of the root test run.
5. ADK's own A2A layer was not tried; the member server is built on a2a-sdk directly because
   the extension header, signed card, bearer check and envelope data parts all need to be
   under our control. Whether ADK's A2A glue passes data parts through was not tested.
6. The repo's pyright config does not cover `examples/`; pyright was not run on it.
