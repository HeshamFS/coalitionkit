# ADR 016: Derived outputs take the narrowest scope

Status: Accepted

## Decision

Every derived output takes the narrowest scope of its sources

## Why

Plans, summaries and lessons would otherwise leak private facts to later readers

R2: a source with a redaction list makes the derived output host-only unless the output is built from the source's redacted projection. Redaction paths name fields of one event and do not survive renaming, so they are never carried into a derived scope.

## Rejected alternatives

Scoping raw events only
