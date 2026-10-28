# ADR 014: In-process bus, log read from per-subscriber cursors

Status: Accepted (supersedes ADR 005 for v0.1)

## Decision

An in-process bus wakes subscribers, and each subscriber reads the Postgres log from its own cursor

## Why

v0.1 is one process; order must come from the log, never from a pub/sub bus

## Rejected alternatives

NATS JetStream in v0.1
