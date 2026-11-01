<!-- SPDX-License-Identifier: Apache-2.0 -->
# Scripted validation

Run in the dedicated Windows worktree with uv cache and TEMP/TMP inside .venv.
The default external cache and pytest temporary directory were not writable.

| Check | Result |
| --- | --- |
| pack validate packs/science-lab | Pass |
| pack eval packs/science-lab --json | Both scenarios pass; 15 messages each; zero canaries |
| pack accept packs/science-lab --json | All 20 assertions pass; 44 messages/refusals; zero canaries |
| pytest -q packs/science-lab/test_contract.py | 7 passed |
| tools/test_separation.py | 11 passed |
| git diff --quiet core-freeze-2 -- packages apps spec | Pass: frozen kit unchanged |
| git diff --check | Pass |
| python tools/check.py | Fails at repository pytest; see below |

The full check passed ruff, formatting, pyright (zero errors/warnings), all 19
import contracts and all 22 schema checks. Repository pytest finished with
1344 passed, 32 skipped, 1 failed and 2 errors in 801.08 seconds:

- acceptance/tests/test_ripple_server.py: the two-second surface latency assertion
  measured p95 2.808399 seconds.
- conformance/tests/test_scenarios.py::test_scripted_lifecycle: teardown failed
  because the server thread remained alive after its 15-second join.
- mcp_server/tests/test_view.py::test_my_view_carries_the_viewers_events_in_order_and_readable_text:
  setup encountered unclosed socket/Proactor transport warnings.

Those files are under packages/ and were not changed. The full command stops
before separation when pytest fails. A separate check_domain run found 27
existing kit occurrences of required denylist terms. Examples:

- packages/server/src/coalitionkit_server/genesis.py:183: labs, couriers
- packages/server/tests/test_genesis.py:41: labs, courier
- packages/mcp_server/src/coalitionkit_mcp/assets/surface-v1.html:47: temperature
- apps/web/package.json:31: instrument
- apps/web/src/gallery/sheets/Sheet10.tsx:131: lab

Other hits include model temperature parameters and font/dependency names.
The terms remain in the denylist; no kit edits or scan exceptions hide them.
This prevents claiming the full done gate. README documents the functional cuts,
including unbound views, limited eval scripting and the trusted Mint reading
fixture. Live variants are left to the integrator with keys and were not run.
