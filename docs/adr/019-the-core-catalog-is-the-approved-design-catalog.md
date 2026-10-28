# ADR 019: The core catalog is the approved design catalog; discipline views live in packs

Status: Accepted

## Decision

`coalitionkit/v0_9` is defined by `spec/catalog/coalitionkit-v0_9.json`: the 201 generic components of the approved design catalog (11 families), each with typed props (type, required, enum values), events, states and doors, in the format the host validator enforces. Consent components bind a revisioned subject and a decision deadline; vault values never travel in a tree. Components that only make sense for one discipline (for example a scientific field map or a departure board) are not part of the core catalog; a Discipline Pack ships them as a pack catalog extension, accepted only while the pack is active, and never replacing or renaming a core component.

Doors are now six: wide, compact, message, voice, lens and mcp-app.

## Why

The spec's table of 13 components could not express the surfaces the protocol needs (consent, privacy, live proof, calls, places, the shell), and agents compose only from what the catalog allows. Keeping discipline views out of the core keeps the kit domain-agnostic: every scenario plugs in from outside, through packs and case studies.

## Rejected alternatives

Keeping the 13-component table and letting renderers add components freely (generated or unlisted components would reach screens); putting discipline views in the core catalog behind a flag (the core would carry discipline vocabulary).
