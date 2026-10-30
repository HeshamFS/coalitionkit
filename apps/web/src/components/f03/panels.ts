// SPDX-License-Identifier: Apache-2.0
// Panel labels and geometry specified by the approved design sheet.
export const panels = [
  {
    title: "Threads and messages",
    panels: [
      {
        name: "CoalitionThread",
        title: "CoalitionThread · people and agents",
        span: 2,
        props:
          "messages[] {author: person | agent | host | steward, text, attachments[], card?, scope, time} · system rows · streaming tail · typing per author · grouped by minute",
        events: "TEXT_MESSAGE_START · _CONTENT · _END on the agent session",
      },
      {
        name: "Message",
        title: "Message · every state",
        span: 1,
        props:
          "state: sending | delivered | seen | failed | redacted | blocked · redaction keeps length hint only · blocked shows policy, never content",
        events: "",
      },
      {
        name: "ToolCall",
        title: "ToolCall · in a message",
        span: 1,
        props:
          "tool · args (viewer projection) · state: running | done | failed · result summary · expandable · TOOL_CALL_START / _END",
        events: "",
      },
      {
        name: "Composer",
        title: "Composer · mention, slash, voice",
        span: 2,
        props:
          "text · audience (scope chip, defaults narrowest) · mentions · slash commands → typed messages · attachments → vault first · voice note with live level",
        events: "→ message.send(text, scope) · need.publish · offer.publish",
      },
      {
        name: "AgentStatus",
        title: "AgentStatus · what my agent is doing",
        span: 2,
        props:
          "state: listening | answering | needs-you | paused | offline · task · budget used / cap (from cost meter) · pause / resume",
        events: "",
      },
    ],
  },
  {
    title: "Calls: voice, video and the transcript",
    panels: [
      {
        name: "VideoCall",
        title: "VideoCall · people and an agent",
        span: 2,
        props:
          "tiles[] {participant, kind: person | agent | screen, speaking, muted} · recording: transcript only | off (each person consents) · agent tiles never fake a face",
        events: "",
      },
      {
        name: "DiarizedTranscript",
        title: "DiarizedTranscript · needs pulled out",
        span: 2,
        props:
          "segments[] {speaker, start, text, confidence} · extracted[] {kind: need | offer | decision, text, segment} · private spans stay in the speaker's vault · nothing posts without the speaker's yes",
        events: "",
      },
      {
        name: "VoiceCall",
        title: "VoiceCall · compact",
        span: 1,
        props: "participants · speaking · caption line · mute | speaker | end · 44 px targets",
        events: "",
      },
      {
        name: "CallInvite",
        title: "CallInvite · consent to record",
        span: 1,
        props:
          "caller · title · listeners[] (agents) · consents[] per person, default off for auto-post · join | muted | decline",
        events: "",
      },
      {
        name: "CallSummary",
        title: "CallSummary · after the call",
        span: 2,
        props:
          "decided[] · needs[] · offers[] · questions[] · each item links to its segment · posting an item is the speaker's owner-signed act",
        events: "",
      },
    ],
  },
  {
    title: "Agents negotiating in the open",
    panels: [
      {
        name: "NegotiationTheatre",
        title: "NegotiationTheatre · protocol as dialogue",
        span: 2,
        props:
          "events[] (viewer projection) as turns · speaker seat · message type in mono · arrow = audience · tap a turn → WiringDrawer",
        events: "",
      },
      {
        name: "AskAgent",
        title: "AskAgent · query a member",
        span: 1,
        props:
          "to (participant) · kind: bool | number-range | choice · text · task_id · → coalition.query",
        events: "",
      },
      {
        name: "AgentHandoff",
        title: "AgentHandoff · to a person",
        span: 1,
        props:
          "reason · question · choices[] · rule that caused the hand-off · answer → owner-signed when it binds",
        events: "",
      },
    ],
  },
  {
    title: "Inside another chat app: MCP and elicitation",
    panels: [
      {
        name: "McpAppView",
        title: "McpAppView · CoalitionKit in a chat client",
        span: 2,
        props:
          "resourceUri ui://coalitionkit/surface-v1.html · same A2UI tree as the web door · CSP default-src 'none' · tool results also carry readable text",
        events: "",
      },
      {
        name: "ElicitationForm",
        title: "ElicitationForm · consent asked by the server",
        span: 1,
        props:
          "message (renders identically on retry) · schema ConsentAnswer {yes: bool} · bound to bearer + subject revision · cancel = no decision",
        events: "",
      },
      {
        name: "ChannelDigest",
        title: "ChannelDigest · email and SMS",
        span: 1,
        props:
          "period · items[] {tone, text, ref} · link only (no consent by email) · SMS ≤ 160 chars",
        events: "",
      },
    ],
  },
];
