// SPDX-License-Identifier: Apache-2.0
import "./thread.css";
import { Action, Frame, label, list, obj, text, type View } from "../f02/ui";

export function CoalitionThread({ p, send }: View) {
  const messages = list(p.messages);
  return (
    <Frame name="CoalitionThread" state={messages.length ? "streaming" : "empty"}>
      {messages.map((message, index) => {
        const author = obj(message.author);
        const card = obj(message.card);
        const name = text(author.label ?? message.author);
        if (message.kind === "separator")
          return (
            <div className="f03-thread-date" key={text(message.id)}>
              <span />
              {text(message.text)}
              <span />
            </div>
          );
        if (author.kind === "steward")
          return (
            <div className="f03-thread-system" key={text(message.id)}>
              <span>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 3l8 4v6c0 4-3.5 7-8 8-4.5-1-8-4-8-8V7z" />
                </svg>
                {text(message.text)}
              </span>
            </div>
          );
        return (
          <div className="f03-thread-turn" key={text(message.id) || String(index)}>
            <span
              className={`f03-thread-avatar ${author.kind === "agent" ? "f03-square" : ""}`}
              style={{ background: `var(--${text(author.seat) || "seat-1"})` }}
            >
              {text(author.initial) || name.slice(0, 1)}
            </span>
            <div className="f03-thread-content">
              <div className="f03-thread-author">
                <b>{name}</b>
                {!!author.role && <span className="badge b-model">{text(author.role)}</span>}
                <span className="f03-thread-time">{text(message.time)}</span>
              </div>
              <button
                className="f03-thread-text"
                type="button"
                onClick={() => send("message.open", { id: message.id })}
              >
                {text(message.text)}
                {message.streaming === true && <span className="f03-thread-caret" />}
              </button>
              {!!message.card && (
                <div className="f03-thread-card">
                  <div className="f03-thread-author">
                    <b>{text(card.title)}</b>
                    <span className="scope">{text(message.scope)}</span>
                  </div>
                  <span>{text(card.summary)}</span>
                  <div>
                    <Action onClick={() => send("message.open", { id: message.id })}>
                      {text(card.action) || "Open"}
                    </Action>
                  </div>
                </div>
              )}
              {list(message.attachments).map((item) => (
                <span key={label(item)}>{label(item)}</span>
              ))}
            </div>
          </div>
        );
      })}
      {!messages.length && <p>No messages yet.</p>}
      {list(p.typing).map((person) => (
        <div className="f03-thread-typing" key={label(person)}>
          <span className="f03-thread-avatar" style={{ background: "var(--seat-3)" }}>
            {text(person.initial) || label(person).slice(0, 1)}
          </span>
          <span aria-hidden="true" className="f03-typing-dots">
            ● ● ●
          </span>
          {text(person.status) || `${label(person)} typing…`}
        </div>
      ))}
    </Frame>
  );
}
