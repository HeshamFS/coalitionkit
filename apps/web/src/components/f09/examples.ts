// SPDX-License-Identifier: Apache-2.0

import type { Props } from "../f08/shared";
import { stateProps } from "../f08/stateProps";

type Example = {
  name: string;
  props: string;
  events: string;
  states: { state: string; props: Props }[];
};
const drawn: Example[] = [
  {
    name: "ActivityStream",
    props: "filter, items",
    events: "item.open(seq)",
    states: [
      {
        state: "default",
        props: {
          filter: "all",
          items: [
            {
              actor: { label: "Member A" },
              verb: "updated",
              object: "Task 3",
              time: "now",
              seq: { value: 41, event_ref: "example:1" },
              live: true,
              aboutMe: true,
            },
            {
              actor: { label: "Member B" },
              verb: "accepted",
              object: "Plan A",
              time: "2 min",
              seq: { value: 42, event_ref: "example:1" },
              decision: true,
            },
          ],
        },
      },
    ],
  },
  {
    name: "CanvasPresence",
    props: "cursors",
    events: "display only",
    states: [
      {
        state: "acting",
        props: {
          cursors: [
            { actor: "Planner", kind: "agent", target: "Plan B", verb: "comparing" },
            { actor: "Member A", kind: "person", target: "Task 3", verb: "editing" },
          ],
        },
      },
    ],
  },
  {
    name: "ChainView",
    props: "entries, genesis",
    events: "chain.verify",
    states: [
      {
        state: "intact",
        props: {
          genesis: "0000…",
          entries: [
            {
              seq: { value: 39, event_ref: "example:1" },
              type: "decide",
              actor: "Member A",
              prev_hash: "a8c1…",
              hash: "8f2e…",
              verified: true,
            },
            {
              seq: { value: 40, event_ref: "example:1" },
              type: "decide",
              actor: "Member A",
              prev_hash: "a8c1…",
              hash: "8f2e…",
              verified: true,
            },
            {
              seq: { value: 41, event_ref: "example:1" },
              type: "decide",
              actor: "Member A",
              prev_hash: "a8c1…",
              hash: "8f2e…",
              verified: true,
            },
          ],
        },
      },
    ],
  },
  {
    name: "ChangedValue",
    props: "after, before, path",
    events: "display only",
    states: [
      { state: "flash", props: { before: "16:00", after: "17:00", path: "/tasks/t2/time" } },
    ],
  },
  {
    name: "ConnectionStatus",
    props: "feed, latencyMs, run",
    events: "feed.reconnect",
    states: [
      {
        state: "live",
        props: { feed: "live", latencyMs: { value: 82, event_ref: "example:1" }, run: "r1" },
      },
      {
        state: "reconnecting",
        props: {
          feed: "reconnecting",
          latencyMs: { value: 82, event_ref: "example:1" },
          run: "r1",
        },
      },
      {
        state: "offline",
        props: { feed: "offline", latencyMs: { value: 82, event_ref: "example:1" }, run: "r1" },
      },
    ],
  },
  {
    name: "ErrorNotice",
    props: "code, detail, ref",
    events: "error.retry?",
    states: [
      {
        state: "shown",
        props: {
          code: "stale_subject",
          detail: { message: "Review the latest revision.", retry: true },
          ref: "e1",
        },
      },
    ],
  },
  {
    name: "EventRow",
    props: "form, seq, summary, type",
    events: "entry.open",
    states: [
      {
        state: "original",
        props: {
          seq: { value: 41, event_ref: "example:1" },
          summary: "Member A accepted Plan A",
          type: "decide",
          form: "original",
        },
      },
      {
        state: "projection",
        props: {
          seq: { value: 41, event_ref: "example:1" },
          summary: "Member A accepted Plan A",
          type: "decide",
          form: "projection",
        },
      },
      {
        state: "receipt-only",
        props: {
          seq: { value: 41, event_ref: "example:1" },
          summary: "Member A accepted Plan A",
          type: "decide",
          form: "receipt-only",
        },
      },
    ],
  },
  {
    name: "EvidenceCard",
    props: "captured_at, kind, masks, ref, task, verified_by",
    events: "evidence.open",
    states: [
      {
        state: "default",
        props: {
          kind: "Image",
          captured_at: "10:41",
          ref: "evidence:1",
          task: "Task 3",
          verified_by: "Member A",
          masks: [],
        },
      },
    ],
  },
  {
    name: "GardenerThinking",
    props: "actor, steps",
    events: "display only",
    states: [
      {
        state: "running",
        props: {
          actor: "Planner",
          steps: [
            { name: "Read constraints", state: "done", took: { value: 2, event_ref: "example:1" } },
            { name: "Try candidates", state: "done", took: { value: 8, event_ref: "example:1" } },
            {
              name: "Check every member",
              state: "running",
              took: { value: 4, event_ref: "example:1" },
            },
          ],
        },
      },
    ],
  },
  {
    name: "LiveDocks",
    props: "docks",
    events: "dock.open(ref)",
    states: [
      {
        state: "default",
        props: {
          docks: [
            { icon: "clock", label: "Next", value: "17:00", ref: "t3" },
            { icon: "people", label: "Live", value: "3 members", ref: "members" },
          ],
        },
      },
    ],
  },
  {
    name: "LogStream",
    props: "entries, filter",
    events: "entry.open(seq)",
    states: [
      {
        state: "default",
        props: {
          entries: [
            {
              seq: { value: 39, event_ref: "example:1" },
              ts: "10:42",
              type: "decide",
              actor: "Member A",
              summary: "Plan A accepted",
              hash: "8f2e…",
              form: "projection",
            },
            {
              seq: { value: 41, event_ref: "example:1" },
              ts: "10:42",
              type: "decide",
              actor: "Member A",
              summary: "Plan A accepted",
              hash: "8f2e…",
              form: "original",
            },
            {
              seq: { value: 42, event_ref: "example:1" },
              ts: "10:42",
              type: "decide",
              actor: "Member A",
              summary: "Plan A accepted",
              hash: "8f2e…",
              form: "projection",
            },
          ],
          filter: [],
        },
      },
    ],
  },
  {
    name: "MediaWithMasks",
    props: "frame, hidden, labels, masks, media_ref",
    events: "mask.label(id, label)",
    states: [
      {
        state: "loading",
        props: {
          media_ref: "vault:media",
          frame: { value: 42, event_ref: "example:1" },
          hidden: [],
          masks: [
            { id: "m1", label: "display", score: { value: 0.98, event_ref: "example:1" } },
            { id: "m2", label: "control", score: { value: 0.94, event_ref: "example:1" } },
          ],
          labels: [{ mask: "m1", label: "display" }],
        },
      },
    ],
  },
  {
    name: "ProvenanceTag",
    props: "kind, source",
    events: "display only",
    states: [
      { state: "measured", props: { kind: "measured", source: "e1" } },
      { state: "vault", props: { kind: "vault", source: "e1" } },
      { state: "signed", props: { kind: "signed", source: "e1" } },
      { state: "model", props: { kind: "model", source: "e1" } },
      { state: "estimate", props: { kind: "estimate", source: "e1" } },
    ],
  },
  {
    name: "ReceiptBadge",
    props: "seq, state",
    events: "receipt.verify",
    states: [
      { state: "ok", props: { seq: { value: 41, event_ref: "example:1" }, state: "ok" } },
      { state: "bad", props: { seq: { value: 41, event_ref: "example:1" }, state: "bad" } },
      { state: "pending", props: { seq: { value: 41, event_ref: "example:1" }, state: "pending" } },
    ],
  },
  {
    name: "RippleBanner",
    props: "ripple",
    events: "ripple.open",
    states: [
      {
        state: "shown",
        props: {
          ripple: {
            by: "Member B",
            change: "moved Task 2 to 17:00",
            invalidated: ["t2", "t3"],
            untouched: ["t1", "t4", "t5"],
          },
        },
      },
    ],
  },
  {
    name: "StepProgress",
    props: "eta, measured, planned, progress, task",
    events: "display only",
    states: [
      {
        state: "running",
        props: {
          task: "Task 3",
          eta: "11:30",
          progress: { value: 0.64, event_ref: "example:1" },
          measured: [
            { t: "10:00", value: { value: 20, event_ref: "example:1" } },
            { t: "10:30", value: { value: 64, event_ref: "example:1" } },
          ],
          planned: [
            { t: "10:00", value: { value: 20, event_ref: "example:1" } },
            { t: "11:00", value: { value: 100, event_ref: "example:1" } },
          ],
        },
      },
    ],
  },
  {
    name: "StewardVerdict",
    props: "verdict",
    events: "verdict.verify",
    states: [
      {
        state: "allow",
        props: {
          verdict: {
            event_id: "e1",
            revision: { value: 2, event_ref: "example:1" },
            action: "redact",
            policy_id: "no-contact-before-consent",
            redact: ["payload.contact"],
            explain: "Contact is private until consent",
            model_audited: true,
            issued_at: "10:42",
            sig: "sig:example",
          },
        },
      },
    ],
  },
  {
    name: "VerifyPanel",
    props: "checks, export",
    events: "verify.run, log.download",
    states: [
      {
        state: "running",
        props: {
          checks: [
            { name: "Hash chain", state: "passed", detail: "verified" },
            { name: "Host signatures", state: "passed", detail: "verified" },
            { name: "Projection links", state: "passed", detail: "verified" },
            { name: "Receipts", state: "passed", detail: "verified" },
          ],
          export: { log: "log:1", receipts: ["r1"], host_key: "example" },
        },
      },
    ],
  },
];

const states: Record<string, string[]> = {
  ActivityStream: ["default"],
  CanvasPresence: ["acting", "idle"],
  ChainView: ["intact", "broken"],
  ChangedValue: ["flash", "tinted", "seen"],
  ConnectionStatus: ["live", "reconnecting", "offline"],
  ErrorNotice: ["shown"],
  EventRow: ["default", "selected"],
  EvidenceCard: ["default", "masked"],
  GardenerThinking: ["running", "done", "failed"],
  LiveDocks: ["default"],
  LogStream: ["default", "gap"],
  MediaWithMasks: ["loading", "ready"],
  ProvenanceTag: ["default"],
  ReceiptBadge: ["ok", "bad", "pending"],
  RippleBanner: ["shown", "dismissed"],
  StepProgress: ["running", "deviating", "done"],
  StewardVerdict: ["allow", "redact", "block", "quarantine", "escalate"],
  VerifyPanel: ["running", "passed", "failed"],
};

export const examples: Example[] = drawn
  .map((example) => ({
    ...example,
    states: [
      ...example.states,
      ...(states[example.name] ?? [])
        .filter((state) => !example.states.some((s) => s.state === state))
        .map((state) => ({ state, props: { ...example.states[0]?.props } })),
    ],
  }))
  .map((example) => ({
    ...example,
    states: example.states.map((s) => ({
      ...s,
      props: stateProps(example.name, s.state, s.props),
    })),
  }));
