// SPDX-License-Identifier: Apache-2.0
import { Action, num, type Props, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

export function MessageTemplate({ p, send }: { p: Props; send: Send }) {
  return (
    <div className="f11-message">
      <b>{text(p.template)}</b>
      <p>{text(p.params)}</p>
      <div className="row">
        {Array.from(
          { length: Math.min(3, Math.max(0, Math.floor(num(p.quickReplies)))) },
          (_, i) => (
            <Action
              key={["yes", "no", "open"][i]}
              label={["Yes", "No", "Open"][i] ?? "Open"}
              event="reply"
              send={send}
              data={{ id: ["yes", "no", "open"][i] }}
            />
          ),
        )}
      </div>
    </div>
  );
}
