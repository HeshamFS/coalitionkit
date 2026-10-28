# ADR 018: Owner-signed consent

Status: Accepted

## Decision

Owner authority is separate from agent authority. At join, `owner_proof` binds an Ed25519 owner key (a JWK) to the participant and the host pins it. Every `coalition.decide` carries `decided_at` and `consent_sig`, a compact JWS by the owner key over the JCS form of `{coalition_id, subject, choice, consent, decided_at}`. The agent's envelope signature alone never makes a decision count. Through MCP, the server's hosted owner key signs a decision only after the person answers an MCP elicitation for that exact subject and revision.

Decisions are recorded per decider (first answer wins per coalition, subject kind, subject ID, revision and decider) against one subject shape `{kind, id, revision}`, and a subject is decided when every named decider has consented.

## Why

A compromised or over-eager agent, or a model that sets a confirmation flag, would otherwise be able to consent for a person. Keeping the signing key out of the agent's reach, and binding each consent to the exact subject, revision and time, makes a decision evidence of what a person actually approved and prevents replay on another subject or Coalition.

## Rejected alternatives

- Trusting the agent's envelope signature for decisions (the agent is the thing being constrained).
- A confirmation flag in the tool arguments (a model or an MCP App view can set it).
- Using one key for agent and owner (no separation, and rotation of one breaks the other).
