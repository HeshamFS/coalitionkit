// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { type Data, Frame, label, list, text, type View } from "../f02/ui";
import "./composer.css";

function ComposerIcon({ kind }: { kind: "attach" | "mic" }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      {kind === "attach" ? (
        <path d="M21 12.5l-8.5 8.5a5 5 0 0 1-7-7L14 5.5a3.3 3.3 0 0 1 4.7 4.7L10 19" />
      ) : (
        <>
          <rect x="9" y="3" width="6" height="11" rx="3" />
          <path d="M5 11a7 7 0 0 0 14 0" />
        </>
      )}
    </svg>
  );
}

function ComposerMenu({
  items,
  mention,
  value,
  change,
}: {
  items: Data[];
  mention: boolean;
  value: string;
  change: (value: string) => void;
}) {
  return (
    <div className="f03-composer-menu">
      <div className="f03-composer-menu-title">{mention ? "Mention" : "Commands"}</div>
      {items.map((item, index) => (
        <button
          className={`f03-composer-option${index === 0 ? " f03-composer-active" : ""}`}
          type="button"
          key={label(item)}
          onClick={() =>
            change(
              mention
                ? value.replace(/@[^\s]*$/, `@${text(item.handle) || label(item)} `)
                : `${text(item.command) || label(item)} `,
            )
          }
        >
          {mention && (
            <span
              className="f03-composer-avatar"
              style={{ background: `var(--${text(item.seat) || "ink"})` }}
            >
              {text(item.initial) || label(item).slice(0, 1)}
            </span>
          )}
          <span>{label(item)}</span>
          <span>{text(item.description) || (mention ? "member" : "")}</span>
        </button>
      ))}
    </div>
  );
}

function ComposerInput({
  value,
  change,
  mention,
}: {
  value: string;
  change: (value: string) => void;
  mention: boolean;
}) {
  const at = value.lastIndexOf("@");
  return (
    <div className={`f03-composer-text${mention ? " f03-composer-mention" : ""}`}>
      <textarea
        aria-label="Message"
        placeholder="Message, @mention or /command"
        value={value}
        onChange={(event) => change(event.target.value)}
      />
      {mention && (
        <div className="f03-composer-highlight" aria-hidden="true">
          {value.slice(0, at)}
          <span>{value.slice(at)}</span>
          <i />
        </div>
      )}
    </div>
  );
}

export function Composer({ p, send }: View) {
  const [value, set] = useState("");
  const [recording, record] = useState(false);
  const [seconds, tick] = useState(0);
  const mention = /@[^\s]*$/.test(value);
  const command = value.startsWith("/");
  useEffect(() => {
    if (!recording) return;
    const timer = setInterval(() => tick((previous) => previous + 1), 1000);
    return () => clearInterval(timer);
  }, [recording]);
  const recordVoice = () => {
    record(!recording);
    tick(0);
    send("voice.record");
  };
  return (
    <Frame
      name="Composer"
      state={
        recording
          ? "recording"
          : mention
            ? "mention-menu"
            : command
              ? "command-menu"
              : value
                ? "typing"
                : "empty"
      }
    >
      {(mention || command) && (
        <ComposerMenu
          items={list(mention ? p.mentions : p.commands)}
          mention={mention}
          value={value}
          change={set}
        />
      )}
      {recording ? (
        <div className="f03-composer-recording">
          <span className="f03-composer-record-dot" />
          <div className="f03-composer-wave" aria-hidden="true">
            <i style={{ height: 8 }} />
            <i style={{ height: 14 }} />
            <i style={{ height: 18 }} />
            <i style={{ height: 10 }} />
            <i style={{ height: 16 }} />
            <i style={{ height: 6 }} />
            <i style={{ height: 12 }} />
            <i style={{ height: 4 }} />
            <i style={{ height: 4 }} />
            <i style={{ height: 4 }} />
          </div>
          <span className="f03-composer-time">
            {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}
          </span>
          <button type="button" className="ck-action" onClick={recordVoice}>
            Stop
          </button>
        </div>
      ) : (
        <div className="f03-composer-editor">
          <ComposerInput value={value} change={set} mention={mention} />
          {list(p.attachments).map((item) => (
            <span className="f03-composer-attachment" key={label(item)}>
              {label(item)}
            </span>
          ))}
          <div className="f03-composer-toolbar">
            <span className="f03-composer-attach" title="Attachments go to your vault">
              <ComposerIcon kind="attach" />
            </span>
            <button
              type="button"
              className="f03-composer-icon"
              aria-label="Record"
              onClick={recordVoice}
            >
              <ComposerIcon kind="mic" />
            </button>
            <span className="scope">to: {text(p.audience) || "me"}</span>
            <button
              className="ck-action ck-primary"
              type="button"
              disabled={!value.trim()}
              onClick={() => {
                const event = value.startsWith("/need ")
                  ? "need.publish"
                  : value.startsWith("/offer ")
                    ? "offer.publish"
                    : "message.send";
                send(event, {
                  text: event === "message.send" ? value : value.replace(/^\/\w+\s*/, ""),
                  scope: value.startsWith("/private ") ? "me" : (p.audience ?? "me"),
                });
                set("");
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </Frame>
  );
}
