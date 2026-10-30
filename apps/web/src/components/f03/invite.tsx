// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Frame, label, list, text, type View } from "../f02/ui";
import "./invite.css";

export function CallInvite({ p, send }: View) {
  const [consents, set] = useState<Record<string, boolean>>({});
  const listeners = list(p.listeners).map(label).join(", ");
  return (
    <Frame name="CallInvite" state="ringing">
      <div className="f03-invite-head">
        <span className="f03-invite-live" />
        <b>{text(p.caller)} is calling</b>
        <span>{text(p.title)}</span>
      </div>
      {!!listeners && (
        <span className="f03-invite-description">
          {listeners} will listen and write a transcript so it can pull out needs and offers. Audio
          is not kept.
        </span>
      )}
      {list(p.consents).map((consent) => (
        <label className="f03-invite-consent" key={text(consent.kind)}>
          <input
            type="checkbox"
            checked={consents[text(consent.kind)] ?? false}
            onChange={(event) => set({ ...consents, [text(consent.kind)]: event.target.checked })}
          />
          <span>{label(consent) || text(consent.kind)}</span>
        </label>
      ))}
      <div className="f03-invite-actions">
        <button
          className="ck-action ck-primary"
          type="button"
          onClick={() => send("call.join", { consents })}
        >
          Join
        </button>
        <button
          className="ck-action"
          type="button"
          onClick={() => send("call.join_muted", { consents })}
        >
          Join muted
        </button>
        <button className="ck-action" type="button" onClick={() => send("call.decline")}>
          Decline
        </button>
      </div>
    </Frame>
  );
}
