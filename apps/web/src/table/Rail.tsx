// SPDX-License-Identifier: Apache-2.0
// The rail: where the room is (status only; nothing here moves it) and the one box to say
// anything to your agent or the room. The host decides where a sentence goes, and says where.
import { type FormEvent, useState } from "react";
import { problemText, type SayReply } from "./api";
import { useTable } from "./context";
import { MOMENTS, momentIndex } from "./phase";
import type { Room } from "./room";

const WHERE: Record<SayReply["route"], string> = {
  private: "Kept private. Only your agent has it.",
  room: "Told the room.",
  change: "Sent as a change. Only what it touches will move.",
  other: "",
};

export function Moments() {
  const { room } = useTable();
  const now = momentIndex(room);
  return (
    <ol className="tb-beads" aria-label="Moments in the room">
      {MOMENTS.map((label, i) => (
        <li
          key={label}
          className="tb-bead"
          data-state={i < now ? "past" : i === now ? "now" : "next"}
          aria-current={i === now ? "step" : undefined}
        >
          <i />
          {label}
        </li>
      ))}
    </ol>
  );
}

/** Why the box is closed, from this viewer's own seat. Null when they may speak. */
export function sayLock(room: Room): string | null {
  const me = room.seats.find((s) => s.you);
  if (room.phase === "ended") return "The room has ended";
  if (!me?.signed) return "Take your seat to speak";
  if (room.phase === "gather") return "Waiting for the room to begin";
  return null;
}

export function Say() {
  const { room, io, setSaid } = useTable();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const lock = sayLock(room);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const said = text.trim();
    if (!said || busy) return;
    setBusy(true);
    const r = await io.say(said);
    setBusy(false);
    if (!r.ok) {
      setSaid({ text: said, error: problemText(r) });
      return;
    }
    setSaid({ text: said, reply: r.data });
    setText("");
  };

  return (
    <form className="tb-say" onSubmit={submit}>
      <label className="tb-sr" htmlFor="tb-say">
        Tell your agent or the room
      </label>
      <input
        id="tb-say"
        type="text"
        maxLength={500}
        value={text}
        disabled={lock !== null}
        placeholder={lock ?? "Tell your agent, or the room"}
        onChange={(e) => setText(e.target.value)}
      />
      <button type="submit" className="btn" disabled={lock !== null || busy || text.trim() === ""}>
        {busy ? "Sending…" : "Say"}
      </button>
    </form>
  );
}

/** What you last said and where it went. It sits on your side, so the footer never grows. */
export function SayNote() {
  const { said, setSaid } = useTable();
  if (!said) return null;
  const r = said.reply;
  return (
    <section className="tb-saynote" role="status" aria-live="polite" aria-label="What you said">
      <span className="tb-tag">You said</span>
      <p className="tb-said">{said.text}</p>
      {said.error ? (
        <p role="alert" className="tb-bad">
          {said.error}
        </p>
      ) : (
        r && (
          <p>
            <b data-stopped={r.stopped === true}>
              {r.stopped ? "Stopped by the Steward." : WHERE[r.route]}
            </b>
            {r.reply && <> {r.reply}</>}
          </p>
        )
      )}
      <button type="button" className="tb-linky" onClick={() => setSaid(null)}>
        Dismiss
      </button>
    </section>
  );
}
