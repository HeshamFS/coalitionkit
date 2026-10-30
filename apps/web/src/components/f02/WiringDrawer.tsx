// SPDX-License-Identifier: Apache-2.0
import { Frame, number, obj, text, type View } from "./ui";
import "./wiring.css";

function JsonLine({ value }: { value: string }) {
  const tokens = value.split(/("(?:[^"\\]|\\.)*"\s*:|"(?:[^"\\]|\\.)*")/g);
  return (
    <>
      {tokens.map((token, i) => (
        <span
          // biome-ignore lint/suspicious/noArrayIndexKey: immutable syntax tokens have no identity or state.
          key={`${i}-${token}`}
          className={
            token.endsWith(":")
              ? "f02-json-key"
              : token.startsWith('"')
                ? "f02-json-string"
                : undefined
          }
        >
          {token}
        </span>
      ))}
    </>
  );
}

function inlineJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(inlineJson).join(", ")}]`;
  if (value && typeof value === "object")
    return `{ ${Object.entries(value)
      .map(([key, item]) => `${JSON.stringify(key)}: ${inlineJson(item)}`)
      .join(", ")} }`;
  return JSON.stringify(value) ?? "null";
}

export function WiringDrawer({ p, send }: View) {
  const projection = obj(p.projection);
  const inspected = obj(projection.inspected);
  const event = projection.event ?? p.projection ?? {};
  const entries = Object.entries(obj(event));
  const lines = entries.length
    ? entries.map(
        ([key, value], i) =>
          `${i === 0 ? "{ " : "  "}${JSON.stringify(key)}: ${inlineJson(value)}${i === entries.length - 1 ? " }" : ","}`,
      )
    : ["{}"];
  return (
    <Frame name="WiringDrawer" state={p.event_ref ? "inspecting" : "closed"}>
      <div className="f02-wiring-columns">
        {inspected.title ? (
          <div className="f02-inspected">
            <header>
              <b>{text(inspected.title)}</b>
              <span>● Changed</span>
            </header>
            <small>{text(inspected.summary)}</small>
            <small>↳ inspecting</small>
          </div>
        ) : null}
        <div className="f02-wire">
          <div className="f02-json-comment">
            {text(p.event_ref)}
            {projection.seq ? ` · seq ${number(projection.seq)}` : ""}
            {projection.time ? ` · ${text(projection.time)}` : ""}
          </div>
          <pre>
            {lines.map((line, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: immutable JSON lines have no identity or state.
              <div key={`${i}-${line}`}>
                <JsonLine value={line} />
              </div>
            ))}
          </pre>
          {projection.prev_hash ? (
            <div className="f02-json-comment">
              prev_hash {text(projection.prev_hash)} · {text(projection.receipt)}
            </div>
          ) : null}
        </div>
      </div>
      <div className="f02-wire-actions">
        <button
          type="button"
          className="f02-verify"
          aria-label="Verify chain"
          onClick={() => send("wiring.verify", { event_ref: p.event_ref })}
        >
          {projection.verified === true ? "Verified" : "Verify"}
        </button>
        {projection.verified === true && <span>chain intact from #1 ·</span>}
        <span className="f02-text-action">open in log</span>
        <span>·</span>
        <button
          type="button"
          className="f02-text-action"
          onClick={() => send("wiring.copy", { event_ref: p.event_ref })}
        >
          copy JSON
        </button>
      </div>
    </Frame>
  );
}
