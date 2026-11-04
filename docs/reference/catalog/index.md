# Component catalog

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

A surface is built only from these 201 components. The catalog is closed: a renderer refuses any other catalog ID, and a tree that names an unknown component is refused. Raw HTML is forbidden.

A tree has at most 500 components, 24 levels deep. A number on screen is bound as `{value, event_ref}`, pointing at the event it came from.

The source is [`spec/catalog/coalitionkit-v0_9.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/catalog/coalitionkit-v0_9.json).

| Family | Components |
|---|---|
| [Foundations](family-01.md) | 58 |
| [Shell, doors and templates](family-02.md) | 19 |
| [Conversation and calls](family-03.md) | 16 |
| [Forms and flows](family-04.md) | 14 |
| [Coalition and people](family-05.md) | 14 |
| [Needs, offers, tasks and plans](family-06.md) | 15 |
| [Places and time](family-07.md) | 9 |
| [Privacy and consent](family-08.md) | 16 |
| [Live and proof](family-09.md) | 18 |
| [Mint and machines](family-10.md) | 9 |
| [Channels, ending and memory](family-11.md) | 13 |
