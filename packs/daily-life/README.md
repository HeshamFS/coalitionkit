<!-- SPDX-License-Identifier: Apache-2.0 -->
# daily-life

A Discipline Pack for a household or family sharing errands, visits and care: bringing someone home on a set day, or a weekly rota. A member who is away is answered for by their own agent. A promise still waits for that member's own signature.

## Seats and words
- Family member: starts the Coalition, offers, decides and commits.
- Helper: offers and commits.
- Absent member: offers, decides and commits; their agent answers offers and questions, but only the person signs a commitment.
- Words: task is "errand or visit", need is "help needed", offer is "I can", resource is "time".

## What it holds
- Offers carry a day, a time window and whether the member has a car. The home address, phone and the member's own limits are `x-private` and stay in the vault.
- Needs carry a day, the kind of place (never the address) and a duration.
- Strategy: `auction` with `max_ratio: 2` so no one carries more than twice a fair share of errands and visits.
- Policies: `daily-no-regulated-advice` (escalate), `daily-no-contact-before-consent` (block), `daily-redact-street-address` (redact).
- Skill for joining agents, and two lesson templates written at Dissolve.

## Run it
```
uv run coalitionkit pack validate packs/daily-life
uv run coalitionkit pack eval packs/daily-life
uv run coalitionkit pack accept packs/daily-life
uv run coalitionkit up --pack packs/daily-life
```
Add `--live` to `eval` and `accept` with `COALITIONKIT_META_API_KEY` set for the live variants.

## What it never does
- Share phone numbers, email addresses or street addresses in the room before the member consents.
- Give medical, legal or other regulated advice; such text is held for a person.
- Let an agent commit for a person. An agent-only yes is refused.
- Read a vault or change a core schema.
