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
    name: "AttackTests",
    props: "tests",
    events: "tests.rerun",
    states: [
      {
        state: "running",
        props: {
          tests: [
            {
              name: "setpoint outside 20–1 200 units refused",
              kind: "bounds",
              state: "passed",
              log: "log:1",
            },
            {
              name: "prompt injection in a reading ignored",
              kind: "injection",
              state: "passed",
              log: "log:1",
            },
            { name: "no network beyond the device", kind: "egress", state: "passed", log: "log:1" },
            {
              name: "rapid toggling not rate-limited",
              kind: "rate",
              state: "failed",
              log: "log:1",
            },
            {
              name: "fails safe when the camera drops",
              kind: "failsafe",
              state: "running",
              log: "log:1",
            },
            ...Array.from({ length: 9 }, (_, i) => ({
              name: `Additional bounds check ${i + 1}`,
              kind: "bounds",
              state: "passed",
              log: `log:${i + 2}`,
            })),
          ],
        },
      },
    ],
  },
  {
    name: "CaptureCard",
    props: "masks, narration, tips, video",
    events: "capture.start, capture.stop → MintPipeline",
    states: [
      {
        state: "ready",
        props: {
          masks: [
            { label: "display", score: { value: 0.98, event_ref: "example:1" } },
            { label: "control", score: { value: 0.94, event_ref: "example:1" } },
          ],
          video: "vault:video",
          narration: "vault:audio",
          tips: ["Show the display and controls", "Explain each control"],
        },
      },
    ],
  },
  {
    name: "DeviceAlarm",
    props: "autoAction, device, duration, reading, threshold",
    events: "alarm.stop, alarm.ack",
    states: [
      {
        state: "firing",
        props: {
          device: "Device 1",
          reading: { value: 1176, event_ref: "example:1" },
          threshold: { value: 1150, event_ref: "example:1" },
          duration: { value: 120, event_ref: "example:1" },
          autoAction: "Agent lowered the value to 1140 within its bounds.",
        },
      },
    ],
  },
  {
    name: "DeviceReading",
    props: "annotations, limits, planned, series, source, unit",
    events: "reading.export",
    states: [
      {
        state: "live",
        props: {
          series: [
            {
              t: "09:30",
              value: { value: 320, event_ref: "example:1" },
              confidence: { value: 0.97, event_ref: "example:1" },
            },
            {
              t: "09:45",
              value: { value: 325, event_ref: "example:1" },
              confidence: { value: 0.97, event_ref: "example:1" },
            },
            {
              t: "10:00",
              value: { value: 650, event_ref: "example:1" },
              confidence: { value: 0.97, event_ref: "example:1" },
            },
            {
              t: "10:15",
              value: { value: 1120, event_ref: "example:1" },
              confidence: { value: 0.97, event_ref: "example:1" },
            },
            {
              t: "10:30",
              value: { value: 1149, event_ref: "example:1" },
              confidence: { value: 0.97, event_ref: "example:1" },
            },
          ],
          unit: "units",
          planned: [
            { t: "09:30", value: { value: 350, event_ref: "example:1" } },
            { t: "10:30", value: { value: 1150, event_ref: "example:1" } },
          ],
          limits: [{ value: 1200, event_ref: "example:1" }],
          annotations: ["hold starts 10:15"],
          source: "Device 1",
        },
      },
    ],
  },
  {
    name: "EdgeReaderStatus",
    props: "confidence, fallback, framesKept, rate, source",
    events: "display only",
    states: [
      {
        state: "reading",
        props: {
          source: "camera",
          rate: { value: 1, event_ref: "example:1" },
          confidence: { value: 0.97, event_ref: "example:1" },
          framesKept: "none · only numbers",
          fallback: "ask a person if < 0.8",
        },
      },
      {
        state: "low-confidence",
        props: {
          source: "camera",
          rate: { value: 1, event_ref: "example:1" },
          confidence: { value: 0.6, event_ref: "example:1" },
          framesKept: "none · only numbers",
          fallback: "ask a person if < 0.8",
        },
      },
      {
        state: "lost",
        props: {
          source: "camera",
          rate: { value: 1, event_ref: "example:1" },
          confidence: { value: 0, event_ref: "example:1" },
          framesKept: "none · only numbers",
          fallback: "ask a person if < 0.8",
        },
      },
    ],
  },
  {
    name: "MintPipeline",
    props: "cost, elapsed, stages",
    events: "stage.open(artifact)",
    states: [
      {
        state: "running",
        props: {
          stages: [
            {
              name: "capture",
              state: "done",
              took: { value: 18, event_ref: "example:1" },
              detail: "recorded",
              artifacts: ["capture:1"],
            },
            {
              name: "read",
              state: "done",
              took: { value: 14, event_ref: "example:1" },
              detail: "regions identified",
              artifacts: ["read:1"],
            },
            {
              name: "design",
              state: "running",
              took: { value: 16, event_ref: "example:1" },
              detail: "agent specification",
              artifacts: ["design:1"],
            },
            {
              name: "code",
              state: "waiting",
              took: { value: 0, event_ref: "example:1" },
              detail: "tools",
              artifacts: ["code:1"],
            },
            {
              name: "attack",
              state: "waiting",
              took: { value: 0, event_ref: "example:1" },
              detail: "bounds and failures",
              artifacts: ["attack:1"],
            },
            {
              name: "publish",
              state: "waiting",
              took: { value: 0, event_ref: "example:1" },
              detail: "owner approval",
              artifacts: ["publish:1"],
            },
          ],
          elapsed: { value: 48, event_ref: "example:1" },
          cost: "≈ €0.35 this mint",
        },
      },
    ],
  },
  {
    name: "MintedAgentCard",
    props: "agent, health, readings, tools",
    events: "agent.logs, agent.offline, agent.remint",
    states: [
      {
        state: "live",
        props: {
          agent: { name: "Device 1", version: "v2", runtime: "isolated", owner: "Member A" },
          health: "live",
          readings: [
            { name: "reading", value: { value: 1149, event_ref: "example:1" }, unit: "units" },
            { name: "setpoint", value: { value: 1150, event_ref: "example:1" }, unit: "units" },
          ],
          tools: ["read_value", "read_status", "set_value"],
        },
      },
      {
        state: "offline",
        props: {
          agent: { name: "Device 1", version: "v2", runtime: "isolated", owner: "Member A" },
          health: "offline",
          readings: [
            { name: "reading", value: { value: 1149, event_ref: "example:1" }, unit: "units" },
            { name: "setpoint", value: { value: 1150, event_ref: "example:1" }, unit: "units" },
          ],
          tools: ["read_value", "read_status", "set_value"],
        },
      },
      {
        state: "updating",
        props: {
          agent: { name: "Device 1", version: "v2", runtime: "isolated", owner: "Member A" },
          health: "updating",
          readings: [
            { name: "reading", value: { value: 1149, event_ref: "example:1" }, unit: "units" },
            { name: "setpoint", value: { value: 1150, event_ref: "example:1" }, unit: "units" },
          ],
          tools: ["read_value", "read_status", "set_value"],
        },
      },
    ],
  },
  {
    name: "PublishApproval",
    props: "coalitions, spec, tests",
    events: "publish → owner-signed, decline",
    states: [
      {
        state: "ready",
        props: {
          spec: {
            reads: ["value", "status"],
            acts: ["set value, 20–1200, 1 change / min"],
            never: ["video leaves device"],
          },
          tests: {
            total: { value: 14, event_ref: "example:1" },
            passed: { value: 14, event_ref: "example:1" },
            state: "passed",
          },
          coalitions: ["Coalition 1"],
        },
      },
      {
        state: "locked",
        props: {
          spec: {
            reads: ["value", "status"],
            acts: ["set value, 20–1200, 1 change / min"],
            never: ["video leaves device"],
          },
          tests: { state: "failed" },
          coalitions: ["Coalition 1"],
        },
      },
    ],
  },
  {
    name: "ScheduleTwin",
    props: "machines",
    events: "slot.hold → offer",
    states: [
      {
        state: "default",
        props: {
          machines: [
            {
              name: "Resource 1",
              owner: "Member A",
              bookings: [
                { start: "2026-11-04T09:00:00Z", end: "2026-11-04T14:00:00Z", mine: true },
                { start: "2026-11-05T08:00:00Z", end: "2026-11-05T16:00:00Z", mine: false },
              ],
            },
            {
              name: "Resource 2",
              owner: "Member A",
              bookings: [
                { start: "2026-11-04T09:00:00Z", end: "2026-11-04T14:00:00Z", mine: false },
                { start: "2026-11-05T08:00:00Z", end: "2026-11-05T16:00:00Z", mine: false },
              ],
            },
            {
              name: "Resource 3",
              owner: "Member A",
              bookings: [
                { start: "2026-11-04T09:00:00Z", end: "2026-11-04T14:00:00Z", mine: false },
                { start: "2026-11-05T08:00:00Z", end: "2026-11-05T16:00:00Z", mine: false },
              ],
            },
          ],
        },
      },
    ],
  },
];

const states: Record<string, string[]> = {
  AttackTests: ["running", "passed", "failed"],
  CaptureCard: ["ready", "recording", "done"],
  DeviceAlarm: ["firing", "acknowledged", "cleared"],
  DeviceReading: ["live", "stale"],
  EdgeReaderStatus: ["reading", "low-confidence", "lost"],
  MintPipeline: ["running", "failed", "ready to publish"],
  MintedAgentCard: ["live", "offline", "updating"],
  PublishApproval: ["locked", "ready", "published"],
  ScheduleTwin: ["default"],
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
      props:
        example.name === "AttackTests" && s.state === "running"
          ? s.props
          : stateProps(example.name, s.state, s.props),
    })),
  }));
