# Public demo: the standing room

A public demo host keeps one room open for anyone who arrives. The host forms the room itself from a fixed sentence, binds it to a pack, and owns it with its own seat. Visitors join it by its code. Nobody else starts rooms on that host. When the room's time is up it ends, and a new one forms.

This page shows how to run it with the World Tour pack, what visitors can do, and the guards that keep the owner's model bill bounded.

## Run it

Put the model keys in the environment, then start the host with the pack and the standing room settings:

```sh
export COALITIONKIT_META_API_KEY=...
export COALITIONKIT_STANDING_ROOM_GOAL="We need a must-see place in each of our cities, the hour that fits everyone, who shows what in order, and a tour poster for our one-hour virtual world tour"
export COALITIONKIT_STANDING_ROOM_PACK=world-tour
export COALITIONKIT_STANDING_ROOM_MINUTES=15
export COALITIONKIT_ROOM_BUDGET_USD=0.50
export COALITIONKIT_SEARCH_PROVIDER=meta
coalitionkit up --port 8000 --data-dir ./public-host --pack packs/world-tour \
  --public-url https://rooms.example
```

`--public-url` is the address people reach, for example a `cloudflared tunnel --url http://127.0.0.1:8000` address (see [Phone inputs](phone-inputs.md) for the tunnel). Within a few seconds the host prints `Standing room formed: ABC-DEFG`, and the landing page shows the room with its code and seats.

## The settings

| Setting | Default | Meaning |
|---|---|---|
| `COALITIONKIT_STANDING_ROOM_GOAL` | unset | The sentence the room forms from. Setting it turns the standing room on |
| `COALITIONKIT_STANDING_ROOM_PACK` | unset | The installed pack the room is bound to, by name. The host refuses to form a room when it is not installed |
| `COALITIONKIT_STANDING_ROOM_MINUTES` | `15` | How long a room lives, from forming to its end |
| `COALITIONKIT_STANDING_ROOM_GATHER_MINUTES` | `5` | How long the room waits for people before it begins. It begins only when at least one visitor sits beside the host's seat |
| `COALITIONKIT_STANDING_ROOM_SEATS` | `12` | The seats in each room. The host's seat takes the pack's chartering role, every other seat its first role that may offer |
| `COALITIONKIT_ROOM_BUDGET_USD` | unset | The most the models may cost one room, in US dollars. Applies to every room on the host |

All of them are in the [settings reference](../reference/settings.md).

## What visitors can do

- **See the room.** The landing page reads `GET /v1/standing` and shows the goal, the seats taken, the minutes left and the code. It never shows a token.
- **Take a seat.** *Take a seat* joins by the code, the same way as any room's code. A visitor gets a hosted agent, or brings their own over [MCP](mcp-agents.md) or A2A with the code.
- **Answer, talk, hold.** Inside, the room runs as any other: the brief, the offers, the talk, the plans, each person's press-and-hold, the results.

Visitors cannot start a room. While the standing room is on, `POST /v1/genesis/start` needs a start code and `POST /v1/genesis/draft` needs the admin token, so the landing page hides the sentence box.

## The clock

1. **Forms.** When no standing room is open, the host creates one from the sentence. Its owner is the host's own hosted seat. The owner's token is written to `standing-room.json` in the data folder, beside `admin.token`; treat it as a password.
2. **Begins.** After the gather minutes, with at least one visitor seated, the host begins the room: the door closes and the people seated decide. The host's own seat has no person to answer its brief, so its brief is closed.
3. **Ends.** At its time the host dissolves the room with the reason `completed`. Vaults are erased and lessons written, as for any room.
4. **Forms again.** The next step forms a new room with a new code.

## The guards

- **Budget per room.** Before each model call of a room (a hosted agent's question or offer, a made result, a picture, a web search), the host checks the room's metered spend against `COALITIONKIT_ROOM_BUDGET_USD`. Past it, nothing is sent, the rules answer instead, and the Table shows one line: *Model budget reached*. The Steward's reviews are not capped, because they guard what the room shows.
- **Time.** No room outlives its minutes, so an abandoned room costs nothing after its end.
- **No new rooms.** Only the host forms rooms. A visitor's sentence never reaches a model.
- **Search stays public.** Agents search the web only with public words: the goal, the need and, for a pack's public question, the answer the seat published. A street address or anything a person said privately stops the query before it leaves the host. See [Web search](web-search.md).

## Cost

Each room is paid by the host's owner. Read the room's spend on the Table's cost line, or from `spent_usd` in `GET /v1/standing`, and set the budget from what one room should cost. A whole scripted room with three hosted seats costs about $0.17.
