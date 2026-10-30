// SPDX-License-Identifier: Apache-2.0
import { list, num, obj, type Props, type Send, text } from "../f08/shared";
import "../../styles/f11.css";
export function MessageTemplate({ p, send }: { p: Props; send: Send }) {
  const params = list(p.params),
    replies = list(obj(params[2]).replies);
  return (
    <>
      <div className="f11-message">
        <div className="f11-bubble">
          <b>{text(params[0])}</b>
          <br />
          {text(params[1])}
          <br />
          <span className="st">template: {text(p.template)}</span>
        </div>
        <div className="row f11-replies">
          {Array.from(
            { length: Math.min(3, Math.max(0, Math.floor(num(p.quickReplies)))) },
            (_, i) => {
              const reply = obj(replies[i]);
              return (
                <button
                  type="button"
                  key={text(reply.id) || i}
                  onClick={() => send("reply", { id: reply.id ?? ["yes", "no", "open"][i] })}
                >
                  {text(reply.label) || ["Yes", "No", "Open"][i]}
                </button>
              );
            },
          )}
        </div>
      </div>
      <span className="st">
        outside the 24 h window only approved templates; no private values in templates
      </span>
    </>
  );
}
