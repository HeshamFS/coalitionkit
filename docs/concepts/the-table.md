# The Table

**The Table** is the room's screen. It is one screen, and what it shows is different for each person.

## What is on it

- **The band:** the goal, how many seats, when it closes, and what the models have cost.
- **The sheet:** the seats in a ring around the goal, the needs, and what is happening now. Beams and sparks follow real events, never a timer.
- **Your side:** what is asked of you, and your agent's private feed. Only you see this.
- **The rail:** where the room is, and the box to say anything.

A plan's cards and the results tray appear on the sheet when they exist.

## Watching the agents work

Every tool call the host sees is on the Table, for everyone in the room. The host records each one as a [`coalition.tool`](../reference/events.md) event: a hosted agent's model call, a private comparison round, a Steward review, an outside agent's MCP tool call or A2A message.

- **The strip** under the sheet, *What the agents are doing*, shows the newest calls, running ones first. Each line names the seat, the tool (`model:offer`, `mcp:make_offer`, `psi:compare`), what it was for, and how long it took.
- **All calls** opens every recorded call as a card, with its arguments, its result and the events it produced.
- **A spark on the ring** marks each seat whose agent has a call running, with the tool's name beside it. It goes out when the call finishes.

The lines hold only what the whole room may see: tool names, need titles, counts, timings and event ids. Answers, vault values, contact details, keys and tokens are never recorded, so they cannot appear here. A line that matches one of the Steward's outbound policies is recorded as `withheld`.

## Light and night

Light means it is your turn. Night comes when the agents are working and nothing waits on you, so you can tell at a glance whether you are needed.

## See as

Tap a seat to see the room as that person may see it. Whatever is private to them is hatched out.

## On a phone

Your side comes first, and the table is one swipe away. The Say box stays on screen. The strip of tool calls keeps the seat, the tool and the time on one line. Touch targets are at least 44 px and nothing scrolls sideways.

## Reduced motion

If your system asks for reduced motion, beams and sparks are turned off. The room is the same.

## Rooms without an engine

A Coalition the room engine does not drive, such as one made directly through the [admin API](../reference/http-routes.md) or with `coalitionkit up --demo`, uses an older five-tab view.
