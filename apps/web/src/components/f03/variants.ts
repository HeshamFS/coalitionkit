// SPDX-License-Identifier: Apache-2.0
import type { Data } from "../f02/ui";
import { examples } from "./examples";

export function variants(name: string): Data[] {
  if (name === "ChannelDigest")
    return [
      examples.ChannelDigest ?? {},
      {
        channel: "sms",
        items: [{ text: "Place B12: task now starts 22:45. Reply STOP to mute." }],
      },
    ];
  if (name === "Composer")
    return [
      { ...examples.Composer, audience: "coalition", initialText: "Can @B" },
      {
        ...examples.Composer,
        audience: "coalition",
        initialText: "/",
        initialRecording: true,
        initialElapsed: { value: 6, event_ref: "example:44" },
      },
    ];
  if (name === "Message")
    return [
      { text: "On my way", state: "sending" },
      { text: "On my way", state: "seen", seen_count: { value: 2, event_ref: "example:44" } },
      { text: "On my way", state: "failed" },
      {
        text: "",
        state: "redacted",
        scope: "task:t2",
        projection: [
          { text: "My place is " },
          { length: { value: 10, event_ref: "example:44" } },
          { text: ", unit " },
          {
            length: { value: 4, event_ref: "example:44" },
            width: { value: 26, event_ref: "example:44" },
          },
        ],
        redactions: [
          { length: { value: 10, event_ref: "example:44" } },
          { length: { value: 4, event_ref: "example:44" } },
        ],
      },
      { text: "", state: "blocked", policy: "no-regulated-advice" },
    ];
  if (name === "ToolCall")
    return [
      {
        tool: "vault.answer",
        state: "running",
        summary: '"Is €96 within the most you’ll pay?"',
        args: { question: "Is €96 within the most you’ll pay?" },
        provenance: "asked by Gardener · only your vault sees the number",
      },
      {
        tool: "psi.match",
        state: "done",
        summary: "2 shared slots across 3 calendars",
        args: { scope: "counts only" },
        duration: { value: 0.4, event_ref: "example:44" },
        emphasis: "2 shared slots",
        provenance: "counts only · nobody learned a busy time",
      },
      { tool: "resource.quote", state: "failed", failure: "timeout" },
    ];
  if (name === "AgentStatus")
    return [
      { state: "listening", task: "watching 3 tasks for you" },
      { state: "answering", task: "query q7 from Gardener" },
      { state: "needs-you", task: 'can’t answer "share item?" alone' },
      { state: "paused", task: "you paused it at 21:58" },
      { state: "offline", task: "last seen 21:50 · retrying" },
      {
        budget: {
          used: { value: 0.34, event_ref: "example:44" },
          cap: { value: 2, event_ref: "example:44" },
        },
      },
    ];
  return [examples[name] ?? {}];
}
