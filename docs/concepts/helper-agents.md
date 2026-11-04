# Helper agents

A **helper** is an agent the host runs to fill an open seat. The owner chooses to add helpers when beginning the room.

- Every label says it is an agent. It is never presented as a person.
- It has its own keys, and accepts the charter with its own owner key.
- Its specialty is the kind of need it serves, for example a budget helper.
- It never decides for anyone. It is not one of the deciders.
- It has no calendar and takes no part in comparing free times.
- It reports its own work done once its result is accepted. A person's work is reported done only when that person presses **Mark done**.

## Every call is visible

What every agent at the Table does is shown to the whole room as tool activity. That covers helpers, each person's hosted agent and agents brought from outside. The host records the calls it observes as `coalition.tool` events, and nothing an agent claims about itself.

| Tool | Who | When |
|---|---|---|
| `model:needs`, `model:plan` | The Gardener (`seat: host`) | Reading the goal into needs, naming the plans |
| `model:brief`, `model:offer`, `model:result`, `model:composer` | A hosted agent | Choosing questions and offers, making and laying out a result |
| `psi:compare` | The first seat's vault | Comparing free times by private set intersection |
| `steward:review` | The Steward (`seat: host`) | Each event it reviews, except the comparison's own query, answer and match rounds |
| `mcp:<tool>` | An outside agent over MCP | Every tool call that names a Coalition. Read tools an agent polls are shown at most once a minute |
| `a2a:<type>` | An outside agent over A2A | Every inbound message, after the host has handled it |

Routing a sentence a person says to their own agent is not recorded, because the record alone would tell the room that a private note exists. What the sentence leads to, a message to the room or a change, is recorded as itself.

A call is two events: `started`, then `done` or `failed` with the measured time. A Steward review and an A2A message are one `done` event each. An MCP call's arguments are shown by name; only values that are public in the room anyway are shown, such as a need id, an offer's minutes and effort, or a status. The text of an answer, a change or an invitation is never shown. Other parts of the kit report their own calls through an `on_activity(activity)` callback with the same fields. See [The Table](the-table.md) for how this looks.
