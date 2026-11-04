# Coalition and room

A **Coalition** is a short-lived group of people and agents working on one goal. A **room** is the same thing as people experience it. The protocol says Coalition. The screen says room.

## The charter

Every Coalition starts with a **charter**: the goal, the roles, the people who must decide, and the deadline. The room reads your sentence and drafts one. You check it before anything is public.

The charter has a revision number. Changing who decides makes a new revision, and everyone is asked again.

## The host

The **host** runs the room. It keeps one signed, append-only log per Coalition and gives each member a live view of only what they may see. A host can run many rooms.

The kit's reference host runs on your computer with `coalitionkit up`, or on a server with `coalitionkit server serve`. Others can implement the [protocol](../reference/protocol.md) and check themselves with the [conformance runner](../reference/conformance.md).

## Stages

| Stage | Means |
|---|---|
| Gather | People take seats and accept the charter |
| Negotiate | Agents make offers and compare |
| Decide | Plans wait for a yes |
| Act | The chosen plan's people commit |
| Live | Work is being done and reported |
| Dissolve | The room has ended |

A change can send part of the room back a stage. See [Ripple and change](ripple-and-change.md).

## A room ends

A room ends when its owner ends it or its deadline passes. Nothing about it is meant to last except what the people take with them. See [Dissolve](dissolve.md).
