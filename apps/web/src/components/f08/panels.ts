// SPDX-License-Identifier: Apache-2.0
export const panels: Record<
  string,
  { title: string; props: string; badge?: string; tone?: string; doors?: string[] }
> = {
  VaultCard: {
    title: "what you keep",
    props:
      "categories[] {name, count, policy: answer-only | psi | masked | never} · answers today · location: device | self-hosted · export | wipe",
    tone: "vault",
    badge: "on your device",
  },
  DisclosureLadder: {
    title: "how much a question can learn",
    props:
      "field · level: none | bool | range | exact · buckets? · per-audience override · going up = a consent; going down applies at once",
  },
  PrivateField: {
    title: "in any form",
    props:
      "value (vault) · disclose policy chip · masked on screen by default · reveal timer · screenshots of the field are blurred on devices that allow it",
  },
  OverlapView: {
    title: "private matching you can watch",
    props:
      "parties[] · mode: intersection | count-only (charter count_trusted) · inputs (local) · tokens (shown truncated) · result · run id → log",
    tone: "measured",
    badge: "PSI · ristretto255",
  },
  WhatOthersKnow: {
    title: "about you",
    props:
      "rows[] {participant, knows[], notKnows[], because (scope | answer | rule)} · computed by the host from deliveries to that participant",
  },
  ScopeBadge: {
    title: "every audience",
    props:
      "audience · redact[] paths · resolved principals on hover · narrowest-of-sources for derived outputs (C-16)",
  },
  ProjectionNote: {
    title: "you see a version",
    props:
      "source {event_id, seq, prev_hash, hash} · removed paths (count, not content) · viewer-specific? · verify → WiringDrawer",
  },
  RedactionDiff: {
    title: "for the sender",
    props:
      "original (sender only) · delivered · verdict {action, policy_id, paths} · appeal → organizer review",
  },
  CanaryMonitor: {
    title: "privacy test",
    props:
      "runs · canaries · surfaces scanned[] · found (must be 0) · last run · measured values only",
    tone: "measured",
    badge: "test 2",
  },
  ConsentCard: {
    title: "a plan to decide",
    props:
      "subject {kind, id, revision} · summary · yourPart · cost · consequenceOfNo · decision_deadline · actions: yes | no | compare · → owner-signed decide",
    doors: ["wide", "compact", "message", "voice"],
  },
  VoteTally: {
    title: "counts, not names",
    props:
      "deciders[] · answered (count while open) · answers (names after close) · rule · outcome: decided | refused | split | expired",
  },
  StaleNotice: {
    title: "it changed while you read",
    props:
      "subject · yourRevision · currentRevision · diff[] · host error stale_subject → this card, never a silent retry",
  },
  CommitmentCard: {
    title: "every state",
    props:
      "commitment_id (member ULID) · task · assignee · status: pending | approved | suspended | withdrawn | superseded · due · approve/withdraw → owner-signed",
  },
  ApprovalButton: {
    title: "one tap",
    props:
      "subject · memberel · consequence (required) · disabledReason · on lens: money never confirms on glasses",
    doors: ["compact", "lens"],
  },
  DurableConsent: {
    title: "standing permissions",
    props:
      "grants[] {grantee, action, scope, expires, signed} · pending requests · revoke → owner-signed · narrowest scope by default (ADR 016)",
    tone: "signed",
    badge: "ADR 015",
  },
  DecisionLog: {
    title: "who decided what",
    props:
      "entries[] {time, participant, subject, revision, answer, reason?, seq, verified} · filter by subject · each row opens the signed decide",
  },
};
