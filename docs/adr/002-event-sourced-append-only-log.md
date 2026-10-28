# ADR 002: Event-sourced append-only log

Status: Accepted

## Decision

Event sourcing: an append-only Postgres log is the source of truth

## Why

Replay, audit, recovery and the consent trail come for free

## Rejected alternatives

State-only database rows
