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
} from "./ui";
import "../../styles/f02.css";

export { AgentDock, Deck, PhoneShell, RoomShell, StageBar, TopBar } from "./shell";
export function EntryComposer({ p, send }: View) {
  const [goal, set] = useState("");
  const [pack, choose] = useState("");
  const [pending, submit] = useState(false);
  return (
    <Frame name="EntryComposer" state={pending ? "submitting" : goal ? "typing" : "empty"}>
      <h2 className="ck-display">What do you want to do together?</h2>
      <label className="ck-field">
        Your goal
        <textarea
          value={goal}
          onChange={(e) => set(e.target.value)}
          placeholder="Describe what needs to happen…"
        />
      </label>
      <Rows value={p.attachments} />
      <div className="ck-row">
        {list(p.packs).map((x) => (
          <Action key={label(x)} pressed={pack === x.id} onClick={() => choose(text(x.id))}>
            {label(x)}
          </Action>
        ))}
      </div>
      <Action
        primary
        disabled={!goal.trim() || pending}
        onClick={() => {
          submit(true);
          send("coalition.create", { goal, ...(pack ? { pack } : {}) });
        }}
      >
        Start a coalition
      </Action>
    </Frame>
  );
}
export function InviteCard({ p, send }: View) {
  const invitation = obj(p.invitation);
  const state = expired(p.expires) ? "expired" : text(invitation.state) || "active";
  return (
    <Frame name="InviteCard" state={state}>
      <h3>Invite a member</h3>
      <span className="ck-tag">{text(p.role)}</span>
      <p>Single-use invitation</p>
      <code>{text(invitation.url ?? invitation.id)}</code>
      <small>
        {text(p.channels)} · {text(p.expires)}
      </small>
      <div className="ck-row">
        <Action
          disabled={state !== "active"}
          onClick={() => send("invite.copy", { invitation: p.invitation })}
        >
          Copy invite
        </Action>
        <Action
          disabled={state !== "active"}
          onClick={() => send("invite.revoke", { invitation: p.invitation })}
        >
          Revoke
        </Action>
      </div>
    </Frame>
  );
}
export function JoinScreen({ p, send }: View) {
  const [read, set] = useState(false);
  const charter = obj(p.charter);
  return (
    <Frame name="JoinScreen" state="invited">
      <span className="ck-meta">Invited by {text(p.inviter)}</span>
      <h3>Join this coalition</h3>
      <p>{text(charter.summary)}</p>
      <Rows value={charter.rules} />
      <Subject value={p.subject} />
      <label>
        <input type="checkbox" checked={read} onChange={(e) => set(e.target.checked)} /> I read the
        charter
      </label>
      <Action
        primary
        disabled={!read}
        onClick={() => send("charter.accept", { subject: p.subject })}
      >
        Accept charter
      </Action>
      <Action onClick={() => send("observe")}>Observe instead</Action>
    </Frame>
  );
}
export function MessageDoor({ p, send }: View) {
  return (
    <Frame name="MessageDoor">
      <div className="ck-bubble">
        <p>{text(p.text)}</p>
        {list(p.choices).map((c) => (
          <Action key={text(c.value)} onClick={() => send("reply", { n: c.n, value: c.value })}>
            {number(c.n)} · {label(c)}
          </Action>
        ))}
        <Action onClick={() => send("reply", { n: "?" })}>? Ask</Action>
      </div>
      {p.receipt ? <small>{text(p.receipt)}</small> : null}
    </Frame>
  );
}
export function LensCard({ p, send }: View) {
  const [ack, set] = useState(false);
  return (
    <Frame name="LensCard" state={ack ? "acknowledged" : "shown"}>
      <span className="ck-meta">{text(p.eyebrow)}</span>
      <h2>{text(p.title)}</h2>
      <p>{text(p.body)}</p>
      {["Tap", "Swipe"].slice(0, Math.min(2, number(p.gestures, 1))).map((name) => (
        <Action
          key={name}
          onClick={() => {
            set(true);
            send("gesture", { name });
          }}
        >
          {name}: {name === "Tap" ? "on my way" : "next"}
        </Action>
      ))}
    </Frame>
  );
}
export function VoiceTurn({ p, send }: View) {
  const [choice, set] = useState<unknown>();
  return (
    <Frame name="VoiceTurn" state={choice === undefined ? "listening" : "confirming"}>
      <b>{choice === undefined ? "Listening" : "Confirm your choice"}</b>
      <div className="ck-wave" aria-hidden="true">
        ▂ ▅ ▇ ▃ ▆ ▂ ▇ ▄ ▃ ▆ ▂
      </div>
      <p>{text(p.script)}</p>
      <small>earcon: {text(p.earcon)}</small>
      <div className="ck-row">
        {list(p.choices).map((c) => (
          <Action
            key={text(c.value)}
            onClick={() => (p.confirm ? set(c.value) : send("voice.choice", { value: c.value }))}
          >
            {Array.isArray(c.words) ? c.words.map(text).join(" / ") : label(c)}
          </Action>
        ))}
      </div>
      {choice !== undefined && (
        <Action
          primary
          onClick={() => {
            send("voice.choice", { value: choice });
            set(undefined);
          }}
        >
          Confirm {text(choice)}
        </Action>
      )}
      <Action onClick={() => send("voice.more")}>Tell me more</Action>
    </Frame>
  );
}
export function PageHeader({ p }: View) {
  return (
    <Frame name="PageHeader">
      <small>{list(p.crumbs).map(label).join(" / ")}</small>
      <span className="ck-meta">{text(p.eyebrow)}</span>
      <h2>{text(p.title)}</h2>
      <div className="ck-row">
        {list(p.tabs).map((t) => (
          <span className="ck-tag" key={label(t)}>
            {label(t)}
          </span>
        ))}
      </div>
    </Frame>
  );
}
export function SplitView({ p, send, build }: View) {
  return (
    <Frame name="SplitView">
      <div className="ck-split">
        <Rows value={p.items} onPick={(x) => send("split.select", { id: x.id })} />
        <div>
          <Children value={p.detail} build={build} />
        </div>
      </div>
    </Frame>
  );
}
export { ConsentTray } from "./ConsentTray";
export function WiringDrawer({ p, send }: View) {
  return (
    <Frame name="WiringDrawer" state={p.event_ref ? "inspecting" : "closed"}>
      <div className="ck-row">
        <h3>The message behind it</h3>
        <code>{text(p.event_ref)}</code>
      </div>
      <pre>{JSON.stringify(p.projection ?? {}, null, 2)}</pre>
      <div className="ck-row">
        <Action onClick={() => send("wiring.verify", { event_ref: p.event_ref })}>
          Verify chain
        </Action>
        <Action onClick={() => send("wiring.copy", { event_ref: p.event_ref })}>Copy</Action>
      </div>
    </Frame>
  );
}
export function NotificationCenter({ p, send }: View) {
  return (
    <Frame name="NotificationCenter" state={list(p.items).length ? "unread" : "empty"}>
      <div className="ck-row">
        <h3>Notifications</h3>
        <Action onClick={() => send("notifications.read")}>Mark all read</Action>
      </div>
      {list(p.items).length ? (
        <Rows value={p.items} onPick={(x) => send("notification.open", { ref: x.ref })} />
      ) : (
        <p>You're all caught up.</p>
      )}
    </Frame>
  );
}
export function AccountMenu({ p, send }: View) {
  return (
    <Frame name="AccountMenu" state="open">
      <b>{label(obj(p.identity))}</b>
      <span className="ck-meta">Owner key · {text(obj(p.identity).kid)}</span>
      <Rows value={p.agents} onPick={(x) => send("account.pick", { id: x.id })} />
      <Rows value={p.channels} onPick={(x) => send("account.pick", { id: x.id })} />
      <small>Appearance · {text(p.appearance) || "system"}</small>
    </Frame>
  );
}
export function BoardTemplate({ p, send }: View) {
  return (
    <Frame name="BoardTemplate">
      <div className="ck-board">
        {list(p.columns).map((c) => (
          <section key={text(c.id)}>
            <h3>{label(c)}</h3>
            {list(p.cards)
              .filter((card) => card.status === c.id)
              .map((card) => (
                <Action key={text(card.id)} onClick={() => send("card.open", { id: card.id })}>
                  {label(card)}
                </Action>
              ))}
          </section>
        ))}
      </div>
    </Frame>
  );
}
