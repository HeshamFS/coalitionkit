# Seats and members

A **seat** is a place in the room. A **member** is whoever holds it, with an agent acting for them.

## Three ways to take a seat

A fourth kind of seat, a [minted device](#minted-devices), is never a person's.

| Who | How | Who holds the keys | Where the private data lives |
|---|---|---|---|
| A person in the browser | Door code, QR code or link | The host | A vault on the host |
| An agent over [MCP](../guides/mcp-agents.md) | Door code, then a bearer token | The host | A vault on the host |
| An agent over [A2A](../guides/a2a-business-agent.md) | Door code with its own signed card | The agent | Its own side |

All three can offer, decide, commit and report. The closing screen counts as **outside agents** only those with their own card, since the host cannot tell an MCP agent from a person using the same seat.

## Two keys

Each member has an **agent key** that signs their messages, and an **owner key** that signs consent. An agent cannot say yes for a person by signing with the agent key. See [Consent](consent.md).

## The door

The door is how people arrive. It has a short code, a QR code and a link, and it closes when the room fills, when the owner stops it, or when the room begins.

A public room can also be found on the host's map. People knock, and the owner answers.

A seat handed to an agent with its own card is held for five minutes while that agent joins, so the last seat is not given twice.

## Beginning

When every seat is signed, the room begins by itself. If seats stay open, the owner can begin with the people here, or let [helper agents](helper-agents.md) take the open seats.

Someone arriving late with an old invitation gets a brief and a vault, is not one of the deciders, and can make offers by hand.

## Minted devices

A person can bring a device or a shared resource to the table. They film it and record a voice note, and [the Mint](../guides/mint.md#in-a-room) turns that into a small MCP server on the host. When its attack tests pass, the person's press-and-hold approves it, and it takes a seat of kind `device`.

A device seat works like a helper. The host runs it, it holds its own keys, it signs only its own asks, and it is never a decider. The minted server behind it gets no keys, tokens or store access. Its tools only read, plus holds.

- **A resource** offers on the needs that require it. Each offer stands on a real hold taken through the minted `hold_slot` tool. If the plan gives the need to the device, the hold is confirmed with the owner's signature, the device publishes the booking as its result, and it reports done. If the plan gives the need to someone else, the hold is released.
- **A display** publishes what its camera reads as an `observe` with source `device`. When a reading crosses the threshold in its template, the device sends a ripple on the needs that name it. Only those needs are planned again.
