// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { CoalitionMark, ShellIcon } from "./shell";
import { expired, Frame, label, list, number, obj, text, type View } from "./ui";
import "./entry.css";

export function EntryComposer({ p, send }: View) {
  const [goal, setGoal] = useState(() => text(p.draft));
  const [pack, setPack] = useState("");
  const [pending, setPending] = useState(false);
  return (
    <Frame name="EntryComposer" state={pending ? "submitting" : goal ? "typing" : "empty"}>
      <CoalitionMark />
      <h2>What do you need done, together?</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!goal.trim() || pending) return;
          setPending(true);
          send("coalition.create", { goal, ...(pack ? { pack } : {}) });
        }}
      >
        <textarea
          aria-label="Your goal"
          placeholder="Describe what you need done, together…"
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
        />
        <div className="f02-compose-tools">
          {list(p.attachments).map((attachment) => (
            <span className="f02-chip" key={label(attachment)}>
              <ShellIcon name="File" />
              {label(attachment)}
            </span>
          ))}
          <span className="f02-chip">
            <ShellIcon name="Microphone" />
            Voice
          </span>
          <span className="f02-chip">
            <span className="f02-vault-note">stays in your vault</span>
          </span>
          <button
            className="ck-action ck-primary"
            type="submit"
            aria-label="Start a coalition"
            disabled={!goal.trim() || pending}
          >
            Form a coalition
            <ShellIcon name="Send" />
          </button>
        </div>
      </form>
      <div className="f02-pack-list">
        <small>Start from:</small>
        {list(p.packs).map((item) => (
          <button
            className="f02-chip"
            type="button"
            key={text(item.id)}
            aria-pressed={pack === item.id}
            onClick={() => setPack(text(item.id))}
          >
            {label(item)}
          </button>
        ))}
        <button type="button" className="f02-chip f02-no-pack" onClick={() => setPack("")}>
          No pack, plain goal
        </button>
      </div>
    </Frame>
  );
}

export function InviteCard({ p, send }: View) {
  const invitation = obj(p.invitation);
  const state = expired(p.expires) ? "expired" : text(invitation.state) || "active";
  const remaining = Math.max(0, Math.ceil((Date.parse(text(p.expires)) - Date.now()) / 3600000));
  return (
    <Frame name="InviteCard" state={state}>
      {Array.isArray(invitation.qr) && (
        <svg
          className="f02-invite-qr"
          viewBox="0 0 29 29"
          aria-label="Invitation code illustration"
          role="img"
          shapeRendering="crispEdges"
        >
          <title>Invitation code illustration</title>
          <rect width="29" height="29" fill="white" />
          {list(invitation.qr).map((rect) => (
            <rect
              key={`${number(rect.x)}-${number(rect.y)}-${number(rect.w)}`}
              x={number(rect.x)}
              y={number(rect.y)}
              width={number(rect.w)}
              height={number(rect.h)}
              fill={rect.light ? "white" : "#0E1726"}
            />
          ))}
        </svg>
      )}
      <b>Join “{text(invitation.title) || "this coalition"}”</b>
      <p>
        Scan with your phone or point your own agent at the card. The link works once, for one
        person.
      </p>
      <button
        type="button"
        className="f02-invite-link"
        aria-label="Copy invite"
        disabled={state !== "active"}
        onClick={() => send("invite.copy", { invitation: p.invitation })}
      >
        <code>{text(invitation.url ?? invitation.id)}</code>
        <ShellIcon name="Copy" />
      </button>
      <small>
        <time dateTime={text(p.expires)} title={text(p.expires)}>
          {state === "active" ? `expires in ${remaining} h` : state}
        </time>{" "}
        · role: {text(p.role).toLowerCase()}
      </small>
      {invitation.canRevoke === true && (
        <button
          type="button"
          className="f02-text-action"
          disabled={state !== "active"}
          onClick={() => send("invite.revoke", { invitation: p.invitation })}
        >
          Revoke invitation
        </button>
      )}
    </Frame>
  );
}

export function JoinScreen({ p, send }: View) {
  const charter = obj(p.charter);
  const [open, setOpen] = useState(false);
  return (
    <Frame name="JoinScreen" state="invited">
      <span className="f02-eyebrow">You're invited by {text(p.inviter)}</span>
      <h3>{text(charter.title) || "Join this coalition"}</h3>
      <p>{text(charter.summary)}</p>
      <hr />
      <div className="f02-charter-rules">
        {list(charter.rules).map((rule) => (
          <div key={label(rule)} data-tone={text(rule.tone)}>
            <ShellIcon name={rule.tone === "warn" ? "Warning" : "Tasks"} />
            <span>{label(rule)}</span>
          </div>
        ))}
      </div>
      <button type="button" className="f02-text-action" onClick={() => setOpen(!open)}>
        Read the full charter (r{number(obj(p.subject).revision)})
      </button>
      {open && <p>{text(charter.full) || text(charter.summary)}</p>}
      <button
        type="button"
        className="ck-action ck-primary"
        onClick={() => send("charter.accept", { subject: p.subject })}
      >
        Join with my agent
      </button>
      <button
        type="button"
        className="ck-action f02-ghost"
        aria-label="Observe instead"
        onClick={() => send("observe")}
      >
        Join as a watcher only
      </button>
    </Frame>
  );
}
