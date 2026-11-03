# 020. Hosted rooms run on their own

**Status:** accepted, 2026-11-03.

**Context.** A web room stalled after its first need. The agents that made offers and did work lived in the demo script, so a real room had nobody acting in it. The model composed nothing inside the room, and the per-viewer surface line had no production caller.

**Decision.** The server runs a room engine for hosted seats. It drives the existing protocol as members and as the host would: needs, offers, queries, match rounds, proposals, commitments and evidence. It adds no event types. A result is a `coalition.observe` with source `document`, cited by `coalition.done` evidence, so results are signed, reviewed and in the chain. A helper agent is an ordinary hosted member that labels itself, holds its own keys and is never a decider. When seats stay open, the owner may begin; the host then issues a charter revision naming the seated people as deciders.

**Consequences.** Real rooms do real work with or without a pack. Live state that is not a log event, such as agent steps and private notes, travels as a per-viewer `room` key on the feed and carries no authority. The server keeps holding a hosted member's owner key, as it already did for web rooms; the screen must say so plainly rather than imply a key on the device. This change moves the core freeze tag.
