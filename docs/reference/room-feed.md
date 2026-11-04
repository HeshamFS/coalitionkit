# Room feed

A viewer follows a room over `GET /v1/feed`, a stream of server-sent events using AG-UI. The first event is a `STATE_SNAPSHOT`, and deltas follow. `state.room` is built separately for each viewer, and only `mine` is private to them.

## How a room runs

| Moment | Who acts | Events in the log | Model step |
|---|---|---|---|
| Arrive | Person holds to sign | `join`, `decide(charter)` | none |
| Needs | Gardener | `need` for each | Goal to 2-6 needs, each with a title and a kind, and up to 6 shared time slots |
| Begin | Owner, or automatic when every seat is signed | `charter` revision only if seats change; helpers `join`, `decide(charter)` | none |
| Brief | Each seat's agent asks its person | none: answers go to the vault | 1-3 questions of closed kinds |
| Offer | Each seat's agent | `offer` per need | Which needs, at what cost, checked against the vault |
| Compare | Vaults | `query`, `answer`, `match` rounds | none |
| Talk | Each seat's agent, in turn, for up to two rounds | `say`, then new `offer` from agents that change their own | One line or a pass, and the needs whose own offer to change |
| Plans | Gardener | `propose`, `tension` | A public name and line per plan, and a private "for you" line per seat |
| Decide | People | `decide` | none |
| Commit | Agent asks, person signs | `commit`, `decide(commitment)`, `decide(task)` | none |
| Make | Assignee's agent | `observe` (source `document`) holding the result, then `done` for helpers and devices | A catalog tree per task |
| Device | A minted device's seat | `offer` on a hold it took, `observe` (source `device`) per reading, `ripple` when a reading crosses its threshold | none |
| My part | Person | `done` with evidence | none |
| Say | Anyone | Private note, `observe` (chat) or `ripple` | Route the sentence |
| Change | Agents, then the people asked | `ripple`, new `offer`, then a Talk stage, `propose`, `tension`, limited to who is affected | As above, for the tasks it touches |
| Finish | Owner, or the deadline | `dissolve` | none |

Every model step has a rule-based fallback. Each output records `source: "model"` or `"rules"`, and the screen shows it.

## `state.room`

```ts
type Room = {
  phase: "gather" | "brief" | "work" | "decide" | "commit" | "make" | "live" | "ended";
  lights: "day" | "night"; // day means it is your turn
  goal: string;
  closes: string; // the charter deadline: when the room ends by itself
  seats: {
    seat: string; role: string; label: string;
    kind: "person" | "helper" | "device" | "open"; you: boolean;
    signed: boolean; state: string;
    busy: { tool: string; args: string; since: string } | null;
  }[];
  needs: {
    id: string; title: string; kind: "place" | "schedule" | "budget" | "list" | "draft";
    detail: string; status: string; offers: number;
    assignee: string | null; result: string | null; source: "model" | "rules";
  }[];
  activity: {
    id: string; at: string; seat: string | null;
    verb: "reading" | "asking" | "offering" | "comparing" | "stopped" | "planning"
        | "explaining" | "committing" | "making" | "saying" | "changing" | "ending"
        | "searching";
    need: string | null; label: string;
    state: "running" | "done" | "failed"; ms: number | null;
    source: "model" | "rules" | "host" | "voice" | "camera" | "search"; event: string | null;
  }[];
  tools: {
    id: string; at: string; seq: number; seat: string; agent: string; tool: string;
    args: string; result: string; status: "started" | "done" | "failed";
    ms: number; refs: string[]; ended: string | null;
  }[];
  slots: { id: string; label: string; start: string | null }[];
  common: { slots: string[]; count_private: number | null; compared: number } | null;
  plan_notes: Record<string, { name: string; line: string; source: "model" | "rules" }>;
  results: {
    id: string; need_id: string; kind: string; title: string;
    by: string; seq: number; source: "model" | "rules"; sources: string[];
    seqs: number[]; tree: unknown[]; data: unknown; messages: unknown[];
    replaced_by: string | null;
    links: { title: string; url: string }[];
  }[];
  search: {
    id: string; seat: string; need: string | null; query: string;
    provider: "meta" | "ddg" | "brave"; ran: string[]; count: number;
    first: string; ms: number | null; stopped: string | null;
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
  measured: {
    calendars_shared: number | null; minutes: number | null;
    cost: string | null; vendors: number | null;
    started_at?: string | null; ended?: boolean;
  } | null;
  talk: {
    open: boolean; round: number; rounds: number;
    stage: "start" | "change" | null; waiting_for: string[];
    thread: {
      seq: number; id: string; from: string; to: string;
      intent: "ask" | "answer" | "trade" | "caveat" | "agree" | "disagree";
      text: string; re: string | null; stage: "start" | "change";
    }[];
    revised: { seat: string; needs: string[]; at: string }[];
    mine: { whisper: string | null; listening: boolean };
  };
  mine: {
    brief: {
      id: string; ask: string; why: string; component: string;
      messages: unknown[]; status: "open" | "answered" | "skipped";
    }[];
    brief_closes: string | null;
    asks: { kind: string; id: string; revision: number; summary: string }[];
    feed: { at: string; text: string }[];
    for_you: Record<string, string>;
    tasks: {
      task_id: string; title: string; status: string;
      result: string | null; can_mark_done: boolean;
    }[];
    inputs: { kind: "voice" | "photo"; text: string; ms: number }[];
  };
  devices: {
    id: string; label: string; template: string; // "resource", "device" or a pack template
    state: "minting" | "approve" | "seated" | "failed";
    health: "live" | "offline"; owner: string; mine: boolean; can_approve: boolean;
    stages: { name: string; state: "done" | "running" | "pending"; took: number | null }[];
    error: string | null; tools: string[]; needs: { id: string; title: string }[];
    attacks: { passed: number; total: number } | null; manifest: string | null;
    cost_micro_usd: number | null; elapsed: number | null;
    fields: { id: string; unit: string; threshold: number }[];
    reading: { field: string; value: number; unit: string; threshold: number;
               over: boolean; t: number }[] | null;
    readings: { field: string; value: number; t: number }[];
    hold: { need: string; start: string; end: string;
            state: "held" | "confirmed" | "released" } | null;
  }[];
};
```

## What the fields mean

- `tools` holds the last 50 tool calls the viewer may see, newest last, read from the `coalition.tool` events. A call's start and its finish (the finish names the start as its `causation_id`) are one entry: `id` and `at` are the start's, `status`, `result` and `ms` are the finish's, and `ended` is when it finished, or null while it runs. `seat` is a participant id or `host`. `refs` are the event ids the call produced or read.
- `seats[].busy` is the newest call of that seat that has started and not finished, for at most two minutes, or null. The Table puts a spark on that seat.
- `activity` is the room's own step lines and is separate from `tools`.
- `results[].id` is the id of the `observe` event. `needs[].result` and `mine.tasks[].result` hold that id. `by` is a seat id. `seqs` holds the log positions of those `sources` this viewer may see, so it can be shorter than `sources`.
- `plan_notes` and `mine.for_you` are keyed by plan id.
- `search` lists the last 20 web searches the agents ran, newest last. `query` is the screened query that left the host, empty when it was refused; `ran` holds the queries the provider actually ran; `stopped` says why a search was refused or failed, else null. No query holds a private value. See [Web search for agents](../guides/web-search.md).
- `results[].links` are the web pages a result came from, read from `data.web`; only `http` and `https` URLs are kept.
- `asks` is what the viewer is asked to decide. A task request whose commitment is also pending is left out, because one yes on the commitment closes both.
- `measured` holds the real numbers for the closing screen. `cost` is null without a cost meter.
- `stops[].to` is the seat a stopped message was aimed at, or null when it was aimed at the room. A plan set the Steward holds appears as a stop without a seat.
- `change.from` is the seat that caused the change, or null when the host did.
- `checked` counts the events the Steward has reviewed in this room, including the ones it stopped.
- `state.cost_meter` is `{spent, currency, calls}`, measured from real model calls.
- `begin` is only for the owner, before the room has begun.
- `results[].replaced_by` is the id of the result that replaced this one, or, while that result is still being made, the id of the successor need.
- `common.count_private` is computed from the viewer's own vault, and is null for a seat that sat out the comparison. It is never stored in the public document.
- `needs[].status` is `no offers` when the offer round is over and nobody has offered on it.
- An offer's minutes are one person's own estimate for one need, capped by the most time they said they would give to any one job. They are never summed.
- `talk.open` is true while the Talk stage runs; `phase` stays `work` meanwhile. `talk.stage` is `start` for the talk before the first plans and `change` for one after a change. Each line's own `stage` says the same for that line.
- `talk.thread` holds every `coalition.say` this viewer may see, in log order. `from` and `to` are seat ids, and `to` is `room` for a line to everyone. `re` is the event id of the line it answers.
- `talk.waiting_for` lists the outside seats a round is still waiting for. `talk.revised` lists the seats whose agent changed its own offers after the talk, and on which needs.
- `talk.mine` is private to the viewer: `whisper` is a sentence they asked their agent to say that it has not said yet, and `listening` is true while a sentence for the others is kept for the talk instead of sent as chat.
- A late joiner gets a brief and a vault, but is not a decider and is not part of the offer or compare rounds.
- `activity[].source` is `voice` on a say or change the person spoke and confirmed, and `camera` on one read from their photo. The Table puts a mic mark by that seat.
- `mine.inputs` holds the viewer's own last ten voice and photo readings: the words the host read, never the audio or the image. `ms` is how long the reading took. It is kept in the viewer's vault and is in no one else's feed.
- `devices` lists the [minted devices](../guides/mint.md#in-a-room) of the room and is the same for every viewer, except `mine` and `can_approve`, which are true only for the device's owner. A seat of kind `device` is the seat of one of them. `hold` never carries the hold's nonce or revision: those stay in the device seat's own vault. `reading` is the latest reading, and `readings` keeps the last 24.

## Results

A result is a `coalition.observe` with `source: "document"`, sent by the assignee's agent, so it is signed, reviewed by the Steward and in the chain like every other event. `content` is JSON:

```json
{"result": 1, "need_id": "<task>", "kind": "budget", "title": "Shared budget",
 "source": "model", "sources": ["<event id>"], "components": [], "data": {}}
```

`coalition.done.evidence` is `[{"kind": "result", "ref": "<observe event id>", "verified_by": "<assignee>"}]`. A helper reports `done` once its result is accepted. A person presses Done themselves.

A change to a task that is already `done` cannot ripple, because `done` is terminal. The host publishes a successor need instead, and the older result is marked replaced.

`results[].data` has one shape per kind:

| Kind | `data` | Export |
|---|---|---|
| `place` | `{options: [{name, why, check, provenance, url?}], chosen: name or null, web?}`. `options` may be empty. A place found on the web has `url` and `provenance: "search"` | none |
| `schedule` | `{items: [{title, start, end, where}]}` with ISO 8601 times, and `steps` beside them | ICS |
| `budget` | `{currency, amount, rows: [{label, amount, who, provenance}], how_shared, time: [{label, amount, provenance, ref}], time_total, suggested: [], total}` | CSV |
| `list` | `{items: [{label, who, provenance}], web?}` | CSV |
| `draft` | `{subject, body}` | text |
| `image` | `{hash, alt, prompt, width, height}`. Without a picture: `{hash: null, alt, prompt, why}` | the picture file |

`web`, when present, is `[{title, url, snippet, source}]`: the pages a web search returned for this result. A `draft` may carry it too.

With no money in the goal, a budget is a time budget: `currency` is `minutes`, `rows` are the signed minutes from offers, and `total` is their sum.

`results[].messages` ends with `updateDataModel`. Its value is the result's `data` with every number written as a string, so a tree may bind to it, for example a `Table` with `rows: {"path": "/rows"}`. For an `image` result it also holds `image.src`, the host path of the picture (`/v1/room/media/<hash>`), which the result's `Image` binds as `src: {"path": "/image/src"}`. The picture itself is fetched from [`GET /v1/room/media/{hash}`](http-routes.md) with the viewer token.

## Brief questions

A question's tree keeps its input at the data path `/answer`, and its Send button carries the action `room.brief` with `{question_id, value}`. The screen posts that to `/v1/room/brief`.

The value is an option id for `choice`, a list of slot ids for `slots`, a number for `amount` and a string for `text`. A number in a data model may be wrapped as `{value, event_ref}`, so both sides unwrap it.

A question can also be answered by voice or with a photo. `/v1/room/voice` with `question_id`, or `/v1/room/photo` with `question_id`, returns `answer` in the same closed shape, or null when the input does not answer the question. The screen shows it and posts it to `/v1/room/brief` only when the person confirms. See [Phone inputs](../guides/phone-inputs.md).

See also [HTTP routes](http-routes.md) and [The Table](../concepts/the-table.md).
