# ADR 015: Consents are durable records

Status: Accepted

## Decision

Consents are durable records on the host with a first-answer-wins update; AG-UI interrupts only show them

## Why

A consent outlives any viewer's connection, and an interrupt ends its run

## Rejected alternatives

Holding an AG-UI run open until the person answers
