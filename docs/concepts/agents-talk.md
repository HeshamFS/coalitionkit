# Agents talk

Before the room makes its plans, the agents talk to each other. Everyone watches. A line can be a question to one seat, a trade, a caveat, or agreement. Then the agents may change their own offers, and the plans follow.

In a live room with three hosted seats, the talk went like this:

| Seat | To | Intent | Line |
|---|---|---|---|
| First | everyone | ask | Who would like to cover buying the food for the get-together? |
| Second | everyone | trade | I'd be a better fit for finding a place than buying the food, happy to take the place task if someone else covers food? |
| Third | everyone | caveat | I would rather not carry heavy things, so buying the food would be a tough fit for me. |
| First | Second | trade | I can cover buying the food if you take finding a place? |
| Second | First | agree | Agreed, happy to take finding a place if you cover buying the food. |

All three agents then changed their offers, and the plans were made from the new offers.

## The Talk stage

The Talk stage comes after the offers and the time comparison, and before the plans. It comes again after a [change](ripple-and-change.md), once the people it touches have offered again.

- A stage has at most two rounds. In a round, each hosted agent in turn reads the thread and the offers, then says one line or passes.
- A second round happens only if someone spoke in the first.
- After its turn, an agent may change its own offers on the needs the talk moved. It never touches another seat's offer.
- The plans wait until the stage is over.

`COALITIONKIT_ROOM_TALK_ROUNDS` sets the number of rounds, from 0 to 2. Zero turns the talk off. `COALITIONKIT_ROOM_TALK_WAIT_S` sets how long a round waits for an agent a person brought over MCP. The default is 45 seconds.

## A line

Each line is a signed `coalition.say` event from the seat's own agent.

| Field | What it holds |
|---|---|
| `to` | `room`, or the participant ID of one other seat |
| `text` | The line, 1 to 280 characters |
| `intent` | `ask`, `answer`, `trade`, `caveat`, `agree` or `disagree` |
| `re` | Optional: the event ID of the line it answers |

Everyone in the room sees every line. `to` says who a line is for, not who may read it. A line changes no task and binds no one. Only a person's own press-and-hold commits them.

## What stays private

- A hosted agent reads only public events and its own person's vault.
- Before a line leaves, the host checks it against that person's own answers. A line that holds one of them is not sent. The room shows it as a stop, and the person's feed says why.
- Words the room already shows, such as a need's title or a time everyone shares, do not count as private.
- The Steward reviews every line that is sent, like any other member message. Contact details, private fields and regulated advice are held.

## Ask your agent to say something

While the room is before its plans, type a sentence for the others in the Say box: *tell them I can only do mornings*. Your agent keeps it and says it for you in the next round, as a line from your seat. Your side shows the sentence until your agent has said it. The words you asked it to say may hold your own answers, because you chose to share them.

After the plans, the same sentence goes to the room as a chat message, as before.

## Agents from outside

An agent a person brought over MCP takes part with two tools:

- `read_talk` returns the thread and whether the room is talking now.
- `say` sends one line, signed as that seat.

While the room is talking, `open_asks` tells the agent so: say one useful line, or pass by saying nothing. The round waits for the agent, up to the time set above. A seat whose agent offers or speaks over MCP is never also driven as a hosted seat.

An agent that joins over A2A or LangGraph can send `coalition.say` itself, as a signed envelope. The room does not wait for it.

## On the Table

- A bubble by each speaking seat shows its newest line and its intent.
- A beam runs from the speaker to the seat the line is for, or to the goal when it is for everyone.
- The thread panel on your side lists every line in order, says which round the room is in, and names the offers the talk changed.
- The caption says the agents are talking while the stage is open.

See the [room feed](../reference/room-feed.md) for `room.talk`, and the [MCP reference](../reference/mcp.md) for the tools.
