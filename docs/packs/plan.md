# Discipline Packs: plan

Status: in progress · 2026-11-01 · owner Hesham Salama
Follows `docs/ux/journey.md` (the zero-pack journey). Spec: `spec/coalition-protocol-v0.1.md`, section "Discipline Pack format".

## 1. Goal

Three Discipline Packs that work end to end, from a typed goal to Dissolve, each in its own words, each a standalone folder wired on top of the kit:

| Pack | What it coordinates |
|---|---|
| `science-lab` | Samples and instrument runs across labs, a courier, an old instrument brought in by the Mint |
| `daily-life` | A household or family coordinating visits, errands and care, with absent members answered for by their agents |
| `travel-disruption` | Stranded travellers, car desks and hotel shuttles, businesses joining over A2A |

## 2. The rules this plan keeps

1. **Nothing from a pack enters the kit.** No pack name, word, schema, policy, view or data under `packages/`, `apps/` or `spec/`. The kit only knows the generic pack format.
2. **The kit never imports a pack.** Packs are loaded at run time from a folder.
3. **Packs never change the kit.** After the `core-freeze-2` tag, a pack branch that touches `packages/`, `apps/` or `spec/` fails CI. This is G3's "empty core diff", with the baseline moved from the G1 commit to `core-freeze-2` (decision 4 below).
4. **Gates open by result, never by date.** Each phase starts when the one before passes.
5. **Every lane is tested live.** Every pack eval has a live variant with `COALITIONKIT_META_API_KEY`; cost and latency are reported. Skipped live tests are reported as not run.
6. **Real people only, measured numbers only, claimed only when proven** (journey section 2).
7. **Work split.** Claude writes plans and briefs, judges every slice it did not write, runs the checks and walks the result in Chrome. Codex builds through the duo bridge, one worktree per slice. Sonnet subagents build web slices and packs. Judge is never the author. At most three heavy jobs at once (memory).

## 3. Decisions taken (2026-11-01)

1. All three packs.
2. Packs live in `packs/<name>/` in this repository, outside `packages/`, kept apart by the checks in section 7.
3. A pack may suggest itself from the typed goal through a new optional `pack.yaml` field (spec change first, slice A0).
4. G3 measures the empty core diff from `core-freeze-2`.

## 4. Phase 0 · finish the zero-pack journey

On `feat/ux-journey`. Gate: J-01 to J-14 walk in Chrome; checks pass; PR merged to `main`.

| # | Slice | Owner |
|---|---|---|
| 0.1 | Plan options in words, not objective keys; one choice shown as one tension card, not three asks; every deadline with its day; vendor count from agent cards | Sonnet |
| 0.2 | One stream per tab: agent lines and open requests travel on the feed stream, so three tabs no longer exhaust Chrome's six connections | Codex |
| 0.3 | Walk the rest in Chrome: choose a plan, commit, ripple, dissolve, glasses; fix what breaks | Claude |
| 0.4 | Codex reviews the Phase 0 diff; PR to `main`; merge; branch and worktrees removed | Claude |

## 5. Phase A · plug points in the kit (generic only)

Branch `feat/pack-host` from `main`. Gate: every slice reviewed and merged; `tools/check.py` passes; a fixture pack (`packages/packs/tests/fixtures/pack-alpha`, already neutral) runs end to end through every plug point in a test; Codex review of the whole diff clean. Then merge to `main` and tag `core-freeze-2`.

| # | Slice | What the kit gains | Owner |
|---|---|---|---|
| A0 | Spec | Optional `pack.yaml` key `suggest: {keywords: [..], examples: [..]}` for Genesis; protocol text on how a charter's `pack` binds a pack to a Coalition and what each key changes at run time | Claude |
| A1 | Install and Genesis | `Settings.packs` (folders) and `coalitionkit up --pack <folder>` (repeatable); each pack loaded with the loader and refused with its report if broken; `GET /v1/packs` (name, version, label, roles, vocabulary, suggest; no files); `/v1/genesis/draft` suggests a pack from `suggest` and returns its roles; `/v1/genesis/start` writes `charter.pack` and the pack's roles | Codex |
| A2 | Run time | When a charter names a pack: its roles' abilities are enforced; its schema extensions validate needs, offers, tasks and resources on top of the core schemas; its `strategy` resolves by name to one of the Gardener's built-in strategies (`auction`, `match`, `vote`) with the fairness keys each accepts, any other name refused at install, and the spec lists the supported names and keys; its task templates seed the Gardener's first needs; its skills are offered to agents at join (MCP resource) and its lessons are written at Dissolve (`skills_written`). Policies come from A7 | Codex |
| A3 | Surfaces | Feed state key `pack: {name, version, vocabulary, views}` for the viewer; the composer orders components per role and device from the pack's views (catalog components only) | Codex |
| A4 | Evals | `coalitionkit pack eval <folder> [--live]`: each scripted scenario runs against a real in-process host with scripted participants and their vaults; checks the expected decision, `canaries_leaked: 0` across every viewer's projection, the log and the Steward, and `max_messages`; reports tokens, latency and cost when live | Codex |
| A5 | Web | `useVocabulary` so every screen (Genesis cards, room, moments, consent sheet) shows the pack's words for core objects; Genesis pack chip lists installed packs, preselects the suggested one, and switching re-germinates the cards; views decide component order per role | Sonnet |
| A6 | Separation guards | Domain-word scan extended to `apps/` and `spec/`; import rule: nothing under `packages/` or `apps/` imports from `packs/`; CI job `core-freeze` failing when a pack branch changes `packages/`, `apps/` or `spec/` since `core-freeze-2` (pack PRs may change only `packs/`, `docs/` and the denylist), with a regression test proving that a neutral web change on a pack branch is refused; `tools/check.py` runs `pack validate` and the scripted evals for every folder in `packs/` | Claude |
| A7 | Policy contract and loader hardening | Spec and loader agree: pack policies may use exactly allow, redact, block and escalate (the loader today wrongly forbids `block`, `loader.py` `FORBIDDEN_PACK_ACTIONS`); the host carries a typed outcome with the policy id for each, after every core check (block → `pack_violation`, escalate → a person is asked, redact → paths added to `scope.redact` before storing); schema `$ref`s resolve only through a closed registry of the pack's own snapshot and the approved core schemas, refusing `file:`, network and escaping references (negative tests first) | Codex |
| A8 | Mint templates and connectors | A bound pack's Mint templates join the Mint pipeline for that Coalition only (each with its own tests, run before a minted agent is enrolled); connectors are declared by the pack and run by the operator out of process (`coalitionkit pack connectors <folder>` prints what to start); a connector joins like any business agent, through an invitation and a verified signed card, and a refused card shows its reason. Both proven with fixture packs before the freeze | Codex |
| A9 | Schema-driven input | A generic, viewer-scoped contract: a bound pack's extension fields for needs and offers render as inputs built from catalog form components (sheet 04) in the viewer's own My part; values meant for the vault go only through the existing private vault channel; required extension fields tested end to end | Sonnet |

**Live lanes before the freeze.** Every lane that calls a model has a live test that must pass, with the key, before `core-freeze-2`; a skip leaves the gate open. The lanes: Genesis drafting, the hosted member brain, the Gardener's planning, the Steward's model audit, the Mint. Each reports calls, tokens, latency and cost.

Slices run in parallel where their files are disjoint: A1, A4 and A7 first (server and cli; packs eval module; loader and host policy path), then A2, A3 and A8, then A5 and A9 against A1's API and A3's state key. At most three at once.

## 6. Phase B · the three packs

Branches `pack/<name>` from `main` after `core-freeze-2`. They run in parallel (one Codex, two Sonnet). Each pack folder holds:

| Item | Content |
|---|---|
| `pack.yaml` | name, version, `core` range, roles with abilities and labels, `suggest`, references to the files below, strategy, evals |
| `vocabulary.yaml` | Words for task, resource, need, offer and the seats |
| `schemas/` | Extensions of need, offer, task and resource |
| `policies/` | At least two deterministic Steward policies, one of which a demo run triggers |
| `views.yaml` | Component order per role and device, catalog components only |
| `templates.yaml` | Task templates the Gardener drafts first |
| `skills/` | SKILL.md files for agents that join, and the lesson templates written at Dissolve |
| `mint/` (science) | A Mint template for an instrument's display, with its tests |
| `connectors/` (travel) | A business agent (A2A, signed card) run out of process |
| `evals/` | At least two scripted scenarios with planted vault canaries, plus a live variant |
| `README.md` | What the pack is for, how to run it, what it never does |

| Pack | Roles | Policies (examples) | Strategy | Evals |
|---|---|---|---|---|
| `science-lab` | lab lead, technician, courier, instrument | hazardous shipments escalate to a person; no dosing or clinical advice (block) | `match` (runs to free instrument time) with a fair-share cap across labs | three labs anneal and image samples by Friday; an instrument reading changes the plan |
| `daily-life` | family member, helper, absent member | no medical or other regulated advice (escalate); no contact details shared before consent | fair share of errands and visits | bringing someone home on a set day with an absent member answered by their agent; a weekly rota |
| `travel-disruption` | traveller, organizer, car desk, shuttle | no contact details before both say yes; spending above a set amount needs a person's yes | group by destination, trade arrival time against cost | a group stranded overnight going to three cities; a new flight appears and only touched rides re-plan |

Owners: `science-lab` Codex, `daily-life` Sonnet, `travel-disruption` Sonnet. Claude judges each.

## 7. Separation checks (run in CI and in `tools/check.py`)

1. Domain words: no word from `tools/discipline-denylist.txt` under `packages/`, `apps/` or `spec/` (extended in A6). Packs add their own domain words to the denylist so the scan covers them.
2. Imports: an import-linter contract forbids any import of `packs` from the kit.
3. Freeze: `git diff --quiet core-freeze-2 -- packages apps spec` on pack branches.
4. Packs: `coalitionkit pack validate` and the scripted evals for every folder in `packs/`.

## 8. Phase C · each pack walked

**Executable acceptance per pack.** Besides its eval scenarios, each pack has one acceptance scenario that runs the whole journey against a real host with the pack bound: Genesis with the pack; offers and vault answers; the Gardener's plans under the pack's strategy (allocation and fairness asserted); an owner-signed commitment (an agent-only yes refused); the pack's distinguishing integration (science: a minted instrument's reading changes the plan; daily-life: an absent member's agent answers and the commitment waits for that member; travel: a business agent joins by signed card and holds a resource); a change that re-plans only touched tasks (affected and untouched asserted); a policy outcome; Dissolve with lessons scoped no wider than their sources. Scripted in CI, live with the key.

Gate per pack, all in Chrome on a local host started with `--pack packs/<name>`:

1. Type a goal; Genesis suggests the pack; the cards show its seats and words.
2. The room, Theatre, Plans, Ripple, Chain and the consent sheet speak the pack's words.
3. One of the pack's policies blocks something; Theatre shows it with the policy name.
4. Dissolve writes the pack's lessons.
5. Its evals pass scripted, and live with the key (cost reported).
6. The freeze check shows an empty kit diff since `core-freeze-2`.

When all three pass: G3.

## 9. Risks

| Risk | Answer |
|---|---|
| A pack needs a kit change after the freeze | It waits for the next kit release; the pack is cut down, the kit is not reopened for one pack |
| Live runs cost more than planned | Evals run scripted in CI; live runs are counted and reported per pack |
| Memory on this machine | At most three heavy jobs at once; long checks run alone |
| Domain words leak into the kit through copy | The extended scan and the freeze check fail the build |
