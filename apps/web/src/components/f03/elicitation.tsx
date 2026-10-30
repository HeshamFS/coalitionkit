// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { expired, Frame, obj, text, type View } from "../f02/ui";
import "./elicitation.css";

export function ElicitationForm({ p, send }: View) {
  const [yes, set] = useState<boolean>();
  return (
    <Frame name="ElicitationForm" state="asked">
      <span className="f03-elicit-eyebrow">coalitionkit asks you</span>
      <b>{text(p.message)}</b>
      {!!obj(p.schema).description && (
        <span className="f03-elicit-description">{text(obj(p.schema).description)}</span>
      )}
      <label className="f03-elicit-choice">
        <input type="radio" checked={yes === true} onChange={() => set(true)} />
        <span>Yes, accept</span>
      </label>
      <label className="f03-elicit-choice">
        <input type="radio" checked={yes === false} onChange={() => set(false)} />
        <span>No</span>
      </label>
      <div className="f03-elicit-actions">
        <button
          className="ck-action ck-primary"
          type="button"
          disabled={yes === undefined || expired(p.decision_deadline)}
          onClick={() =>
            send(yes ? "elicitation.accept" : "elicitation.decline", {
              subject: p.subject,
              binding: p.binding,
            })
          }
        >
          Submit
        </button>
        <button className="ck-action" type="button" onClick={() => send("elicitation.cancel")}>
          Cancel
        </button>
      </div>
      <span className="f03-elicit-footnote">
        signed by your owner key after you submit · if the plan changes, you're asked again
      </span>
    </Frame>
  );
}
