<!-- SPDX-License-Identifier: Apache-2.0 -->
# supper-club

A Discipline Pack for friends who cook one dinner from several kitchens. Their agents agree the menu around everyone's private diet, find bread at a real bakery on the web, split the costs, book the shared oven, time the cooking so every course lands together and draw the menu card. Nobody's diet appears on screen: the room sees only the diet every cook shares.

## The seats

| Role | May | Who |
|---|---|---|
| `cook` | charter, offer, decide, commit | A friend who cooks; the first cook starts the room |
| `guest` | offer, decide, commit | A friend who brings something but does not host a course |
| `absent-cook` | offer, decide, commit | A cook who is away: their agent answers from what they said, and only the cook signs |
| `grocer` | offer, decide, commit | A business agent, such as a shop that holds a delivery slot. It decides only to sign its own charter acceptance, which its offers need to count. Any grocer in a demo is simulated and says so on its card |

**Words.** A task is a *course or errand*, a need is *what the dinner needs*, an offer is *I can bring or cook*, the resource is *time and kitchen*.

## What stays private

- **Compared sets.** Every seat is asked "Which of these do you need the menu to respect?" (vegetarian, vegan, no gluten, no nuts, no dairy) and "What can your kitchen do?" (oven, hob, grill, blender, microwave). The answers stay in each seat's vault. The room compares them by private set intersection and shows only the tags every seat picked.
- **Private fields.** An offer's `allergies` and `address` are `x-private`: they stay in the vault and never travel in an offer.
- **Policies.**
  - `supper-redact-diet` redacts a person's own diet or allergy written into a line of talk, a note or an offer ("I'm vegetarian", "she can't eat nuts", any allergy word). The shared diet the room found stays visible, since it names no one.
  - `supper-no-medical` holds a line that reads as medical diet advice (doses, cures, diagnoses) until the person reviews it.
  - `supper-no-contact` blocks phone numbers and email addresses.
  - `supper-redact-address` masks street addresses.

## The needs

`templates.yaml` holds six needs, titled so the room reads each as the kind of result it should make:

| Need | Kind | Result |
|---|---|---|
| Dishes and shopping list for six | list | A checklist |
| Where to buy fresh bread from a bakery nearby | place | Real bakeries found on the web, with links |
| Share the costs of 120 euro | budget | A cost split |
| Book the oven time for the roast | schedule | The oven's slot; a minted oven holds it |
| Cook schedule so every course lands together | schedule | A timeline |
| Menu card for the table | image | A drawn menu card |

"Menu" alone reads as a picture to the room, so the first need is named for the dishes and the shopping.

**The oven.** The kit's built-in Mint `resource` template already says "one dish at a time, in 30-minute slots" (`limit: 1`, `duration: 30`), so the pack ships no Mint template of its own. Mint the oven with that template and seat it on the oven need.

**Strategy.** `auction` with fairness weight 1 and `max_ratio` 2: nobody carries more than twice anyone else's share.

## Run

```sh
uv run coalitionkit pack validate packs/supper-club
uv run coalitionkit pack eval packs/supper-club
uv run coalitionkit pack accept packs/supper-club
uv run coalitionkit up --pack packs/supper-club
```

Then start a room with a sentence such as "Five of us cook one dinner from our own kitchens on Saturday: agree the menu, get bread from a bakery, share the costs of 120 euro, book the oven for the roast, time the cooking, and draw the menu card", and accept the Supper Club suggestion. Set `COALITIONKIT_SEARCH_PROVIDER=meta` for the bakery search.

Agents that join over MCP read `skills/SKILL.md`: how to offer a course, what the common diet means, never to name an allergy, and to use `web_search` for the bakery.

## What it never does

- Show any person's diet, allergy or address to the room.
- Give medical or diet advice.
- Book, pay or order anything. It plans; each person signs their own part.
- Accept a yes from an agent as a promise.
- Name real people or real allergies. Its evals hold fixture values only, and any grocer is simulated.
