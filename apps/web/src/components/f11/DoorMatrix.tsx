// SPDX-License-Identifier: Apache-2.0
import { list, obj, type Props, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

function DoorPreview({ door }: { door: Props }) {
  const kind = text(door.kind),
    title = text(door.title),
    body = text(door.body);
  if (kind === "message")
    return (
      <div className="f11-message">
        <div className="f11-bubble">
          {body}
          <br />
          Reply <b>1</b> accept · <b>2</b> no · <b>?</b> ask
          <br />
          <span className="st">{text(door.deadline)}</span>
        </div>
      </div>
    );
  if (kind === "lens")
    return (
      <div className="f11-lens">
        <span className="mono">{text(door.deadline)}</span>
        <b>{title}</b>
        <span>{body}</span>
      </div>
    );
  if (kind === "voice")
    return (
      <div className="card">
        <span className="row">
          <span className="live-dot" />
          <span className="st">speaking</span>
        </span>
        <span className="small">{body}</span>
        <span className="st">{text(door.confirm)}</span>
      </div>
    );
  if (kind === "mcp-app")
    return (
      <div className="card f11-mcp-preview">
        <span className="st">in a chat client</span>
        <b>{title}</b>
        <span className="row">
          <span className="radio radio-on" />
          <span className="small">Yes</span>
          <span className="radio" />
          <span className="small">No</span>
        </span>
        <span className="st">elicitation · signed after submit</span>
      </div>
    );
  return (
    <div className="card card-ask">
      <b>{title}</b>
      <span className="small">{body}</span>
      <div className={kind === "compact" ? "col" : "row"}>
        <button type="button" className="btn btn-sm btn-primary" aria-disabled="true">
          Accept
        </button>
        <button type="button" className="btn btn-sm" aria-disabled="true">
          {kind === "compact" ? "Not this" : "No"}
        </button>
        {kind === "wide" && (
          <button type="button" className="btn btn-sm btn-ghost" aria-disabled="true">
            Compare
          </button>
        )}
      </div>
    </div>
  );
}
export function DoorMatrix({ p }: { p: Props; send: Send }) {
  return (
    <>
      <div className="f11-doors">
        {list(p.doors).map((value) => {
          const door = typeof value === "string" ? { kind: value, title: p.target } : obj(value);
          return (
            <div className={`col f11-door-${text(door.kind)}`} key={text(door.kind)}>
              <span className="eyebrow">
                {text(door.kind) === "mcp-app" ? "MCP App" : text(door.kind)}
              </span>
              <DoorPreview door={door} />
            </div>
          );
        })}
      </div>
      <span className="small">
        Every door shows the same subject, revision, deadline and consequence; each picks its own
        layout and input. A door that can't sign (lens, email) hands off to one that can.
      </span>
    </>
  );
}
