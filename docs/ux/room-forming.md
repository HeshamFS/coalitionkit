# Room forming and the Door: the host contract

Status: approved direction A, 2026-11-02. Design: https://claude.ai/artifact/EKLcPFdmKtFu2qfiUuXbRX

After the first screen, a sentence becomes a screen composed for it, the opener says who can find the
room, and the Door holds a QR and a short code while seats fill. Nobody needs a start link.

## 1. The composed draft

`POST /v1/genesis/draft` keeps every field it has and adds:

```
composition: { source: "reader" | "model", cards: Card[] }
draft.place: string | null          // the place named in the goal, in the goal's words
Reading.kind may also be "place"
Card = {
  id: string,                       // unique in the composition
  component: string,                // a name in the closed catalog (spec/catalog/coalitionkit-v0_9.json)
  title: string,                    // plain words, in the goal's words where it can
  word: string | null,              // the exact substring of the goal that produced this card
  size: "hero" | "wide" | "half" | "third",
  props: object                     // valid for that component
}
```

Rules:

- The host validates every card with `validate_surface` against the catalog and drops any that fail. A
  composition always holds a `SeatRing` card, built from the draft's roles.
- Props hold only what the sentence says or the draft holds. Nothing is invented: no people, no
  numbers, no readings. A card with nothing known yet uses the component's empty form.
- At most 6 cards. No two sentences need the same set: the choice follows the sentence.
- The core stays domain-agnostic. No word from `tools/discipline-denylist.txt` under `packages/`.
- Reader, without a model, generic rules only: a place makes `MapView`; seats make `SeatRing`; a
  deadline makes `Deadline`; needs make `Checklist`; a weekday makes `CalendarWeek`; "fair" makes
  `FairnessMeter`; ordered steps ("X then Y", "X and Y" as verbs) make `DependencyGraph`.
- Model, with `COALITIONKIT_META_API_KEY`: the model's closed reply model holds a list of cards chosen
  from a closed list of kinds, with plain fields per kind; the host maps them to catalog props and falls
  back to the reader's cards on any failure, inside the existing draft budget. Keep a separate closed
  reply model and test its `response_format` (never the host's response model as a strict schema). A
  live test marked `live` runs next to the scripted tests and reports latency, tokens and cost.

## 2. Opening without a start link

`POST /v1/genesis/start`:

- `genesis == "local"`: the `Authorization: Start` header is optional. The gate already holds it to a
  loopback, same-origin caller. A valid code is still accepted. At most 10 starts a minute on the host,
  else 429.
- `genesis == "admin"`: unchanged, the code is required.
- Body adds `visibility: "code" | "nearby"` (default `"code"`). `draft.place` is stored.
- Reply adds `door: Door`.

A draft may ask for `accept_suggestion: true`, so the first reading uses the suggested pack without a
second model call. A deadline already past is refused (422). A `place` that isn't words from the goal
is dropped, because it goes public.

`up` keeps printing its start line only if something still needs it; the page no longer does. Local mode
trusts loopback, so a local host must never sit behind a tunnel or a proxy: that would open starts to
anyone. A public host needs its own mode, which does not exist yet.

## 3. The Door

A many-use short code, three characters, dash, four, from an alphabet without look-alikes
(`ABCDEFGHJKMNPQRSTUVWXYZ23456789`). Stored per coalition, stored plainly because the opener can see
it again, revocable, closed by the deadline, a full room, or dissolve. Dissolve erases every door,
knock and arrival row.

```
Door = {
  code: string, link: string,       // link = base + "/join#" + code
  stopped: boolean,
  visibility: "code" | "nearby",
  goal: string, place: string | null, closes_at: string,
  seats: number, filled: number,    // seats = sum of role counts; filled = seated members
  arrivals: { participant: string, role: string, label: string,
              home: "hosted" | "whatsapp" | "mcp" | "a2a", at: string }[],  // newest first
  knocks: { id: string, at: string }[]   // unanswered only
}
```

| Call | Who | What |
| --- | --- | --- |
| `GET /v1/coalition/door` | owner bearer | the Door |
| `POST /v1/coalition/door/stop` | owner bearer | stops the code, returns the Door |
| `POST /v1/coalition/door/knocks/{id}` `{answer: "yes" \| "no"}` | owner bearer | answers a knock, returns the Door |
| `GET /v1/door/{code}` | anyone through the gate | `{goal, place, closes_at, seats, filled, roles: [{id, label, open}]}` where `open` is seats left; 404 when unknown, stopped or closed |
| `POST /v1/door/join` `{code, display_name?, role?}` | anyone through the gate | same reply as `/v1/invitations/accept`; a role with an open seat is used, else the first role with one; 404 unknown or closed, 409 full, 429 too many tries (per code and per caller, sliding minute) |
| `POST /v1/rooms/{id}/knock` | anyone through the gate | `{knock: id, secret}`, rate limited; 404 unless the room is listed |
| `GET /v1/rooms/{id}/knocks/{knock}?secret=` | the knocker | `{state: "waiting" \| "yes" \| "no"}`, plus `invitation` once on yes (a one-use secret for `/join#`) |

A knock nobody answers lapses after 15 minutes: it leaves the queue and reads as a no. An invitation
for a full room answers 409 before it is spent. A join by code reuses `issue_invitation`, `redeem` and `enroll_member`. The opener's own seat counts as
filled and appears in arrivals. Refused joins name no seat holder.

## 4. The map

`GET /v1/rooms` lists the operator's samples as today, plus every open room with visibility `nearby`:
`{id, goal, place, seats, filled, closes, lat, lon, status, sample: false}`. Only those public fields
leave the host. Rooms hold no coordinates yet, so `lat`/`lon` are a stable position derived from the
room's id inside the samples' bounds (or a default box), and the map keeps saying it is not a street
map. A room leaves the list when stopped, full, past its deadline, or dissolved.

Short code joins and knocks are additions to how a participant is admitted: record them in `spec/`
before the code if the spec's text on invitations would otherwise disagree.

## 5. What the page may say

Claimed only when proven. Nothing says the Steward read the sentence unless the host ran it. "People
nearby" today means a pin on this host's map; there is no distance filter and "Anyone" is cut (approved
first cut).
