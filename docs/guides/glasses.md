# Glasses view

Two routes draw the room for a small display.

- **`/glasses`** shows the viewer's current step only: one card, one step. If something waits for their decision, it shows that first.
- **`/lens`** shows the current view in the lens layout.

Both use the same [feed](../reference/room-feed.md) and the same viewer token as the web room. Open them in the browser on the device, signed in as that member.

Components carry a `doors` list in [the catalog](../reference/catalog/index.md), which says where each one can be drawn: `wide`, `compact`, `message` or `voice`.

!!! note
    These are web pages sized for a small display. The kit has no app for any particular pair of glasses.
