# Compared sets

A pack can name private sets the room compares without anyone showing their list. Each person picks or types their own values, the values stay in their vault, and the room learns only what everyone shares, or only how many.

```yaml
compare:
  - id: colours
    label: Colours everyone likes
    question:
      text: "Which of these wall colours would you be happy with?"
      kind: choice
      options: [white, grey, sage green, sky blue, sunny yellow]
      why: "Only the colours everyone picked are shown."
    mode: overlap
  - id: tools
    label: Tools in common
    question: { text: "Which tools do you own? Separate them with commas.", kind: text }
    mode: count
    min_seats: 2
```

## The keys

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | Lowercase letters, digits and hyphens, starting with a letter, at most 32. Distinct within the pack |
| `label` | yes | The words the Table shows above the result, at most 60 characters |
| `question.text` | yes | What every seated person is asked, at most 140 characters |
| `question.kind` | yes | `choice` (pick any of the options), `slots` (the room's time slots) or `text` (a short list separated by commas) |
| `question.options` | for `choice` | Two to twelve distinct options, each at most 60 characters. `slots` and `text` take none |
| `question.why` | no | One line under the question. A default line says only shared values are shown |
| `mode` | no | `overlap` (default) publishes the shared values; `count` publishes only how many there are |
| `min_seats` | no | How many seats must give values before the room compares, at least 2. Default: every seated person |

A pack declares at most four sets. `amount` is refused, because a set is matched value by value; to compare amounts, list them as `choice` options. The loader names the rule a bad entry breaks, for example *a compared set needs values to match one by one; an amount is one number*.

## What happens in the room

1. **Asked.** When the room begins, each person's brief holds their agent's own questions and then one question per set. A `choice` set lets the person pick any number of options. The answer stays in that seat's vault.
2. **Compared.** After the offers, for each set, the host asks each vault only whether it holds values (`coalition.query` and `coalition.answer`). The first seat that does then meets each of the others in turn in a blinded intersection (`coalition.match` setup, request and response), over strings such as `colours:sage green`. Only the running overlap goes forward.
3. **Published.** One `coalition.observe` with `source: "document"` carries the result to the whole room:

    ```json
    {"common": 1, "set": "colours", "values": ["sage green", "sky blue"], "compared": 3}
    {"common": 1, "set": "tools", "count": 2, "compared": 2}
    ```

    With fewer seats than `min_seats`, nothing is published and the room moves on.
4. **Used.** The Table shows each set under *Found in common, privately*, and each person sees how many of their own values stayed private. Plans are named with the shared sets in view, and a result maker is told to choose only from the shared values. A made thing that names one of the set's options outside them is sent back to be made again.

The feed keys are `room.sets` and `room.mine.sets`; see [Room feed](../../reference/room-feed.md).

## Agents brought over MCP

A seat whose own agent acts over MCP is not asked the brief. Its agent gives the values itself by writing the vault key `compare:<id>` through `POST /v1/agent/vault` with the seat's viewer token:

```json
{"values": {"compare:colours": ["sage green", "sky blue"]}}
```

For a `choice` set only the pack's own options count, matched without regard to case; anything else is dropped. A `text` set takes the values as they are, trimmed and lowercased. The host never shows the values back: `GET /v1/agent/vault` lists keys only.

There is no MCP tool for this yet, so an agent needs the HTTP route beside its MCP connection.

## Choosing the mode

Use `count` when the values themselves are sensitive and the number is enough, for example how many people own a ladder. Count hides the values from the room. It does not hide them from the host: the hosted vaults compare on the host, and only the number leaves it. See [Vault and PSI](../../concepts/vault-and-psi.md) for the limits.

## Public questions

Some answers are meant for everyone, such as the city a person is in. A pack declares those under `public:`, beside `compare:`. Each seated person is asked the question in their brief, and when they answer, the room sees it as a message from their seat, such as *City: Lisbon*.

```yaml
public:
  - id: city
    label: City
    question: { text: "Which city are you in?", kind: text }
    why: "Everyone in the room sees your city, and your agent searches the web for a stop there."
    search: true
```

| Key | Required | Meaning |
|---|---|---|
| `id`, `label` | yes | Same rules as a compared set. The label starts the published message |
| `question` | yes | `text` or `choice` with its options |
| `why` | no | The line under the question. The default says everyone in the room sees the answer |
| `search` | no | `true` adds the answer to that seat's web search on `place` needs |

A pack declares at most two public questions. With `search: true`, each seat that offers on a `place` need searches once with the need's title and its own answer only, for example *A must-see place in each city in Lisbon*, and the hits of every seat are kept together, each page title ending with the place in brackets. The result maker is told to choose one place for each person. Because the answer is published, web search does not refuse a query for holding it.

An agent brought over MCP gives its answer by writing the vault key `public:<id>` (a string) through `POST /v1/agent/vault`. The [world tour pack](https://github.com/HeshamFS/coalitionkit/tree/main/packs/world-tour) uses one public question for the city.
