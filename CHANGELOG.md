# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Coalition Protocol v0.1 draft text, JSON Schemas (2020-12), and shared test vectors.
- `coalitionkit-contracts`: Pydantic models, JCS canonicalisation, EdDSA JWS signing, ULIDs and schema validation.
- `tools/check.py`: the one checks command.
- Spec revision R1: authenticated projections and receipts (ADR 017), owner-signed consent (ADR 018), authenticated idempotency (`duplicate_mismatch`), a target authorization matrix (`not_authorized`), per-decider decisions, one subject shape with host-assigned revisions, per-task flow, scope intersection with `spec/vectors/scope.json`, the PSI wire format and threat model, MCP `commit`, `report_ripple` and `accept_charter`, charter acceptance, the authenticated log boundary with `spec/vectors/log.json`, and fixed identifiers.
- `coalitionkit-contracts`: `consent`, `owner`, `idempotency`, `revisions`, `decisions`, `log` and `scope_resolve` modules; `coalition.projection` and `coalition.receipt` (eighteen message types).

- Spec revision R2 (second review): see `spec/OPEN-QUESTIONS.md` R2-1 to R2-10 and H1 to H3. New wire fields: `match.task_id` (required), `tension.task_ids` and `tension.decision_deadline` (required), `propose.decision_deadline` (required), `query.task_id` (optional), `projection.source.prev_hash` and `.hash` (required). Members now mint `commitment_id`.
- `coalitionkit-contracts`: `lifecycle` (task status table, commitment states, decision deadline), `delivery_form`, `projection_stub`, `verify_projection`, `tally_choice`, `ScopeSource.projected`; `resolve_narrowest` now never returns a `redact` list. `coalitionkit-vault`: `Context.task_id`.
- The core A2UI catalog `coalitionkit/v0_9` is now `spec/catalog/coalitionkit-v0_9.json` (202 generic components in 11 families, six doors); discipline views move to pack catalog extensions (ADR 019).

### Security

- Owner-signed consent now names the participant (`{coalition_id, participant, subject, choice, consent, decided_at}`). `consent_payload`, `sign_consent` and `verify_consent` take a required `participant=`; `verify_decision` uses the envelope's `on_behalf_of`. Added `jwk_thumbprint` and `check_owner_key_unique`; the host rejects a join whose owner key is already pinned to another participant (`not_authorized`).
