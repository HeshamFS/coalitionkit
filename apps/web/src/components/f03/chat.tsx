// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Frame, list, number, obj, text, type View } from "../f02/ui";

export function Message({ p, send }: View) {
  const state = text(p.state) || "delivered";
  const hidden = state === "redacted" || state === "blocked";
  return (
    <Frame name="Message" state={state}>
      <div className={`f03-bubble ${hidden ? "f03-in" : "f03-out"}`}>
        {state === "blocked" ? (
          <>
            Blocked by the steward:{" "}
            {text(p.policy).replace(/^no-/, "").replaceAll("-", " ") || "policy restriction"}
          </>
        ) : state === "redacted" ? (
          <span role="img" aria-label="Redacted content">
            {list(p.projection ?? p.redactions).map((part, i) =>
              part.text ? (
                <span key={String(i)}>{text(part.text)}</span>
              ) : (
                <span
                  className="f03-redaction"
                  key={text(part.id) || String(i)}
                  style={{
                    width: Math.min(
                      160,
                      Math.max(12, number(part.width, number(part.length, 10) * 7)),
                    ),
                  }}
                />
              ),
            )}
            {!list(p.projection ?? p.redactions).length && <span className="f03-redaction" />}
          </span>
        ) : (
          text(p.text)
        )}
        {state === "sending" && <span className="f03-spinner" aria-hidden="true" />}
      </div>
      {state === "failed" ? (
        <span className="f03-message-error">
          Not sent ·{" "}
          <button type="button" onClick={() => send("message.retry")}>
            Retry
          </button>
        </span>
      ) : (
        <span className="f03-message-meta">
          {state === "seen"
            ? `delivered · seen${p.seen_count ? ` by ${number(p.seen_count)}` : ""} ✓✓`
            : state === "redacted"
              ? `${list(p.redactions).length || 1} parts redacted for you${p.scope ? ` · scope ${text(p.scope)}` : ""}`
              : state === "blocked"
                ? `policy ${text(p.policy) || "restricted"}`
                : state}
        </span>
      )}
    </Frame>
  );
}

export function ToolCall({ p, send }: View) {
  const [open, set] = useState(false);
  const state = text(p.state);
  const mark = state === "running" ? "◌" : state === "failed" ? "!" : "✓";
  const toggle = () => {
    set(!open);
    send("toolcall.expand");
  };
  return (
    <Frame name="ToolCall" state={state}>
      <button
        className="f03-tool-head"
        type="button"
        aria-label={`${mark} ${text(p.tool)} · ${state}`}
        aria-expanded={open}
        onClick={toggle}
      >
        {state === "running" ? (
          <span className="f03-spinner" />
        ) : (
          <svg className="ico ico-sm f03-tool-mark" viewBox="0 0 24 24" aria-hidden="true">
            {state === "failed" ? (
              <>
                <circle cx="12" cy="12" r="9" />
                <path d="M8 8l8 8M16 8l-8 8" />
              </>
            ) : (
              <path d="M5 12l5 5 9-10" />
            )}
          </svg>
        )}
        <span>{text(p.tool)}</span>
        <span className="f03-tool-state">
          {state === "done" && p.duration ? `${number(p.duration)} s` : state}
          {state === "failed" && p.failure ? ` · ${text(p.failure)}` : ""}
        </span>
      </button>
      {(p.summary || open) && (
        <div className="f03-tool-body">
          {!!p.summary && (
            <span>
              {p.emphasis && text(p.summary).startsWith(text(p.emphasis)) ? (
                <>
                  <b>{text(p.emphasis)}</b>
                  {text(p.summary).slice(text(p.emphasis).length)}
                </>
              ) : (
                text(p.summary)
              )}
            </span>
          )}
          {!!p.provenance && <span className="st">{text(p.provenance)}</span>}
          {state === "done" && (
            <button className="f03-text-button" type="button" onClick={toggle} aria-expanded={open}>
              Show the call {open ? "▴" : "▾"}
            </button>
          )}
          {open && <pre>{JSON.stringify(p.args ?? {}, null, 2)}</pre>}
        </div>
      )}
    </Frame>
  );
}

export function AgentStatus({ p, send }: View) {
  const state = text(p.state) || "listening";
  const budget = obj(p.budget);
  const used = number(budget.used);
  const cap = number(budget.cap);
  const budgetOnly = !p.state && !!p.budget && !p.task;
  const names: Record<string, string> = {
    listening: "Listening",
    answering: "Answering",
    "needs-you": "Needs you",
    paused: "Paused",
    offline: "Offline",
  };
  return (
    <Frame name="AgentStatus" state={state}>
      <button
        type="button"
        className="f03-status-control"
        data-budget={budgetOnly || undefined}
        aria-label={state === "paused" ? "Resume" : "Pause"}
        onClick={() => send(state === "paused" ? "agent.resume" : "agent.pause")}
      >
        <span className="f03-agent-avatar">Y</span>
        <b>{budgetOnly ? "Budget" : names[state]}</b>
        {state === "answering" && <span className="f03-spinner" />}
        {budgetOnly && (
          <span className="f03-budget">
            €{used} / €{cap}
          </span>
        )}
      </button>
      {!!p.task && <span className="f03-status-task">{text(p.task)}</span>}
      {!!p.budget && (
        <meter
          className="f03-budget-bar"
          aria-label="Agent budget"
          min={0}
          max={Math.max(1, cap)}
          value={used}
        />
      )}
    </Frame>
  );
}
