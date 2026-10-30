// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { ShellIcon } from "./shell";
import { Frame, label, list, number, text, type View } from "./ui";
import "./doors.css";

export function MessageDoor({ p, send }: View) {
  const [intro, ...closing] = text(p.text).split("\n\n");
  const selected = list(p.choices).find((choice) => choice.selected === true);
  const [reply, setReply] = useState(selected ? String(number(selected.n)) : "");
  const [draft, setDraft] = useState("");
  return (
    <Frame name="MessageDoor">
      <header>
        <span className="f02-channel-avatar">C</span>
        <div>
          <b>CoalitionKit</b>
          <small>business account · test number</small>
        </div>
      </header>
      <div className="f02-chat-in">
        <p>{intro}</p>
        {list(p.choices).map((choice) => (
          <button
            type="button"
            className="f02-message-choice"
            aria-label={`${number(choice.n)} · ${label(choice)}`}
            key={text(choice.value)}
            onClick={() => {
              setReply(String(number(choice.n)));
              send("reply", { n: choice.n, value: choice.value });
            }}
          >
            <b>{number(choice.n)}</b> {label(choice)}
          </button>
        ))}
        <span>
          Reply{" "}
          <b>
            {list(p.choices)
              .map((choice) => number(choice.n))
              .join(", ")}
          </b>{" "}
          or{" "}
          <button
            type="button"
            className="f02-inline-action"
            onClick={() => send("reply", { n: "?" })}
          >
            ?
          </button>{" "}
          to ask. {closing.join("\n\n")}
        </span>
      </div>
      {reply && <div className="f02-chat-out">{reply}</div>}
      {Boolean(selected?.confirmation) && reply === String(number(selected?.n)) && (
        <div className="f02-chat-in">{text(selected?.confirmation)}</div>
      )}
      {p.receipt && (!selected || reply === String(number(selected.n))) ? (
        <div className="f02-chat-in">
          <span className="ck-meta">receipt {text(p.receipt)}</span>
        </div>
      ) : null}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (draft.trim()) {
            setReply(draft);
            send("reply", { n: draft });
            setDraft("");
          }
        }}
      >
        <input
          aria-label="Message"
          placeholder="Message"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button type="submit" aria-label="Send reply" disabled={!draft.trim()}>
          <ShellIcon name={draft ? "Send" : "Microphone"} />
        </button>
      </form>
    </Frame>
  );
}

export function LensCard({ p, send }: View) {
  const [ack, setAck] = useState(false);
  return (
    <Frame name="LensCard" state={ack ? "acknowledged" : "shown"}>
      <span className="ck-meta">{text(p.eyebrow)}</span>
      <h2>{text(p.title)}</h2>
      <p>{text(p.body)}</p>
      <div className="f02-lens-gestures">
        {["Tap", "Swipe"].slice(0, Math.min(2, number(p.gestures, 1))).map((name) => (
          <button
            className="f02-chip"
            type="button"
            key={name}
            aria-label={`${name}: ${name === "Tap" ? "on my way" : "next"}`}
            onClick={() => {
              setAck(true);
              send("gesture", { name });
            }}
          >
            {name === "Tap" ? "Pinch: on my way" : "Swipe: next"}
          </button>
        ))}
      </div>
    </Frame>
  );
}

const waveform = [10, 22, 30, 18, 26, 12, 28, 16, 22, 10, 26, 14, 20, 8, 18, 24].map(
  (height, position) => ({ id: `bar-${position}`, height, active: position < 8 }),
);
export function VoiceTurn({ p, send }: View) {
  const [choice, setChoice] = useState<unknown>();
  const choices = list(p.choices);
  const transcript = choices.find((item) => item.transcript)?.transcript;
  const script = text(p.script);
  const prompt = script.lastIndexOf("Say ");
  return (
    <Frame name="VoiceTurn" state={choice === undefined ? "speaking" : "confirming"}>
      <div className="f02-voice-card">
        <header>
          <i className="f02-live" />
          <b>{choice === undefined ? "Speaking" : "Confirm your choice"}</b>
          <small>earcon: {text(p.earcon)}</small>
        </header>
        <div className="f02-wave" aria-hidden="true">
          {waveform.map(({ id, height, active }) => (
            <i key={id} style={{ height }} data-on={active} />
          ))}
        </div>
        <p>
          "
          {prompt < 0 ? (
            script
          ) : (
            <>
              {script.slice(0, prompt)}
              <b>{script.slice(prompt)}</b>
            </>
          )}
          "
        </p>
        <hr />
        <dl>
          <dt>Listens for</dt>
          <dd>
            {choices.map((item) => (
              <button
                type="button"
                className="f02-inline-action"
                key={text(item.value)}
                onClick={() =>
                  p.confirm ? setChoice(item.value) : send("voice.choice", { value: item.value })
                }
              >
                {Array.isArray(item.words) ? item.words.map(text).join(" · ") : label(item)}
              </button>
            ))}
            <button
              type="button"
              className="f02-inline-action"
              aria-label="Tell me more"
              onClick={() => send("voice.more")}
            >
              more
            </button>
            <span>stop</span>
          </dd>
          <dt>Confirms</dt>
          <dd>{p.confirm ? "repeats the choice, then signs" : "repeats the choice"}</dd>
          <dt>Timeout</dt>
          <dd>8 s, then asks once more</dd>
        </dl>
        {choice !== undefined && (
          <button
            type="button"
            className="ck-action ck-primary"
            onClick={() => {
              send("voice.choice", { value: choice });
              setChoice(undefined);
            }}
          >
            Confirm {text(choice)}
          </button>
        )}
      </div>
      {Boolean(transcript) && (
        <div className="f02-transcript">
          <span>Transcript</span>
          <small>{text(transcript)}</small>
        </div>
      )}
    </Frame>
  );
}
