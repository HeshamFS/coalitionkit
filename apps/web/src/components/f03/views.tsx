// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import {
  Action,
  Children,
  expired,
  Frame,
  label,
  list,
  number,
  obj,
  Rows,
  Subject,
  text,
  type View,
} from "../f02/ui";
import "../../styles/f02.css";
import "../../styles/f03.css";

export { AgentStatus, Message, ToolCall } from "./chat";

export function CoalitionThread({ p, send }: View) {
  return (
    <Frame name="CoalitionThread" state={list(p.messages).length ? "streaming" : "empty"}>
      {list(p.messages).map((m, i) => (
        <div className="ck-turn" key={text(m.id) || `${text(m.time)}-${i}`}>
          <span className="ck-avatar">{text(obj(m.author).label ?? m.author).slice(0, 1)}</span>
          <div className="ck-bubble">
            <small>
              {text(obj(m.author).label ?? m.author)} · {text(m.time)} · {text(m.scope)}
            </small>
            <Action onClick={() => send("message.open", { id: m.id })}>{text(m.text)}</Action>
            <Rows value={m.attachments} />
          </div>
        </div>
      ))}
      {!list(p.messages).length && <p>No messages yet.</p>}
      {list(p.typing).length > 0 && <small>{list(p.typing).map(label).join(", ")} typing…</small>}
    </Frame>
  );
}
export function Composer({ p, send }: View) {
  const [value, set] = useState("");
  const [recording, record] = useState(false);
  return (
    <Frame
      name="Composer"
      state={
        recording
          ? "recording"
          : value.startsWith("@")
            ? "mention-menu"
            : value.startsWith("/")
              ? "command-menu"
              : value
                ? "typing"
                : "empty"
      }
    >
      <label className="ck-field">
        Message
        <textarea
          placeholder="Message, @mention or /command"
          value={value}
          onChange={(e) => set(e.target.value)}
        />
      </label>
      {value.startsWith("@") && <Rows value={p.mentions} onPick={(x) => set(`@${label(x)} `)} />}{" "}
      {value.startsWith("/") && <Rows value={p.commands} onPick={(x) => set(`${label(x)} `)} />}
      <Rows value={p.attachments} />
      <div className="ck-row">
        <span className="ck-tag">{text(p.audience) || "me"}</span>
        <Action onClick={() => send("need.publish", { text: value })}>Need</Action>
        <Action onClick={() => send("offer.publish", { text: value })}>Offer</Action>
        <Action
          pressed={recording}
          onClick={() => {
            record(!recording);
            send("voice.record");
          }}
        >
          Record
        </Action>
        <Action
          primary
          disabled={!value.trim()}
          onClick={() => {
            send("message.send", { text: value, scope: p.audience ?? "me" });
            set("");
          }}
        >
          Send
        </Action>
      </div>
    </Frame>
  );
}
export function VideoCall({ p, send }: View) {
  const [muted, mute] = useState(false);
  const [camera, setCamera] = useState(false);
  const [ended, end] = useState(false);
  return (
    <Frame name="VideoCall" state={ended ? "ended" : list(p.tiles).length ? "live" : "connecting"}>
      <div className="ck-call-head">
        <b>{ended ? "Call ended" : "Coalition call"}</b>
        <small>Recording: {text(p.recording) || "off"}</small>
      </div>
      <div className="ck-video-grid">
        {list(p.tiles).map((tile, i) => (
          <div
            className={`ck-video-tile ${tile.speaking ? "ck-speaking" : ""}`}
            key={text(tile.id ?? tile.participant) || `${i}`}
          >
            <span className="ck-avatar">
              {text(obj(tile.participant).label ?? tile.participant).slice(0, 1)}
            </span>
            <small>
              {text(obj(tile.participant).label ?? tile.participant)} {tile.muted ? "· muted" : ""}
            </small>
          </div>
        ))}
      </div>
      {!!p.captions && <p className="ck-captions">Captions on</p>}
      <div className="ck-row">
        <Action
          disabled={ended}
          pressed={muted}
          onClick={() => {
            mute(!muted);
            send("call.mute", { muted: !muted });
          }}
        >
          Mute
        </Action>
        <Action
          disabled={ended}
          pressed={camera}
          onClick={() => {
            setCamera(!camera);
            send("call.camera", { enabled: !camera });
          }}
        >
          Camera
        </Action>
        <Action disabled={ended} onClick={() => send("call.share")}>
          Share
        </Action>
        <Action
          disabled={ended}
          onClick={() => {
            end(true);
            send("call.end");
          }}
        >
          End call
        </Action>
      </div>
    </Frame>
  );
}
export function VoiceCall({ p, send }: View) {
  const [muted, mute] = useState(false);
  const [speaker, set] = useState(false);
  const [ended, end] = useState(false);
  return (
    <Frame name="VoiceCall" state={ended ? "ended" : p.speaking ? "live" : "ringing"}>
      <h3>{ended ? "Call ended" : "Coalition call"}</h3>
      <div className="ck-call-people">
        {list(p.participants).map((x) => (
          <span className="ck-avatar" key={label(x)}>
            {label(x).slice(0, 1)}
          </span>
        ))}
      </div>
      <span>{text(p.speaking)} speaking</span>
      <p>{text(p.caption)}</p>
      <div className="ck-wave" aria-hidden="true">
        ▂ ▅ ▇ ▃ ▆ ▂ ▇
      </div>
      <div className="ck-row">
        <Action
          disabled={ended}
          pressed={muted}
          onClick={() => {
            mute(!muted);
            send("call.mute", { muted: !muted });
          }}
        >
          Mute
        </Action>
        <Action
          disabled={ended}
          pressed={speaker}
          onClick={() => {
            set(!speaker);
            send("call.speaker", { enabled: !speaker });
          }}
        >
          Speaker
        </Action>
        <Action
          disabled={ended}
          onClick={() => {
            end(true);
            send("call.end");
          }}
        >
          End call
        </Action>
      </div>
    </Frame>
  );
}
export function CallInvite({ p, send }: View) {
  const [consents, set] = useState<Record<string, boolean>>({});
  return (
    <Frame name="CallInvite" state="ringing">
      <span className="ck-meta">Incoming call · {text(p.caller)}</span>
      <h3>{text(p.title)}</h3>
      <Rows value={p.listeners} />
      {list(p.consents).map((c) => (
        <label key={text(c.kind)}>
          <input
            type="checkbox"
            checked={consents[text(c.kind)] ?? false}
            onChange={(e) => set({ ...consents, [text(c.kind)]: e.target.checked })}
          />
          {label(c) || text(c.kind)}
        </label>
      ))}
      <div className="ck-row">
        <Action primary onClick={() => send("call.join", { consents })}>
          Join
        </Action>
        <Action onClick={() => send("call.join_muted", { consents })}>Join muted</Action>
        <Action onClick={() => send("call.decline")}>Decline</Action>
      </div>
    </Frame>
  );
}
export function DiarizedTranscript({ p, send }: View) {
  return (
    <Frame name="DiarizedTranscript">
      <b>Live transcript</b>
      <span className="ck-tag">Model output · review before posting</span>
      {list(p.segments).map((s, i) => (
        <div className="ck-turn" key={text(s.id) || `${i}`}>
          <span className="ck-meta">{text(s.start)}</span>
          <b>{text(s.speaker)}</b>
          <p>{text(s.text)}</p>
        </div>
      ))}
      <Action onClick={() => send("extract.review")}>Review extracted items</Action>
      {list(p.extracted).map((x, i) => (
        <div className="ck-extract" key={text(x.id) || `${i}`}>
          <b>{text(x.kind)}</b>
          <p>{text(x.text)}</p>
          <Action onClick={() => send("extract.post", { id: x.id ?? x.segment })}>
            Review and post
          </Action>
        </div>
      ))}
    </Frame>
  );
}
export function CallSummary({ p, send }: View) {
  return (
    <Frame name="CallSummary">
      <h3>Call summary</h3>
      <small>{number(p.duration)} seconds · Model output</small>
      {["needs", "offers", "decided", "questions"].map((kind) => (
        <section key={kind}>
          <b>{kind}</b>
          {list(p[kind]).map((item, i) => (
            <div className="ck-row" key={text(item.id) || `${i}`}>
              <span>{label(item)}</span>
              <Action onClick={() => send("summary.post", { item })}>Review and post</Action>
            </div>
          ))}
        </section>
      ))}
    </Frame>
  );
}
export function NegotiationTheatre({ p, send }: View) {
  return (
    <Frame name="NegotiationTheatre">
      <h3>Agents negotiating</h3>
      {list(p.events).map((e, i) => (
        <div className="ck-turn" key={text(e.event_ref) || `${i}`}>
          <span className="ck-avatar">{text(e.speaker).slice(0, 1)}</span>
          <div className="ck-bubble">
            <small className="ck-meta">
              {text(e.type)} → {text(e.audience)}
            </small>
            <p>{text(e.text ?? e.summary)}</p>
            <Action onClick={() => send("turn.inspect", { event_ref: e.event_ref })}>
              Inspect turn
            </Action>
          </div>
        </div>
      ))}
    </Frame>
  );
}
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
export function McpAppView({ p, build }: View) {
  return (
    <Frame name="McpAppView" state={p.tree ? "ready" : "loading"}>
      <header>CoalitionKit</header>
      {p.tree ? <Children value={p.tree} build={build} /> : <p role="status">Loading your view…</p>}
      <small className="ck-meta">{text(p.resourceUri)}</small>
    </Frame>
  );
}
export function ElicitationForm({ p, send }: View) {
  const [yes, set] = useState<boolean>();
  return (
    <Frame name="ElicitationForm" state="asked">
      <span className="ck-meta">CoalitionKit asks you</span>
      <h3>{text(p.message)}</h3>
      <Subject value={p.subject} />
      <label>
        <input type="radio" checked={yes === true} onChange={() => set(true)} />
        Yes, accept
      </label>
      <label>
        <input type="radio" checked={yes === false} onChange={() => set(false)} />
        No
      </label>
      <div className="ck-row">
        <Action
          primary
          disabled={yes === undefined || expired(p.decision_deadline)}
          onClick={() =>
            send(yes ? "elicitation.accept" : "elicitation.decline", {
              subject: p.subject,
              binding: p.binding,
            })
          }
        >
          Submit
        </Action>
        <Action onClick={() => send("elicitation.cancel")}>Cancel</Action>
      </div>
      <small>Your owner key signs after review. A changed revision must be reviewed again.</small>
    </Frame>
  );
}
export function ChannelDigest({ p }: View) {
  return (
    <Frame name="ChannelDigest" state="sent">
      <header>
        <small>{text(p.channel)}</small>
        <h3>{text(p.period)}</h3>
      </header>
      {list(p.items).map((x, i) => (
        <div className="ck-row" key={text(x.ref) || `${i}`}>
          <span className="ck-tag">{text(x.tone)}</span>
          <span>{text(x.text)}</span>
        </div>
      ))}
      <small>Decisions are never taken by email reply.</small>
    </Frame>
  );
}
