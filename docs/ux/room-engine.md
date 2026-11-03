# The room engine and The Table

Approved by the owner on 2026-11-03. Today a real room stalls after the first need: agents act only in the demo script, and the model composes nothing inside the room. This document is the contract for fixing that. The engine makes real work happen in any web room, with or without a pack. The Table is the one living screen that shows it. `docs/ux/room-stories.md` holds the stories it must satisfy.

Reference walk (scripted, nothing runs): the canvas "Inside the Room", https://claude.ai/artifact/UcnurCU3vhoUKuvzgaSKgb.

## Rules that do not bend

- Agents never commit anyone. A plan, a commitment and the charter need that person's own signed yes. A helper's own owner key signs only the helper's own charter acceptance and its own commitments.
- Plans come from fixed rules (`plan_for`). The model explains plans and never builds them.
- The model picks only catalog components. Every tree passes `validate_surface` on the host, and numbers carry `{value, event_ref}` pointing at a real event. An invalid tree is retried once with the errors, then replaced by a fixed tree built by code. No HTML in props.
- Vault values never enter the log, a projection, Steward input or anything another viewer can read. Private text reaches only its own viewer.
- The model never invents facts. A statement that is not from the goal, an answer or an event is labelled as a suggestion, with `provenance: "estimate"`.
- Every model step has a rule-based fallback, so a room works without a key or when a call fails. Each output records `source: "model" | "rules"`, and the screen shows it.
- Goals, answers and Say text are data. Prompts say so and never let them change instructions.
- No scenario words or sample data under `packages/`. All prompts are domain-agnostic.

## The flow

| Moment | Who acts | Real events | Model step |
|---|---|---|---|
| Arrive | Person holds to sign | `join`, `decide(charter)` | none |
| Needs | Gardener | `need` for each | `gardener`: goal to 2-6 needs, each with a title, a kind, and a shared list of up to 6 time slots |
| Begin | Owner, or automatic when every seat is signed | `charter` revision only if seats change; helpers `join`, `decide(charter)` | none |
| Brief | Each seat's agent asks its person | none (answers go to the vault) | `hosted_agent`: 1-3 questions from closed kinds |
| Offer | Each seat's agent | `offer` per need, scope coalition | `hosted_agent`: which needs, at what cost, checked against the vault |
| Compare | Vaults | `query`, `answer`, `match` rounds | none |
| Plans | Gardener | `propose`, `tension` | `gardener`: public name and one line per plan; `hosted_agent`: private "for you" line per seat |
| Decide | People | `decide` | none |
| Commit | Agent asks, person signs | `commit`, `decide(commitment)`, `decide(task)` | none |
| Make | Assignee's agent | `observe` (source `document`) holding the result, then `done` for helpers | `composer`: an A2UI tree per task |
| My part | Person | `done` with evidence | none |
| Say | Anyone | private note, or `observe` (chat), or `ripple` | `hosted_agent`: route the sentence |
| Change | Agents, then asked people | `ripple`, new `offer`, `propose`, `tension` limited to who is affected | as above, only for the tasks it touches |
| Finish | Owner, or the deadline | `dissolve` | none |

## Seats and helpers

The charter names seats p1..pN and all of them are deciders. The opener would otherwise wait forever for empty seats, so the owner can begin.

- `POST /v1/room/begin {"helpers": bool}`, owner only. If open seats remain, the host stops the door and emits a charter revision with `deciders` set to the people seated. The owner's click counts as accepting that revision; other seated people get the normal ask. With `helpers: true`, the host adds one helper per open seat (at most one per need) after the revision.
- If every seat is signed, begin happens by itself, with no revision.
- A helper is a hosted member with its own keys. Its card and every label say it is an agent. It joins with `surfaces: []` and accepts the charter with its own owner key. It is never a decider, so it cannot approve a plan, and it never answers for a person.
- A helper's specialty is the need kind it serves, for example "Budget helper". Helpers have no calendar and take no part in match rounds.

## Results

A result is a `coalition.observe` with `source: "document"`, scope coalition, sent by the assignee's agent, so it is signed, reviewed by the Steward and in the chain like every other event. `content` is JSON:

```json
{"result": 1, "need_id": "<task>", "kind": "budget", "title": "Shared budget",
 "source": "model", "sources": ["<event id>"], "components": [], "data": {}}
```

Kinds: `place`, `schedule`, `budget`, `list`, `draft`. `coalition.done.evidence` is `[{"kind": "result", "ref": "<observe event id>", "verified_by": "<assignee>"}]`.

A helper reports `done` once its result is accepted. A person's agent makes the draft and the person presses Done, so `done` is never reported without their click.

A change to a task that is already `done` cannot ripple, because `done` is terminal. The host publishes a successor need instead, and the older result is marked replaced in room state.

## HTTP

All routes use the viewer bearer token, and all live behind `Dispatch` with the `agent` surface. They act only for the authenticated viewer.

| Route | Body | Answer |
|---|---|---|
| `POST /v1/room/begin` | `{helpers}` | `{phase}`; 403 unless owner |
| `POST /v1/room/brief` | `{question_id, value}` or `{question_id, skip: true}` | `{status}`; the value is checked against that question's closed shape; 422 otherwise |
| `POST /v1/room/say` | `{text}`, up to 500 characters | `{route, reply, event_id?, stopped?}` |
| `POST /v1/room/done` | `{task_id}` | `{seq}`; 409 unless the viewer's approved commitment has a result |

Consents still go through `POST /v1/agent/answers`. A tree can never answer a consent.

## What the feed adds

`state.stage` and `state.cost_meter` become host values, and `derive.ts` already prefers them. A new key `state.room` is built per viewer. Only `mine` is private.

```ts
type Room = {
  phase: "gather" | "brief" | "work" | "decide" | "commit" | "make" | "live" | "ended";
  // Light means it is your turn. Night while agents work and nothing waits on this viewer.
  lights: "day" | "night";
  goal: string;
  // The charter deadline as an ISO time: when the room ends by itself.
  closes: string;
  seats: {
    seat: string; role: string; label: string;
    kind: "person" | "helper" | "open"; you: boolean;
    signed: boolean; state: string;
  }[];
  needs: {
    id: string; title: string; kind: "place" | "schedule" | "budget" | "list" | "draft";
    detail: string; status: string; offers: number;
    assignee: string | null; result: string | null; source: "model" | "rules";
  }[];
  activity: {
    id: string; at: string; seat: string | null;
    verb: "reading" | "asking" | "offering" | "comparing" | "stopped" | "planning"
        | "explaining" | "committing" | "making" | "saying" | "changing" | "ending";
    need: string | null; label: string;
    state: "running" | "done" | "failed"; ms: number | null;
    source: "model" | "rules" | "host"; event: string | null;
  }[];
  slots: { id: string; label: string }[];
  common: { slots: string[]; count_private: number | null; compared: number } | null;
  plan_notes: Record<string, { name: string; line: string; source: "model" | "rules" }>;
  results: {
    id: string; need_id: string; kind: string; title: string;
    by: string; seq: number; source: "model" | "rules"; sources: string[];
    seqs: number[]; tree: unknown[]; data: unknown; messages: unknown[];
    replaced_by: string | null;
  }[];
  stops: {
    id: string; at: string; seat: string | null; to: string | null;
    policy: string; explain: string;
  }[];
  checked: number;
  change: {
    from: string | null; text: string; moved: string[]; asked: string[]; untouched: number;
  } | null;
  begin: { can: boolean; open_seats: number } | null;
  mine: {
    brief: {
      id: string; ask: string; why: string; component: string;
      messages: unknown[]; status: "open" | "answered" | "skipped";
    }[];
    feed: { at: string; text: string }[];
    for_you: Record<string, string>;
    tasks: {
      task_id: string; title: string; status: string;
      result: string | null; can_mark_done: boolean;
    }[];
  };
};
```

What the fields mean:

- `results[].id` is the id of the `observe` event, and `needs[].result` and `mine.tasks[].result` hold that id. `by` is a seat id. `seqs` holds the log positions of those `sources` this viewer may see, so it can be shorter than `sources`.
- `plan_notes` and `mine.for_you` are keyed by plan id.
- `stops[].to` is the seat a stopped message was aimed at, or `null` when it was aimed at the room.
- `change.from` is the seat that caused the change, or `null` when the host did.
- `checked` counts the events the Steward has reviewed in this room, including the ones it stopped.
- `state.cost_meter` is `{spent, currency, calls}`, measured from real model calls.

`results[].data` has one shape per kind, so the screen can offer real exports:

| Kind | `data` | Export |
|---|---|---|
| `place` | `{options: [{name, why, provenance}], chosen: name or null}` | none |
| `schedule` | `{items: [{title, start, end, where}]}`, with ISO 8601 times | ICS |
| `budget` | `{currency, rows: [{label, amount, provenance}], total}` | CSV |
| `list` | `{items: [{label, who, provenance}]}` | CSV |
| `draft` | `{subject, body}` | text |

A brief question's tree keeps its input at the data path `/answer`, and its Send button carries the action `room.brief` with `{question_id, value}`. The screen posts that context to `/v1/room/brief`. The value is a plain option id for `choice`, a list of slot ids for `slots`, a number for `amount` and a string for `text`. A number in a data model may be wrapped as `{value, event_ref}`, so both sides unwrap it: the screen before it posts, and the host before it checks the shape.

The hub takes a `room_state(viewer)` callable and a version counter. `_poll` sends a delta when the version changed, so steps reach the screen within half a second without a log event.

## Server layout

`packages/server/src/coalitionkit_server/room/`, each file under 500 lines:

| File | Holds |
|---|---|
| `engine.py` | `RoomEngine`: one per server, a level-triggered `step(coalition)` called from `GardenerLoop.step`, idempotent, resumes after restart. Durable public doc in table `room_engine`; private seat data in the hosted vault under reserved `_room*` keys, so dissolve erases it |
| `model.py` | `ask()`: one wrapper for gateway calls with timeout, strict schema, fallback, activity entries and measured cost |
| `needs.py` | Goal to needs and slots |
| `seats.py` | Begin, helpers |
| `brief.py` | Questions, composed through `compose_surface`; answer checks |
| `offers.py` | Seat agents make offers within vault limits |
| `compare.py` | Queries, answers and blinded match rounds with `coalitionkit_vault.psi` |
| `explain.py` | Plan names and "for you" lines |
| `work.py` | Commit requests, helper approvals, makers, `done` |
| `say.py` | Route the sentence; ripple, successor needs |
| `view.py` | `room_state(viewer)` |
| `routes.py` | The HTTP table above |

`Settings.room_engine: "on" | "off"`, default `off` so harnesses that drive a coalition themselves are unchanged. `coalitionkit up` sets it to `on`. A pack room keeps its pack's needs and offer forms and still gets the engine.

`GardenerLoop.step` keeps seeding and proposing, but when the engine is on it asks `engine.may_plan(coalition)` first, so a plan never appears before the offers and compare rounds finish.

## The Table

`apps/web/src/table/` replaces the five tabs whenever `state.room` is present. `RoomView` stays for rooms without it.

- One screen: the blue band with the serif goal; a dotted sheet with the seat ring and needs; your side to the right, or first on a phone; a rail of moments and the Say box at the bottom.
- Light is the default. Night comes only from `room.lights` and fades over 1.2 seconds.
- The ring opens from the landing's seat mark, and seats reuse its colours and marks.
- Beams, sparks and waves animate real activity entries and events, never a timer pretending work is happening. Reduced motion turns them off.
- Results render through `A2uiSurface` from `messages`. "Show the work" flips a result to its tree, its source events and the check it passed.
- Tap a seat to call `/v1/view-as`. Whatever is private to them is hatched.
- Phone: your side first, the table one swipe away. Every target is at least 44 px. No horizontal scroll.
- Press-and-hold signs through the existing trusted consent path, with a non-hold way to do the same.

## Gates

Each opens only when the last passes in a real room with the live model.

1. **Engine.** Sign, begin, brief and offer in a real web room, reaching real plans with no demo script. Live test reports cost and time.
2. **Things get made.** A signed plan gives real results, a sentence re-plans only what it touches, the room ends cleanly, and the deadline ends it too.
3. **The Table.** The whole walk in Chrome on real events, on desktop and phone, with several real browsers in one room.

Then: spec updated, `FREEZE_TAG` moved to a new tag, `tools/check.py` green, public host next.
