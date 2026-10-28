# ADR 013: Live state as a host-written JSON document with patches

Status: Accepted (supersedes ADR 003)

## Decision

Live state is a JSON document per Coalition, written only by the host, projected per viewer and streamed as RFC 6902 patches

## Why

The host is the only writer, so a CRDT adds nothing, and a shared CRDT document would give every browser data outside its scope

## Rejected alternatives

A Yjs document synced to browsers (kept for shared free text after v0.1)
