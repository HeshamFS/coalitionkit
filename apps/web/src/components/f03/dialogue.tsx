// SPDX-License-Identifier: Apache-2.0
import { Frame, list, number, obj, text, type View } from "../f02/ui";
import "./dialogue.css";

export function NegotiationTheatre({ p, send }: View) {
  return (
    <Frame name="NegotiationTheatre">
      {list(p.events).map((event, index) => {
        const speaker = obj(event.speaker);
        const answer = text(event.type) === "coalition.answer";
        const proposal = text(event.type) === "coalition.propose";
        return (
          <div
            className={`f03-dialogue-turn${answer ? " f03-dialogue-answer" : ""}`}
            key={text(event.event_ref) || String(index)}
          >
            <span
              className="f03-dialogue-avatar"
              style={{ background: `var(--${text(speaker.seat) || "ink"})` }}
            >
              {text(speaker.initial) || text(event.speaker).slice(0, 1)}
            </span>
            <button
              type="button"
              aria-label="Inspect turn"
              className={`f03-dialogue-card${proposal ? " f03-dialogue-proposal" : ""}`}
              onClick={() => send("turn.inspect", { event_ref: event.event_ref })}
            >
              <span className="f03-dialogue-heading">
                <span>{text(event.type)}</span>
                <span>
                  #{text(event.event_ref).split(":").at(-1)} {text(event.audience)}
                </span>
              </span>
              <span className="f03-dialogue-text">
                {answer && text(event.text).includes(".") ? (
                  <>
                    <b>{text(event.text).split(".")[0]}.</b>
                    <span className="f03-dialogue-aside">
                      {text(event.text).slice(text(event.text).indexOf(".") + 1)}
                    </span>
                  </>
                ) : (
                  text(event.text ?? event.summary)
                )}
              </span>
              {proposal && (
                <span className="f03-dialogue-controls">
                  {event.checked === true && <span className="badge b-signed">steward passed</span>}
                  <span className="f03-dialogue-compare">Compare</span>
                </span>
              )}
            </button>
          </div>
        );
      })}
    </Frame>
  );
}

export function DiarizedTranscript({ p, send }: View) {
  const extracted = list(p.extracted);
  return (
    <Frame name="DiarizedTranscript">
      <div className="f03-transcript-lines">
        {list(p.segments).map((segment, index) => {
          const speaker = obj(segment.speaker);
          return (
            <div
              className={`f03-transcript-line${segment.streaming === true ? " f03-transcript-live" : ""}`}
              key={text(segment.id) || String(index)}
            >
              <span className="f03-transcript-time">{text(segment.start)}</span>
              <span
                className="f03-transcript-avatar"
                style={{ background: `var(--${text(speaker.seat) || "seat-1"})` }}
              >
                {text(speaker.initial) || text(segment.speaker).slice(0, 1)}
              </span>
              <div className="f03-transcript-content">
                <span>
                  {text(segment.text)}
                  {segment.streaming === true && <span className="f03-thread-caret" />}
                </span>
                <div className="f03-transcript-chips">
                  {extracted
                    .filter((item) => item.segment === segment.id)
                    .map((item, itemIndex) => (
                      <button
                        type="button"
                        className={`f03-transcript-chip${item.kind === "offer" ? " f03-transcript-captured" : ""}`}
                        key={text(item.id) || String(itemIndex)}
                        onClick={() => send("extract.review", { id: item.id })}
                      >
                        {item.kind === "offer" && (
                          <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M12 5v14M5 12h14" />
                          </svg>
                        )}
                        {text(item.text)}
                      </button>
                    ))}
                </div>
                {!!segment.note && (
                  <span
                    className={
                      segment.private === true ? "f03-transcript-private" : "f03-transcript-note"
                    }
                  >
                    {segment.private === true && (
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <rect x="5" y="11" width="14" height="10" rx="2" />
                        <path d="M8 11V8a4 4 0 0 1 8 0v3" />
                      </svg>
                    )}
                    {text(segment.note)}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <div className="f03-transcript-footer">
        <span>{extracted.length} items to add to the coalition</span>
        <div>
          <button
            className="ck-action"
            type="button"
            aria-label="Review extracted items"
            onClick={() => send("extract.review")}
          >
            Review
          </button>
          <button
            className="ck-action ck-primary"
            type="button"
            disabled={!extracted.length}
            onClick={() =>
              extracted.forEach((item) => {
                send("extract.post", { id: item.id ?? item.segment });
              })
            }
          >
            Add {extracted.length === 2 ? "both" : "items"}
          </button>
        </div>
      </div>
    </Frame>
  );
}

export function CallSummary({ p, send }: View) {
  const groups = [
    ["decided", "Decided", "Agreed"],
    ["needs", "New needs", "Needs you"],
    ["offers", "New offers", "Offered"],
    ["questions", "Open questions", "Private"],
  ];
  return (
    <Frame name="CallSummary">
      <div className="f03-summary-grid">
        {groups
          .filter(([key]) => list(p[key ?? ""]).length)
          .map(([key, title, status]) => (
            <div className="f03-summary-column" key={key}>
              <span>{title}</span>
              {list(p[key ?? ""]).map((item, index) => (
                <button
                  type="button"
                  className="f03-summary-card"
                  aria-label="Review and post"
                  key={text(item.id) || String(index)}
                  onClick={() => send("summary.post", { item })}
                >
                  <b>{text(item.text)}</b>
                  <span>{text(item.detail)}</span>
                  <span
                    className={`tag ${key === "decided" ? "t-agreed" : key === "needs" ? "t-needs" : "t-private"}`}
                  >
                    {status}
                  </span>
                </button>
              ))}
            </div>
          ))}
      </div>
      <div className="f03-summary-footer">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v4l3 2" />
        </svg>
        <span>
          {Math.round(number(p.duration) / 60)} min ·{" "}
          {p.participants ? `${text(p.participants)} · ` : ""}transcript in each speaker's vault
        </span>
        {!!p.transcript && (
          <button
            className="f03-text-button"
            style={{ marginLeft: "auto", flexShrink: 0 }}
            type="button"
            onClick={() => send("transcript.open", { id: p.transcript })}
          >
            Open transcript
          </button>
        )}
      </div>
    </Frame>
  );
}
