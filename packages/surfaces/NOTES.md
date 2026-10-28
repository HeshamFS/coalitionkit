Notes for the lead (spec, runtime and contracts are unchanged).

- Runtime has no call that lists a decider's open consent requests. `open_requests` in
  `agent.py` reads the `consents` table through the public `EventStore.transaction` port. A
  `ConsentLedger.pending_for(decider)` method would replace that SQL.
- `host.view()` rebuilds state and files consent rows on every call, so each feed wake costs a
  full rebuild. Fine for v0.1 sizes; a cursor-based projection fold would remove it.
- The spec says the answer "resumes with a new run". The POST `/v1/agent/answers` is a plain
  JSON endpoint; the agent stream starts a new run on the next bus wake. AG-UI `resume` entries
  on a RunAgentInput POST are not wired.
- The spec says numbers are "bound to the event they came from" without a wire form. This
  package uses `{"value": n, "event_ref": "<event id>"}` (`bound_number`); any other number in a
  prop or data model is rejected.
- Catalog file `doors` means the props that hold other components' ids (`child`, `children`).
- Pinned: ag-ui-protocol 1.0.0, fastapi 0.162.0, jsonpatch 1.38 (pulls jsonpointer 3.6),
  uvicorn 0.54.0.
- Root `pyproject.toml` also gained `packages/surfaces/tests` on pytest `pythonpath` and
  pyright `extraPaths`, because the test helpers live in `surfaces_support.py` (a second
  `tests/__init__.py` collides with the runtime tests package).
