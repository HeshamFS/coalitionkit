# The CoalitionKit journey: one goal, start to end

Status: draft for Hesham's review · 2026-10-31
Design source: the claude.ai canvas "CoalitionKit design" (boards Stage, Room, the nine Concept moments, the catalog sheets 00 to 11).

## 1. Why this document exists

PR #4 made the catalog match sheets 00 to 11. The product around the catalog does not follow the design yet. The design shows a product in nine moments; the web app shows a token box and an empty dashboard.

| Design (canvas) | What the web app does today (`main` at 1b3a2e3) |
| --- | --- |
| **Genesis**: the first screen is a dark stage with a round table. You type or say a goal; seats fill, needs and roles appear, a pack is suggested, you invite any agent | The first screen is a small "Viewer token" box in the top-left corner. Nobody can start a coalition from the web; creation is admin-only with a fixed JSON charter |
| **Prism**: one state, a different screen for each person; "View as" takes a panel apart and rebuilds it for someone else | Three identical cards, each saying "No current item in your projection". "View as" exists but shows nothing distinct |
| **Overlap**: you watch two vaults find shared free time while blinded points cross | Not built |
| **Ripple**: a change travels through the plan graph; only touched nodes move; "3 of 20 tasks re-planned" | Not built (the log line exists) |
| **Theatre**: agents from four vendors move around the Gardener; bubbles open their real messages; the Steward blocks visibly | Not built |
| **Chain**: decisions as signed links; tampering breaks the chain visibly | A raw log list ("1 charter · 2 join · …") |
| **Consent seal**: press and hold to sign with your own key, with "if you say yes" and "what stays private" | Built (PR #4), but reached through a "Read / Charter" button on an otherwise empty room |
| **Dissolve**: the table folds away, lessons are written as skills, measured results stay | Not built |
| **Glasses**: one card, one step | Not built |
| **Theme**: working screens (Stage, Room, Chain, Ripple, Prism, Dissolve) are drawn light; Genesis, Theatre and Overlap are dark stages. Both themes have tokens (design system board) | The room renders dark only, so it never looks like the Stage board |
| **Germination** (Idea Book, "Generative UI on the fly"): every component arrives as a labelled skeleton, fills, flashes once when live, settles | Components appear statically; nothing shows that the screen was composed for you |

The demo is also silent: `coalitionkit up --demo` enrolls three members who never act, so every projection is empty and no moment could show even if it were built.

**Root cause.** We built bottom-up (catalog components, then a room that lists state) without a written end-to-end journey. This document is that journey. Every screen we build from now on traces to a story below, and every story names the moment board it must look like.

## 2. Rules every screen follows

From the Idea Book's eight UX rules, plus what the canvas shows:

1. **Generative from the first second.** The first thing anyone sees is a screen being composed for them. Components germinate (skeleton, fill, flash, settle) and say what they were built from. A visitor must understand within ten seconds that no screen here was designed in advance.
2. **Nothing to install.** A link, a sentence, a voice note.
3. **Only your part, where you already are.** Web, phone, WhatsApp, Claude or ChatGPT (MCP App), glasses.
4. **The right person decides, with one press-and-hold.** Agents never say yes for you.
5. **Absent is fine.** Your agent answers capacity questions; nothing counts until you approve.
6. **Ask rarely.** People are interrupted only for decisions that are theirs.
7. **Show the work.** Every element can open the protocol message that produced it (wiring) and who decided it (provenance).
8. **Leave no mess.** The coalition dissolves; only lessons remain, as skills.

Plus three honesty rules that already bind this repo:

- **Real people only.** The person typing the goal is the owner; members are the people and agents they invite. No invented names in core, seeds or demos.
- **No case data in core.** Core screens use the words of the goal the owner typed. Scenario words (flights, labs, care) come only from a pack.
- **Measured, never promised.** Numbers on screen (minutes, cost, calendars shared) come from the log or the cost meter; until measured they show `[MEASURED]`.
- **Claimed only when proven.** A screen states an outcome ("signed", "verified", "vaults closed") only when the host returned the evidence for it. Otherwise it says what is pending.

### Who may see and do what

Every screen is composed on the host for the **requesting viewer**, from the events in that viewer's scope (spec, Scopes and Projections). The browser never receives anything the viewer may not see, and it never composes another person's view itself.

| Action | Who may do it | Credential |
| --- | --- | --- |
| Draft a coalition from a sentence | Anyone at the local host (`up`), or the operator with the admin token on a hosted deployment | Local: loopback client, `Origin` equals the host, JSON body. Hosted: admin token, server side only, never in a browser |
| Start the drafted coalition | The person holding the **start code** | `up` prints a start link `http://127.0.0.1:<port>/#start=<code>`. The code is single use, expires after 24 hours, travels in the URL fragment (never sent in a request line, never logged), and the web removes it from the address on load. Starting returns the owner's viewer token |
| Invite | The owner | Owner viewer token. Each invitation is single use, carried in a link fragment (`/join#<invitation>`), revocable by the owner until redeemed |
| Join | Whoever holds an unused invitation | The invitation; it is exchanged for a viewer token and dies |
| Decide, approve, commit | The participant themselves | Owner-key `consent_sig` (spec, Owner keys). Agents propose and answer; they never commit anyone |
| Dissolve | The owner, or the host on deadline or budget | Owner viewer token; the host emits `coalition.dissolve` |
| View as | Anyone, for any participant or role | Composed as the **intersection** of the requester's scope and the target's scope: you see what they would see, minus everything you may not see. A request to view as someone outside your scope returns their public summary only |

The admin token never reaches a browser. Viewer tokens live in memory and `sessionStorage` for one tab, as today.

## 3. The zero-pack journey

Zero-pack means no Discipline Pack is loaded: the coalition runs from the plain-language goal alone (FR-05, success criterion 2). Every story below must work with no pack. Packs come in section 4.

Actors: **Owner** (the person who types the goal), **Member** (a person who joins, through their own agent from any vendor), **Business** (a business agent over A2A, or one minted by the Mint), **Machine** (a device minted as a read-only agent), **Steward** (independent checker), **Gardener** (planner and host).

### Act 1 · Form

**J-01 Start from a sentence** (moment: Genesis)
As an Owner, I want to type or say what I want done, so that a coalition forms without me filling in a form.
- The first screen at `/` is Genesis: dark stage, the round-table mark with empty seats, one composer ("What should get done?") with a microphone.
- As I type, the Gardener reads the sentence live and the stage answers: seats fill one by one, cards germinate beside the table: **Seats it found** (roles read from my sentence), **Needs**, **Deadline**, **Discipline pack** (suggested pack, or "No pack: plain language"), **Invite, any agent**.
- Pressing send lights the centre of the table blue and shows "Goal set · the Gardener is drafting the first plans".
- Done means: with no model key, a deterministic reader still fills roles, needs and deadline from the sentence; with `COALITIONKIT_META_API_KEY` set, the Gardener's model drafts them (live variant run and reported). The charter it creates passes the same validation as `POST /admin/coalitions`.

**J-02 Correct the draft before it starts** (Genesis)
As an Owner, I want to adjust what the Gardener understood, so that the coalition starts with the right roles and deadline.
- Each germinated card is editable in place (rename a role, change the deadline, remove a need). Edits re-germinate only the card they touch.
- Nothing is created on the host until I press **Start**; then the charter event is the first link in the chain (seq 1).

**J-03 Invite people through their own agents** (Genesis → Room)
As an Owner, I want to invite people through whatever they already use, so that nobody installs anything.
- The invite card offers: copy link, QR, "Add to Claude", "Add to ChatGPT", WhatsApp, A2A Agent Card URL. Each produces a one-use invitation from the host.
- Seats on the table fill as members join; each seat shows the vendor of the agent that joined ("agent on ChatGPT", "agent in Claude").

**J-04 Join from a link** (Room, phone)
As a Member, I want to open a link and be in, so that I take part in seconds (US-01).
- The invitation link opens a short join screen: what this coalition is for, who started it, what it will and will not see about me, and one **Join** button. No token box; the viewer token is exchanged behind the link.
- The token box remains only as a fallback for developers, styled to the system, under "Have a token?".

### Act 2 · Work

**J-05 See my part, composed for me** (moments: Prism, Germination; boards: Room, Stage)
As a Member, I want to see only my part, on my device, so that I know what to do at a glance (US-03).
- My room is composed by the host from catalog components for me alone. On first load, each component germinates in order: skeleton with its catalog name, then content, a single flash, then rest.
- Phone shows the Room board: "your part" hero card, the ask (if any), my timeline, "What others know about you".
- Desktop shows the Stage board: the goal bar, a grid of **participants' screens**, plan options, the measured strip, and the aside with Wiring, Decisions and What stayed private. Each miniature is composed on the host for the requesting viewer: the intersection of my scope and that participant's (see "Who may see and do what"). Where that intersection is empty, the miniature shows the participant's public summary (seat, vendor, status) and says "private to them".
- **View as** plays the Prism transition: the panel takes itself apart and rebuilds as the intersection view for the chosen participant or role. The Prism moment is shown in full by opening the same coalition as two members on two devices side by side; the demo script does exactly that.
- Done means: a test signs in as two members with disjoint private data and asserts that neither's browser projection, miniatures or "view as" response contains the other's private fields.

**J-06 Say what I can do without saying why** (moment: Overlap)
As a Member, I want to state my limits privately, so that the coalition can match me without learning my life (US-02).
- My agent (or I, in a private panel) fills my vault: free times, places, budget, constraints. The panel is visibly marked "never leaves this circle".
- When matching runs, the Overlap view plays: my vault and theirs on either side, blinded points crossing through the host, then one result: "Shared: [what matched]" and "your other N stayed private".
- The host relays only blinded points; it never learns the overlap. The result exists in each participant's own vault. For a hosted vault (run by the host on the member's behalf), the vault hands the result to its own member's viewer over the member-scoped agent channel (`/v1/agent`), never into the log and never to anyone else. A member whose vault runs on their own device shows the result locally.
- Done means: the view's crossing points come from the real `coalition.match` rounds in my scope; a test asserts the requester sees "Shared: ...", while every other viewer's feed and agent channel carry neither the result nor either raw set. Core work: the vault-to-own-viewer channel is part of S1b.

**J-07 Watch the agents work** (moment: Theatre)
As any participant, I want to see the agents negotiating for the people they serve, so that I trust the work without reading logs.
- Theatre view: the Gardener in the centre; each agent as a coloured cursor with its vendor; bubbles for offers, vault answers, matches, holds. Every bubble opens its real message.
- Steward interventions appear in red with the policy name ("blocked a request for contact details · no-contact-before-consent").
- Footer counts: agents, vendors, "people interrupted only for decisions".

**J-08 Choose between plans, not argue** (Stage: plan options; Idea Book: tension cards, plan universes)
As a Member, I want options side by side with their trade-offs, so that we decide without a chat argument (UC-3).
- Plan options show as universes A/B/C with their objectives ("earliest · higher cost", "fair split · +25 min", "lowest cost · later"), and "none better on every goal; you choose".
- Choosing one folds the others away and records the decision.

**J-09 Approve what commits me** (moment: Consent seal)
As a Member, I want to approve or veto anything that commits me, so that nothing happens in my name without my yes (US-04).
- The ask arrives as a card in my part ("Your agent asks before it commits you") and as a notification on my channel.
- Opening it shows the Consent board: the question in one line, **If you say yes** (each consequence), **What stays private**, then press-and-hold to sign with my key. Done: "Signed." plus the receipt (seq, signature).
- "See the other plans" returns to J-08.

**J-10 Something changes; only what it touches moves** (moment: Ripple)
As a participant, I want a change to re-plan only what it affects, so that I am not asked again for things that still hold (UC-7, FR-13).
- A change (someone drops out, a resource disappears, a deadline moves) sends a ripple through the plan graph: the touched nodes pulse, untouched nodes stay still; affected screens flash only the numbers that changed.
- Counter: "N of M tasks re-planned · K people asked again · rest untouched", with the measured time to every affected screen.

**J-11 Bring in a business or a machine** (Theatre, Prism; UC-4, UC-5)
As an Owner, I want to add a business or a device as a participant, so that bookings and readings happen inside the coalition.
- "Add a participant" offers: an A2A business agent by Agent Card URL, or **Mint from a video** (the Mint flow, catalog sheet 10).
- A business invitation is a link the business agent redeems with its signed card (`/invitations/redeem` with `card_url`, which exists). The host verifies the card; the seat appears square (businesses and minted agents) with its vendor.
- Mint: the owner uploads a short video and an optional voice note; the host runs the Mint pipeline (`packages/mint`), shows its stages (perceive, schema, prove, publish) live, and enrolls the minted agent only after its tests pass. A refused Mint shows the refusal reason and enrolls nothing.
- The business's own screen in Prism shows only its orders ("no names, no reasons").
- Done means: enrollment succeeds with a valid signed card; an unsigned or tampered card is refused with the reason on screen; a business viewer's projection contains no member private fields.

### Act 3 · Finish

**J-12 Verify what happened** (moment: Chain)
As any participant, I want to verify the record, so that I can trust who decided what.
- "What happened" is the Chain view: decisions as signed links (seq, type, hash, "signed"), and "receipt · head matches". Scrubbing replays any moment **as I saw it** (my own scope only; there is no replay as another person).
- **Verify** runs the spec's reader check (Coalition Protocol, "The authenticated log boundary") in the browser: the feed delivers my log as originals, host-signed projections and stubs `{seq, prev_hash, hash}` for events outside my scope, plus the host public key pinned at join and the receipts I kept. The browser verifies every projection's host signature (EdDSA over JCS), then checks gap-free seq from 1, seq 1 against the genesis hash, each `prev_hash` against the previous entry's hash, and every kept receipt's `head_hash`. It is the same algorithm as `verify_chain` and `check_receipts` in `coalitionkit_contracts`, and it runs against the spec vectors in a unit test.
- A failure names the first bad seq and the check that failed, drawn as the broken link in red. The view never claims more than the checks cover: "verified up to your latest receipt, seq N".
- Core work: the feed does not carry the log, stubs, host key or receipts today. Slice S1b adds them before the core freeze.

**J-13 End and keep the lessons** (moment: Dissolve)
As an Owner, I want the coalition to fold away when the goal is met, so that nothing private lingers (rule 8, UC-9).
- The owner presses **End coalition**, or the host dissolves on deadline or budget. The host emits `coalition.dissolve` with `reason` and `skills_written`; open tasks close as `withdrawn` (spec, Coalition end).
- Dissolve plays from that event: outcome cards fold into the mark, lessons appear as SKILL.md cards (each scoped no wider than the events it came from, spec rule "derived takes the narrowest scope"), and the measured strip stays (calendars shared, minutes, model spend, vendors).
- Each closing claim is shown only with its evidence: "tasks closed" from the dissolve transition; "viewer links revoked" after the host revokes every viewer token and invitation of the coalition and returns the count; "hosted vaults erased" after the host deletes hosted vault state and returns the count. If any step fails, the screen says which one and offers a retry; it never shows "nothing kept" on a partial cleanup.
- Done means: a test dissolves a coalition holding sentinel vault values, then shows old viewer tokens get 401, invitations are refused, and the sentinels are absent from the store and from every lesson.

**J-14 Take part from glasses** (moment: Glasses; UC-8)
As a Member wearing glasses, I want one card and one step, so that I act with my hands free.
- `/glasses` renders the current step only: large type, step n of m, "say done or skip", agents never press buttons. Runs in the Ray-Ban Display simulator if no device is available.

## 4. Packs: plugins on top of the journey

A Discipline Pack never adds a screen and never changes the core. It is loaded on top and gives the same moments its words and knowledge. The manifest already supports this (`packages/packs`, `pack.yaml`):

| Pack part | What it changes in the journey |
| --- | --- |
| `vocabulary` | The words on every card: "seats" become "travellers", "lab members" or "family"; "tasks" become "rides", "runs" or "visits" |
| `roles` | What Genesis proposes as seats, and who may decide |
| `schemas` (need, offer, task, resource) | What J-06's vault panel asks for, what offers look like |
| `task_templates` | What the Gardener drafts first in J-01 |
| `strategy` | How plans in J-08 are allocated and what "fair" means |
| `policies` | Extra Steward rules (for example, regulated advice only through a reviewed flow) |
| `views` | Which catalog components compose each role's part in J-05 (catalog components only; the loader refuses raw UI) |
| `skills` | What J-13 writes, and what a later coalition loads |
| `mint`, `connectors` | Which businesses and machines J-11 can bring in |

In Genesis the pack appears as one chip: the suggested pack from the sentence, or **No pack: plain language**. Switching it re-germinates the cards in the new vocabulary; the table and the moments stay the same. The rule we prove at G3: the diff of core packages between G1 and the packs is empty.

Candidate packs (the two for G3 are Hesham's decision):

- **Science**: samples, instruments, runs across labs; Mint brings in an old instrument; lessons are protocols.
- **Daily life**: a family or household coordinating care, visits, errands; absent members' agents answer; picture cards for whoever needs them.
- **Flight (travel disruption)**: stranded travellers, car desks, hotel shuttles; the travel example drawn on the canvas lives here, not in core.

## 5. Build slices and gates

Gates open by result, never by date. The order is:

1. **Core slices** (S1, S1b, S3, S8) land on `feat/ux-journey`.
2. **Journey gate**: J-01 to J-14 walk end to end in Chrome, once with no model key and once live with `COALITIONKIT_META_API_KEY` (cost and latency reported), each screen side by side with its board. `uv run python tools/check.py`, `npm run typecheck`, `npm test`, `npm run lint`, and the e2e suite pass.
3. **Core freeze**: merge to `main` and tag `core-freeze-2`. The core path set is `packages/` and `spec/`. CI gains a check that fails when a pack branch changes any file in that set relative to the tag.
4. **Packs** start only after the freeze, each as a plugin loaded by the existing loader, each with its evals in CI.
5. **G3**: two packs pass their evals and the freeze check shows an empty core diff.

The G1 baseline moves from the G1 commit to `core-freeze-2`, because this journey needs core work (Genesis, the log in the feed, dissolve cleanup, Mint enrollment) that G1 did not include. That is Hesham's call (decision 4).

| # | Slice | Stories | Where | Owner |
| --- | --- | --- | --- | --- |
| S1 | **Genesis and membership on the host**: `POST /v1/genesis/draft`, `POST /v1/genesis/start` (start code), `POST /v1/invitations` (owner issues, kinds member and business), `DELETE /v1/invitations/{id}` (revoke), `POST /v1/invitations/accept`, `POST /v1/coalition/dissolve` (owner) with token revocation and hosted vault erase, each returning counts | J-01 to J-04, J-11 (business), J-13 | `packages/server`, `packages/cli` | Codex (worktree) |
| S1b | **The log in the feed**: the feed carries the viewer's log as originals, projections and stubs, the pinned host key and the viewer's receipts; a viewer-scoped "view as" composition endpoint (intersection scope); a hosted vault's match result delivered only to its own member over `/v1/agent` | J-05, J-06, J-12 | `packages/surfaces`, `packages/server` | Codex (worktree) |
| S3 | **Agents that act in the demo**: `up --demo` runs hosted member agents for the enrolled demo participants. Members send only member messages: offers, vault answers, match rounds, observations. The host's Gardener creates needs, queries, proposals and tensions from them (host-only types, spec Who may send what). For web-started Genesis coalitions, a durable host loop posts the drafted needs after the first participant accepts the charter, debounces counted offers into proposals and tensions, and re-plans tasks invalidated by member ripples. It resumes from the log on restart without repeating needs or unchanged proposals. Refused drafted needs are recorded once and reported in the owner's room; the remaining needs continue. Admin-created and demo coalitions retain their own drivers. The loop never sends member messages or approves a decision. Every commitment waits for that participant's owner-signed approval in the room. Live variant with the Meta key. Synthetic protocol fixtures stay in tests only | J-05 to J-10 data | `packages/cli`, `examples/members` | Codex (worktree) |
| S8 | **Mint enrollment**: host endpoint that accepts a video and voice note, runs `packages/mint`, streams its stages, and enrolls the minted agent only after its tests pass | J-11 (Mint) | `packages/server`, `packages/mint` (wiring only) | Codex (worktree) |
| S2 | **Genesis screen** at `/`: stage, the mark with seats arriving, germinating cards from the draft and its reading spans, editable draft, Start with the start code, invite card; `/join` page; sign-in moves to "Have a token?" | J-01 to J-04 | `apps/web/src/genesis/*`, `App.tsx`, `SignIn.tsx` | Claude |
| S4 | **Stage and Room to the boards**, with **Germination** (Assemble: 450 ms, skeleton, fill, live) on every composed component and the **Prism** transition for View as | J-05, J-08 | `apps/web/src/RoomView.tsx`, `room/*`, `shell/*` | Sonnet subagent, Claude reviews |
| S5 | **Theatre, Overlap, Ripple** driven by real events | J-06, J-07, J-10 | `apps/web/src/moments/*` | Sonnet subagents, one per view |
| S6 | **Chain with in-browser verify** (tested against `spec/vectors`), **Dissolve** with evidence, **Glasses** | J-12 to J-14 | `apps/web/src/moments/*`, `/glasses` | Sonnet subagent |
| S7 | Consent seal reached from J-09 cards and notifications (exists; rewire); "Add a participant" panel for J-11 | J-09, J-11 | `apps/web/src/components/consent.tsx`, `TrustedRequest.tsx`, `apps/web/src/participants/*` | Claude |

Judging: Claude reviews Codex's slices; Codex critiques Claude's and Sonnet's diffs (`duo diff`). Each slice merges into `feat/ux-journey`; one PR to `main` at the journey gate.

## 6. Decisions for Hesham

1. The two packs for G3 (science, daily life, flight, or another).
2. Local Genesis: drafting open on 127.0.0.1 and starting with the printed start code (proposed), admin token on hosted deployments.
3. Glasses: real Ray-Ban Display or the simulator for filming.
4. Move the G3 empty-diff baseline from the G1 commit to `core-freeze-2`.

## First screen

A visitor without a session lands on `/`: a sentence box over a map of open rooms, with the explanation below. The sentence carries to `/open`, the Genesis screen. Light is the default whatever the system says; dark is a choice the browser remembers.

Discoverable rooms are not stored yet. `GET /v1/rooms` lists only what an operator supplies with `COALITIONKIT_SAMPLE_ROOMS`, and marks every entry as a sample; without a file the map says it is empty. The kit ships no such file. `examples/rooms/sample-rooms.json` is one to run with. The ground under the map is a fixed pattern that keeps the rooms' relative places. It is not a street map yet.
