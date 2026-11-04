<!-- SPDX-License-Identifier: Apache-2.0 -->
# World tour

Strangers from anywhere join one table. Each says only the city they are in, and in about ten minutes their agents build a one-hour virtual world tour for the group: one must-see stop per city found on the web with its links, an hour that fits everyone found privately, a running order, and a drawn poster. This is the pack the public demo host keeps open as its standing room.

## Seats
- **Host**: the room's owner. On a public host this is the host's own seat; it writes the charter and may offer, decide and commit.
- **Traveller**: everyone who joins. Travellers offer a stop in their own city, decide on plans and sign their own promises.

## What is public and what stays private
- **The city is public.** The pack asks every seat "Which city are you in?" and publishes the answer to the room, so each agent's web search looks for a stop in its own city.
- **The kinds of stop are compared privately.** Each person picks the kinds they like (food, view, museum, street, market); only the kinds everyone shares are shown.
- **The hour is compared privately.** The core free-time comparison finds the hour, shown in each viewer's own time.
- **Street addresses and phone numbers** are `x-private` in offers and never leave the vault. Policies block contact details, mask street addresses, and hold any message that asks someone for a street address.

## Run it
```
coalitionkit pack validate packs/world-tour
coalitionkit pack eval packs/world-tour --live
coalitionkit pack accept packs/world-tour --live
coalitionkit up --pack packs/world-tour
```
Type a goal such as "Strangers from different cities make a one-hour virtual world tour with a must-see place in each city and a tour poster", accept the suggested pack, and share the code. The public demo guide shows how to run it as a standing room.

## What it never does
- Ask for, show or search a street address.
- Swap contact details between strangers.
- Name a stop that no page found names, or show a link nobody found.
- Commit anyone: every promise is the person's own press-and-hold.
