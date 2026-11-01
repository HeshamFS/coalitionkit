// SPDX-License-Identifier: Apache-2.0
import { type FormEvent, type ReactNode, useState } from "react";
import { Banner } from "../components/feedback";
import { Avatar, Badge, cx } from "../components/primitives";
import { capital, useVocabulary } from "../feed/vocabulary";
import { Icon } from "../ui/Icon";

/* ---------- AgentDock ---------- */

export type DockMessage =
  | { id: string; from: "agent" | "me"; text: string }
  | { id: string; from: "tool"; text: string };
export type DockState = "idle" | "streaming" | "tool-call" | "offline";

export function AgentDock({
  agentName = "Your agent",
  messages,
  state = "idle",
  composer = "text",
  composerDisabledReason,
  onSay,
}: {
  agentName?: string;
  messages: DockMessage[];
  state?: DockState;
  composer?: "text" | "voice";
  /** When set the composer is switched off and says why. */
  composerDisabledReason?: string;
  onSay?: (text: string) => void;
}) {
  const [draft, setDraft] = useState("");
  const offline = state === "offline";
  const off = offline || Boolean(composerDisabledReason);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || off) return;
    onSay?.(text);
    setDraft("");
  };
  return (
    <aside className="agent-dock" aria-label={agentName}>
      <div className="row" style={{ padding: "10px 12px", borderBottom: "1px solid var(--line)" }}>
        <Avatar seat="host" label="Your agent" />
        <b style={{ fontSize: 13 }}>{agentName}</b>
        <span className="h-right small" role="status">
          {state === "idle" && "private to you"}
          {state === "streaming" && "writing…"}
          {state === "tool-call" && "checking your vault…"}
          {offline && "offline"}
        </span>
      </div>
      <div
        className="col"
        style={{ padding: "10px 12px", gap: 8, flex: 1, overflow: "auto" }}
        role="log"
        aria-live="polite"
      >
        {messages.map((m, i) =>
          m.from === "tool" ? (
            <div key={m.id} className="card" style={{ padding: "8px 10px" }}>
              <div className="row">
                <Badge kind="signed" label="tool" />
                <span className="mono" style={{ fontSize: 10.5 }}>
                  {m.text}
                </span>
              </div>
            </div>
          ) : (
            <div
              key={m.id}
              className={cx("bubble", m.from === "agent" ? "bubble-in" : "bubble-out")}
            >
              {m.text}
              {state === "streaming" && m.from === "agent" && i === messages.length - 1 && (
                <span className="caret" aria-hidden="true" />
              )}
            </div>
          ),
        )}
        {state === "tool-call" && (
          <div className="card card-dashed" style={{ padding: "8px 10px" }}>
            <span className="small">
              <span
                className="spinner"
                style={{
                  color: "var(--blue)",
                  width: 10,
                  height: 10,
                  display: "inline-block",
                  verticalAlign: -1,
                }}
              />{" "}
              Calling a tool{"…"}
            </span>
          </div>
        )}
      </div>
      {offline && (
        <div style={{ padding: "0 12px 8px" }}>
          <Banner
            tone="ask"
            title="Your agent is offline."
            body="Messages wait until it is back."
          />
        </div>
      )}
      <form onSubmit={submit} style={{ padding: "10px 12px", borderTop: "1px solid var(--line)" }}>
        <div
          className="input"
          style={off ? { background: "var(--surface-2)" } : undefined}
          title={composerDisabledReason}
        >
          <input
            aria-label="Ask your agent"
            value={draft}
            disabled={off}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={composer === "voice" ? "Hold the mic to talk…" : "Ask your agent…"}
            style={{
              border: 0,
              outline: "none",
              background: "transparent",
              font: "inherit",
              color: "inherit",
              flex: 1,
              minWidth: 0,
            }}
          />
          <span className="h-right row" style={{ gap: 6, color: "var(--ink-3)" }}>
            <button type="button" className="icon-btn" aria-label="Speak" disabled={off}>
              <Icon name="mic" size="sm" />
            </button>
            <button
              type="submit"
              className="icon-btn"
              aria-label="Send"
              disabled={off || !draft.trim()}
            >
              <Icon name="send" size="sm" />
            </button>
          </span>
        </div>
        {composerDisabledReason && <span className="help">{composerDisabledReason}</span>}
      </form>
    </aside>
  );
}

/* ---------- ConsentTray ---------- */

export type ConsentRequest = {
  id: string;
  kind: "plan" | "tension" | "commitment" | "charter";
  title: string;
  /** Free text such as "18 min" or "no deadline". Set `urgent` when the clock is close. */
  deadline?: string;
  urgent?: boolean;
  revision?: number;
};
const KIND_BADGE: Record<ConsentRequest["kind"], string> = {
  plan: "Decide",
  tension: "Choose",
  commitment: "Approve",
  charter: "Review",
};

export function ConsentTray({
  requests,
  onOpen,
}: {
  requests: ConsentRequest[];
  onOpen?: (id: string) => void;
}) {
  const { word } = useVocabulary();
  const decisions = `${capital(word("decision", 2))} waiting for you`;
  if (requests.length === 0) {
    return (
      <section className="tray" aria-label={decisions} data-state="empty">
        <Icon name="shieldCheck" />
        <span className="small">Nothing waits for you.</span>
      </section>
    );
  }
  const urgent = requests.some((r) => r.urgent);
  const first = requests[0];
  if (requests.length === 1 && first) {
    return (
      <section className="tray" aria-label={decisions} data-state={urgent ? "urgent" : "pending"}>
        <span style={{ color: "var(--warn-fg)", display: "inline-flex" }}>
          <Icon name="shield" />
        </span>
        <div className="col grow" style={{ gap: 0 }}>
          <b style={{ fontSize: 12.5 }}>1 {word("decision")} waits for you</b>
          <span className="small">
            {first.title}
            {first.deadline ? ` · ${first.deadline}` : ""}
          </span>
        </div>
        <button type="button" className="btn btn-sm btn-primary" onClick={() => onOpen?.(first.id)}>
          {KIND_BADGE[first.kind]}
        </button>
      </section>
    );
  }
  return (
    <section
      className="tray"
      aria-label={decisions}
      data-state={urgent ? "urgent" : "pending"}
      style={{ flexDirection: "column", alignItems: "stretch", gap: 6 }}
    >
      <div className="row">
        <span style={{ color: "var(--warn-fg)", display: "inline-flex" }}>
          <Icon name="shield" />
        </span>
        <b style={{ fontSize: 13 }}>{requests.length} things wait for you</b>
        <span className="h-right small">nothing happens without your answer</span>
      </div>
      {requests.map((r, i) => (
        <div key={r.id} className="row card" style={{ flexDirection: "row", padding: "8px 10px" }}>
          <span className="badge b-estimate" style={{ minWidth: 62, justifyContent: "center" }}>
            {KIND_BADGE[r.kind]}
          </span>
          <span className="h-title grow">{r.title}</span>
          <span className="num small" style={r.urgent ? { color: "var(--warn-fg)" } : undefined}>
            {r.deadline}
          </span>
          <button
            type="button"
            className={cx("btn btn-sm", i === 0 && "btn-primary")}
            aria-label={`Open ${r.title}`}
            onClick={() => onOpen?.(r.id)}
          >
            Open
          </button>
        </div>
      ))}
    </section>
  );
}

/* ---------- WiringDrawer ---------- */

export type WiringState = "closed" | "inspecting" | "verified" | "broken";

/** Pretty JSON, one div per line, keys and string values coloured as in the wiring sheet. */
function Json({ value }: { value: unknown }): ReactNode {
  const lines = JSON.stringify(value, null, 2).split("\n");
  return lines.map((line, n) => {
    const m = /^(\s*)("(?:[^"\\]|\\.)*")(: )?(.*)$/.exec(line);
    const key = `${n}-${line}`;
    if (!m) {
      return (
        <div key={key} style={{ whiteSpace: "pre" }}>
          {line}
        </div>
      );
    }
    const [, indent, first, colon, rest] = m;
    return (
      <div key={key} style={{ whiteSpace: "pre" }}>
        {indent}
        <span className={colon ? "k" : "s"}>{first}</span>
        {colon}
        {rest && /^"/.test(rest) ? (
          <>
            <span className="s">{rest.replace(/,$/, "")}</span>
            {rest.endsWith(",") ? "," : ""}
          </>
        ) : (
          rest
        )}
      </div>
    );
  });
}

export function WiringDrawer({
  state,
  header,
  message,
  footnote,
  onVerify,
  onCopy,
  onClose,
}: {
  state: WiringState;
  /** For example "#43 · seq 43 · 22:19:07". */
  header?: string;
  /** The viewer's own projection of the event, never more. */
  message?: unknown;
  footnote?: string;
  onVerify?: () => void;
  onCopy?: () => void;
  onClose?: () => void;
}) {
  if (state === "closed") return null;
  return (
    <aside className="drawer" aria-label="The message behind this element" data-state={state}>
      <div className="row">
        <b style={{ fontSize: 13 }}>Wiring</b>
        <span className="h-right">
          <button type="button" className="icon-btn" aria-label="Close wiring" onClick={onClose}>
            <Icon name="x" size="sm" />
          </button>
        </span>
      </div>
      <div className="wire">
        {header && (
          <div>
            <span className="c">{header}</span>
          </div>
        )}
        <Json value={message ?? {}} />
        {footnote && (
          <div>
            <span className="c">{footnote}</span>
          </div>
        )}
      </div>
      <div className="row small" role="status">
        {state === "verified" && <Badge kind="signed" label="Verified" />}
        {state === "broken" && (
          <span className="badge" style={{ background: "var(--bad-bg)", color: "var(--bad-fg)" }}>
            Chain broken
          </span>
        )}
        {state === "inspecting" && <span className="st blue">{"↳"} inspecting</span>}
        <button
          type="button"
          className="btn btn-sm btn-ghost"
          onClick={onVerify}
          disabled={!onVerify}
        >
          Verify
        </button>
        <button type="button" className="btn btn-sm btn-ghost" onClick={onCopy}>
          Copy JSON
        </button>
      </div>
    </aside>
  );
}
