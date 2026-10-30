// SPDX-License-Identifier: Apache-2.0
import type { Data } from "../f02/ui";
export const examples: Record<string, Data> = {
  AgentHandoff: {
    question: "Would you share Resource 1?",
    reason: "That is a personal choice, so I did not answer.",
    rule: "Personal choices go to the owner",
    choices: [
      { label: "Yes, share", value: "yes" },
      { label: "No", value: "no" },
    ],
  },
  AgentStatus: {
    state: "answering",
    task: "t1",
    budget: {
      used: { value: 0.32, event_ref: "example:44" },
      cap: { value: 2, event_ref: "example:44" },
    },
  },
  AskAgent: {
    text: "Can Task 1 finish Wednesday by 16:00?",
    kind: "bool",
    to: "Member B",
    task_id: "t1",
  },
  CallInvite: {
    title: "Quick check on Plan A?",
    caller: "Member B",
    listeners: ["Your agent"],
    consents: [
      { kind: "transcript", label: "Allow transcript" },
      { kind: "agent", label: "Let your agent listen" },
    ],
  },
  CallSummary: {
    duration: { value: 142, event_ref: "example:44" },
    needs: [{ id: "n1", text: "Resource 1 by Friday" }],
    offers: [{ id: "o1", text: "Member B can help" }],
    decided: [{ id: "p1", text: "Plan A, subject to approval" }],
    questions: [{ id: "q1", text: "Is Thursday available?" }],
  },
  ChannelDigest: {
    channel: "email",
    period: "1 decision, 2 changes since this morning",
    items: [
      { tone: "Needs you", text: "Plan A by Wed 12:00", ref: "p1" },
      { tone: "Changed", text: "Task 3 moved to Friday", ref: "t3" },
      { tone: "Changed", text: "Results Monday", ref: "t4" },
    ],
  },
  CoalitionThread: {
    messages: [
      {
        id: "m1",
        author: "Member A",
        text: "Can we finish together by 10:00?",
        time: "22:14",
        scope: "coalition",
      },
      {
        id: "m2",
        author: "Agent B",
        text: "Yes. The private constraint is satisfied.",
        time: "22:15",
        scope: "coalition",
      },
    ],
    typing: ["Member C"],
  },
  Composer: {
    audience: "me",
    mentions: ["Member A", "Member B"],
    commands: ["/need", "/offer", "/ask", "/private"],
    attachments: [],
  },
  DiarizedTranscript: {
    segments: [
      { id: "s1", speaker: "Member A", start: "00:12", text: "We need Resource 1 by Friday." },
      { id: "s2", speaker: "Member B", start: "00:18", text: "I can provide it." },
    ],
    extracted: [{ id: "n1", kind: "need", text: "Resource 1 by Friday", segment: "s1" }],
  },
  ElicitationForm: {
    message: "Accept Plan A, revision 2?",
    subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
    binding: { bearer: "owner:1" },
    schema: { yes: "bool" },
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  McpAppView: { resourceUri: "ui://coalitionkit/surface-v1.html", tree: ["content"] },
  Message: { text: "Resource 1 is ready.", state: "delivered" },
  NegotiationTheatre: {
    speakers: ["Agent A", "Agent B"],
    events: [
      {
        event_ref: "example:39",
        speaker: "Agent A",
        type: "coalition.query",
        audience: "Agent B",
        text: "Can Task 1 finish Wednesday?",
      },
      {
        event_ref: "example:40",
        speaker: "Agent B",
        type: "coalition.offer",
        audience: "coalition",
        text: "Yes. I can provide Resource 1.",
      },
    ],
  },
  ToolCall: {
    tool: "coalition.my_view",
    args: { scope: "me" },
    state: "done",
    summary: "Your view updated · 2 plans",
  },
  VideoCall: {
    tiles: [
      { participant: "Member A", kind: "person", speaking: true },
      { participant: "Member B", kind: "person", muted: true },
      { participant: "Agent C", kind: "agent" },
    ],
    recording: "off",
    captions: true,
  },
  VoiceCall: {
    participants: ["Member A", "Member B", "Member C"],
    speaking: "Member B",
    caption: "The first plan works for me.",
  },
};
export const groups = [
  ["Threads and messages", ["CoalitionThread", "Message", "ToolCall", "Composer", "AgentStatus"]],
  [
    "Calls: voice, video and the transcript",
    ["VideoCall", "DiarizedTranscript", "VoiceCall", "CallInvite", "CallSummary"],
  ],
  ["Agents negotiating in the open", ["NegotiationTheatre", "AskAgent", "AgentHandoff"]],
  [
    "Inside another chat app: MCP and elicitation",
    ["McpAppView", "ElicitationForm", "ChannelDigest"],
  ],
];
export const labels: Record<string, { props: string; events: string }> = {
  AgentHandoff: {
    props: "choices \u00b7 question \u00b7 reason \u00b7 rule",
    events: "handoff.answer(value)",
  },
  AgentStatus: {
    props: "budget \u00b7 state \u00b7 task",
    events: "agent.pause \u00b7 agent.resume",
  },
  AskAgent: { props: "kind \u00b7 task_id \u00b7 text \u00b7 to", events: "coalition.query" },
  CallInvite: {
    props: "caller \u00b7 consents \u00b7 listeners \u00b7 title",
    events: "call.join \u00b7 call.join_muted \u00b7 call.decline",
  },
  CallSummary: {
    props: "decided \u00b7 duration \u00b7 needs \u00b7 offers \u00b7 questions",
    events: "summary.post(item)",
  },
  ChannelDigest: { props: "channel \u00b7 items \u00b7 period", events: "display only" },
  CoalitionThread: { props: "messages \u00b7 typing", events: "message.open(id)" },
  Composer: {
    props: "attachments \u00b7 audience \u00b7 commands \u00b7 mentions",
    events:
      "message.send(text, scope) \u00b7 need.publish \u00b7 offer.publish \u00b7 voice.record",
  },
  DiarizedTranscript: {
    props: "extracted \u00b7 segments",
    events: "extract.review \u00b7 extract.post(id) \u2192 speaker-signed",
  },
  ElicitationForm: {
    props: "binding \u00b7 decision_deadline \u00b7 message \u00b7 schema \u00b7 subject",
    events: "elicitation.accept \u00b7 elicitation.decline \u00b7 elicitation.cancel",
  },
  McpAppView: { props: "resourceUri \u00b7 tree", events: "tool: my_view, decide, ..." },
  Message: { props: "policy \u00b7 redactions \u00b7 state \u00b7 text", events: "message.retry" },
  NegotiationTheatre: { props: "events \u00b7 speakers", events: "turn.inspect(event_ref)" },
  ToolCall: { props: "args \u00b7 state \u00b7 summary \u00b7 tool", events: "toolcall.expand" },
  VideoCall: {
    props: "captions \u00b7 recording \u00b7 tiles",
    events: "call.mute \u00b7 call.camera \u00b7 call.share \u00b7 call.end",
  },
  VoiceCall: {
    props: "caption \u00b7 participants \u00b7 speaking",
    events: "call.mute \u00b7 call.speaker \u00b7 call.end",
  },
};
