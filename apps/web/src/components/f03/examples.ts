// SPDX-License-Identifier: Apache-2.0
import type { Data } from "../f02/ui";
export const examples: Record<string, Data> = {
  AgentHandoff: {
    question: "B asks whether you’d share a resource.",
    reason: "That’s a personal choice, so I didn’t answer.",
    rule: "personal choices go to the owner",
    choices: [
      { label: "Yes, share", value: "yes" },
      { label: "No", value: "no" },
      { label: "Talk it over", value: "discuss" },
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
    text: "Can the resource leave Wednesday by 16:00?",
    kind: "bool",
    to: "Member B",
    task_id: "t4",
  },
  CallInvite: {
    title: "Three-member sync",
    caller: "Member A",
    listeners: ["Planner"],
    consents: [
      { kind: "transcript", label: "Transcribe what I say" },
      { kind: "auto-post", label: "Let agents post items I said without asking me" },
    ],
  },
  CallSummary: {
    duration: { value: 1080, event_ref: "example:44" },
    decided: [{ id: "p1", text: "Task run Thursday", detail: "A · 1 150 units, 45 min hold" }],
    needs: [{ id: "n1", text: "Item by Wed 22:00", detail: "from Member A · task t4" }],
    questions: [
      { id: "q1", text: "Input size for the task?", detail: "Member C will answer by Fri" },
    ],
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
      { id: "date", kind: "separator", text: "today · 21:40" },
      {
        id: "m1",
        author: { label: "Member A", initial: "A", seat: "seat-1" },
        text: "Can we finish together by 10:00?",
        time: "21:41",
        scope: "coalition",
      },
      {
        id: "m2",
        author: { label: "B's agent", initial: "B", kind: "agent", role: "agent", seat: "seat-2" },
        text: "Member B needs a resource near the workspace before 01:00 and can share a slot.",
        time: "21:42",
        scope: "coalition",
        card: {
          title: "Offer · resource slot ×1",
          summary: "starts after 22:30 · splits the cost",
          action: "Add to my plan",
        },
      },
      {
        id: "system",
        author: { kind: "steward" },
        text: "The steward removed a phone number from B's message",
      },
      {
        id: "m3",
        author: { label: "Planner", initial: "G", kind: "agent", role: "planner", seat: "ink" },
        text: "Drafting two plans from 7 offers",
        time: "now",
        streaming: true,
      },
    ],
    typing: [{ label: "C's agent", initial: "C", status: "C's agent is answering a query" }],
  },
  Composer: {
    audience: "me",
    mentions: [
      { label: "B's agent", handle: "B", initial: "B", seat: "seat-2" },
      { label: "C's agent", handle: "C", initial: "C", seat: "seat-3" },
      { label: "Planner", handle: "Planner", initial: "G", seat: "ink", description: "planner" },
    ],
    commands: [
      { label: "/need", description: "publish a need" },
      { label: "/offer", description: "offer something" },
      { label: "/ask", description: "query an agent" },
      { label: "/private", description: "only me and the host" },
    ],
    attachments: [],
  },
  DiarizedTranscript: {
    segments: [
      {
        id: "s1",
        speaker: { initial: "A", seat: "seat-3" },
        start: "12:01",
        text: "We can run the task Thursday, but only if the item arrives by Wednesday night.",
      },
      {
        id: "s2",
        speaker: { initial: "B", seat: "seat-1" },
        start: "12:02",
        text: "The provider leaves at four. I'd rather not say which provider on the call.",
        note: "kept in B's vault",
        private: true,
      },
      {
        id: "s3",
        speaker: { initial: "C", seat: "seat-5" },
        start: "12:03",
        text: "Then we'll take the input Friday and run the next task on it over the weekend",
        streaming: true,
        note: "transcribing · 0.6 s behind",
      },
    ],
    extracted: [
      { id: "o1", kind: "offer", text: "Offer captured: task Thu", segment: "s1" },
      { id: "n1", kind: "need", text: "Need: item by Wed", segment: "s1" },
    ],
  },
  ElicitationForm: {
    message: "Accept Plan A, revision 2?",
    subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
    binding: { bearer: "owner:1" },
    schema: {
      yes: "bool",
      description:
        "Send Wednesday 16:00, process Thursday, review Friday, finish Monday. Your share: the provider.",
    },
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  McpAppView: { resourceUri: "ui://coalitionkit/surface-v1.html", tree: ["content"] },
  Message: { text: "Resource 1 is ready.", state: "delivered" },
  NegotiationTheatre: {
    speakers: ["Planner", "Agent B", "Agent C"],
    events: [
      {
        event_ref: "example:38",
        speaker: { initial: "G", seat: "ink" },
        type: "coalition.query",
        audience: "→ Member B",
        text: "Can the item leave Wednesday by 16:00?",
      },
      {
        event_ref: "example:39",
        speaker: { initial: "B", seat: "seat-1" },
        type: "coalition.answer",
        audience: "· vault",
        text: "Yes. (the provider stays private)",
      },
      {
        event_ref: "example:40",
        speaker: { initial: "C", seat: "seat-5" },
        type: "coalition.offer",
        audience: "→ task t5",
        text: "Task run on the input, 2D, results Monday.",
      },
      {
        event_ref: "example:41",
        speaker: { initial: "G", seat: "ink" },
        type: "coalition.propose",
        audience: "· 2 plans",
        text: "Plan A: send Wed, process Thu, review Fri, finish Mon. Plan B: everything a week later, cheaper provider.",
        checked: true,
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
