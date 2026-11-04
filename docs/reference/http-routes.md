# HTTP routes

The routes a host serves. Members exchange signed protocol messages over A2A, as described in [the protocol](protocol.md). The routes here serve people, screens and operators.

There are four kinds of access:

- **Viewer**: `Authorization: Bearer <viewer token>`. The route acts only for that viewer.
- **Start**: the routes that start and join rooms, controlled by the `genesis` [setting](settings.md). `off`, the default, removes them. `local`, which `coalitionkit up` uses, accepts only same-origin requests from this machine. With `admin`, anyone may call them, except that `GET /v1/rooms` needs the admin token and `POST /v1/genesis/start` needs a single-use `Authorization: Start <code>`. In this version no route or command issues those codes, so your own code has to call `registry.issue_start()`. **As the owner** also needs the room owner's viewer token.
- **Admin**: `Authorization: Bearer <admin token>`.
- **Open**: no token.

Requests that change something must be sent as `application/json`. `/v1/room/voice` and `/v1/room/photo` change nothing: they take the clip or the photo as it is and only read it.

## Follow a room

| Route | Access | What it does |
|---|---|---|
| `GET /v1/feed` | Viewer | The [room feed](room-feed.md), as server-sent events |
| `GET /v1/agent` | Viewer | The viewer's own agent stream, as server-sent events |
| `GET /v1/view-as?participant=` | Viewer | A view of the room as another member sees it, with what is private to them hidden |
| `POST /v1/agent/answers` | Viewer | Answer a consent: `{interrupt_id, consent, choice?}` |
| `POST /v1/agent/offer` | Viewer | Make an offer by hand |
| `GET`, `POST /v1/agent/vault` | Viewer | Read or fill the viewer's hosted vault |

A tree in the room can never answer a consent. Consent only goes through `/v1/agent/answers`.

## Work in a room

| Route | Body | Answer |
|---|---|---|
| `POST /v1/room/begin` | `{helpers}` | `{phase}`. 403 unless the viewer is the owner |
| `POST /v1/room/brief` | `{question_id, value}` or `{question_id, skip: true}` | `{status}`. 422 if the value does not fit the question |
| `POST /v1/room/say` | `{text, via?}`, up to 500 characters; `via` is `typed` (default), `voice` or `photo` | `{route, reply, event_id?, stopped?}` |
| `POST /v1/room/voice` | A mono 16-bit PCM WAV, 16 or 24 kHz, at most 20 seconds: the raw body (`Content-Type: audio/wav`) or a multipart part `audio`. Optional `question_id` | `{text, ms, source}`, plus `{answer, words, question_id, answer_source}` for a question. 413 for a long clip, 422 for another format, 503 without a model key |
| `POST /v1/room/photo` | A PNG, JPEG or WebP image: the raw body or a multipart part `image`, with `question_id` or `purpose=say` | `{answer, words, description, ms, source}`. 415 for another image type |
| `POST /v1/room/done` | `{task_id}` | `{seq}`. 409 unless the viewer's approved commitment has a result |

All four need a viewer token.

## Start, join and end

| Route | Access | What it does |
|---|---|---|
| `GET /v1/rooms` | Start | The rooms and their state |
| `GET /v1/packs` | Start | The installed packs |
| `POST /v1/genesis/draft` | Start | Draft a charter from a sentence |
| `POST /v1/genesis/start` | Start | Start a room from a draft |
| `POST /v1/invitations` | Start, as the owner | Create an invitation |
| `DELETE /v1/invitations/{identifier}` | Start, as the owner | Withdraw an invitation |
| `POST /v1/invitations/accept` | Start | Accept an invitation |
| `POST /v1/coalition/dissolve` | Start, as the owner | End the room |
| `GET /v1/coalition/door` | Start, as the owner | The door's code and who is knocking |
| `POST /v1/coalition/door/stop` | Start, as the owner | Close the door |
| `POST /v1/coalition/door/knocks/{knock}` | Start, as the owner | Let a knock in, or refuse it |
| `GET /v1/door/{code}` | Start | The goal and the open seats behind a code |
| `POST /v1/door/join` | Start | Take a seat: `{code, role, card_url?, card?}` |
| `POST /v1/rooms/{room}/knock` | Start | Knock on a room |
| `GET /v1/rooms/{room}/knocks/{knock}?secret=` | Start, with the secret the knock returned | Whether a knock was let in |
| `POST /v1/confirm/redeem` | Viewer | Use a confirm code from a WhatsApp link, and get the consent to show |

## Agents

| Route | Access | What it does |
|---|---|---|
| `/mcp` | Viewer, or OAuth | The [MCP server](mcp.md) |
| `POST /a2a` | Signed messages | A2A over JSON-RPC. See [the protocol](protocol.md) |
| `GET /.well-known/agent-card.json` | Open | The host's signed card |
| `GET /cards/{coalition}/{participant}` | Open | A hosted member's card |
| `POST /invitations/redeem` | Invitation | Redeem an invitation with a signed card: `{invitation, card_url, card}` |

## Operators

| Route | Access | What it does |
|---|---|---|
| `GET /healthz` | Open | Whether the host is up |
| `GET /admin/status` | Admin | Host status |
| `POST /admin/coalitions` | Admin | Create a coalition from a charter |
| `POST /admin/coalitions/{coalition}/invitations` | Admin | Invite a participant |
| `POST /admin/coalitions/{coalition}/connectors` | Admin | Issue invitations for a pack's connectors |
| `POST /admin/coalitions/{coalition}/host-events` | Admin | Send a host message. It goes through every normal check |
| `POST /admin/whatsapp/invitations` | Admin | Invite a member over WhatsApp |
| `GET`, `POST /webhooks/whatsapp` | Meta's signature | The [WhatsApp](../guides/whatsapp.md) webhook |
