// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Action, Frame, label, list, text, type View } from "../f02/ui";
import "../../styles/f02.css";
import "../../styles/f03.css";

export { VideoCall, VoiceCall } from "./calls";
export { AgentStatus, Message, ToolCall } from "./chat";
export { Composer } from "./composer";
export { CallSummary, DiarizedTranscript, NegotiationTheatre } from "./dialogue";
export { CallInvite } from "./invite";
export { CoalitionThread } from "./thread";
export function AskAgent({ p, send }: View) {
  const [value, set] = useState(text(p.text));
  const [kind, choose] = useState(text(p.kind) || "bool");
  return (
    <Frame name="AskAgent">
      <b>Ask {text(p.to)}'s agent</b>
      <div className="f03-query-options">
        {["bool", "number-range", "choice"].map((k) => (
          <Action key={k} pressed={kind === k} onClick={() => choose(k)}>
            {k === "bool" ? "Yes / no" : k === "number-range" ? "Number" : "Choice"}
          </Action>
        ))}
      </div>
      <textarea
        className="f03-query-input"
        aria-label="Question"
        value={value}
        onChange={(e) => set(e.target.value)}
      />
      <div className="f03-query-note">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="5" y="11" width="14" height="10" rx="2" />
          <path d="M8 11V8a4 4 0 0 1 8 0v3" />
        </svg>
        Their vault answers; you see only the answer
      </div>
      <div className="f03-query-footer">
        <span className="ck-tag">{p.task_id ? `task:${text(p.task_id)}` : "me"}</span>
        <Action
          primary
          disabled={!value.trim()}
          onClick={() =>
            send("coalition.query", { to: p.to, kind, text: value, task_id: p.task_id })
          }
        >
          Ask
        </Action>
      </div>
    </Frame>
  );
}
export function AgentHandoff({ p, send }: View) {
  return (
    <Frame name="AgentHandoff">
      <div className="card card-ask">
        <div className="row">
          <span className="f03-agent-avatar">Y</span>
          <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
          <span className="av s1">A</span>
          <b style={{ fontSize: 12.5 }}>Your agent needs you</b>
        </div>
        <span className="small" style={{ color: "var(--ink)" }}>
          {text(p.question)} {text(p.reason)}
        </span>
        <div className="row">
          {list(p.choices).map((c, index) => (
            <Action
              key={text(c.value ?? c.id)}
              primary={index === 0}
              onClick={() => send("handoff.answer", { value: c.value ?? c.id })}
            >
              {label(c)}
            </Action>
          ))}
        </div>
      </div>
      <span className="st">the agent's rule: {text(p.rule)}</span>
    </Frame>
  );
}
export { ChannelDigest } from "./digest";
export { ElicitationForm } from "./elicitation";
export { McpAppView } from "./mcp";
