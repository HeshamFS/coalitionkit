# Results

A **result** is the real thing a need asked for: a budget that adds up, a list, a message to send, a poster. It is an event in the log, signed by the agent that made it, and the Steward reviews it like any other message.

## How one is made

1. A person holds to commit to their part.
2. Their agent makes the content with a model. Code checks it: a budget must add up to the amount stated, and a draft may not claim an agreement nobody made.
3. The composer lays it out from the [closed catalog](generative-ui.md). If that layout fails its checks, or shows ids or empty values, a fixed layout is used.
4. **Mark done** is the person's own click. A helper reports its own work.

## Kinds and exports

| Kind | Holds | Shown as | Export |
|---|---|---|---|
| `place` | Kinds of place, why each fits, what to check first | Cards | None |
| `schedule` | Ordered steps, with times | `Timeline`, in the viewer's own time | ICS |
| `budget` | Lines, who pays, how it is shared, and the time people offered | `CostSplit`, in the goal's currency | CSV |
| `list` | Items and who brings each | `Checklist` | CSV |
| `draft` | A subject and a body | A card with the message | Text |
| `image` | A picture, its alt text and the prompt it was drawn from | `Image` | The picture file |

## Pictures

The Gardener makes a need of kind `image` only when the goal asks for a picture, such as a poster, a card, an invitation or a menu. Code turns any other picture it proposes into a draft, so no image is drawn unasked.

The agent that holds the need writes the prompt from the room's public facts only: the goal, the need's title and its detail. No answer from a brief, no vault value and no name goes in. Before the prompt leaves the host it passes the Steward's deterministic policies as if it were a message to the whole room; if one matches, nothing is drawn, the stop is written down, and the result says so and keeps the prompt.

The image model (`muse-image-1.0`) answers with a picture. The host keeps it under its data directory, named by the SHA-256 of its bytes, and serves it to the room's viewers at `GET /v1/room/media/{hash}`. The result holds `{hash, alt, prompt, width, height}`. **Show the work** shows the prompt, and **Download picture** saves the file. With no image key, or when the call fails, the result says why and keeps the prompt.

## What to trust

Each result says whether it came from the model or from rules, and what it builds on is labelled **estimate** when it is a suggestion. **Show the work** shows the tree, the events it came from and the check it passed.

The agent does not know things it cannot check. Hosted agents suggest kinds of place, not named venues, because they do not search the web. An outside agent writes what it likes: a venue it names may not exist. The Steward checks policy, not truth.

## Who can publish

A result counts only from the seat holding that need's approved commitment when it was sent. Nobody can publish over another seat's work, and a former assignee cannot publish over the current one. What they made while they held the need stays in the record.

An outside agent may send only its data with no layout, and it is shown in the fixed layout.

## After the room

Results live in your browser tab after the room ends. Copy or export what you want before you leave.
