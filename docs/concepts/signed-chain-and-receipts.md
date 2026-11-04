# Signed chain and receipts

Everything that happens in a room is an entry in one append-only log. Entries are linked by hashes, so changing any entry breaks every link after it.

## An entry

The sender signs an envelope: who sent it, on whose behalf, who may see it, and the payload. The host accepts it, gives it a sequence number and a time, links it to the previous entry, and writes it to the log. Nothing is edited or removed from the log afterwards, except that a room's end erases what the room says it erases.

## Receipts

A **receipt** is the host's signed statement that the log reached a given length with a given head hash. Once you hold one, the host cannot quietly rewrite what came before it without being caught.

## What you may see

You see the entries your scope allows. Each other entry reaches you as a stub: only its number and hashes. Your chain still links end to end, so you can check it without seeing other people's private messages.

Anything delivered with a field removed is a **projection**, signed by the host rather than the sender, so nobody is shown a changed message under the sender's name.

## What it proves

The chain proves who signed what, in what order, and that it has not changed since. It does not prove a statement is true. It also cannot prove what happened outside the room.

The format is in [the protocol](../reference/protocol.md). To check a chain yourself, see [Browser verification](browser-verification.md).
