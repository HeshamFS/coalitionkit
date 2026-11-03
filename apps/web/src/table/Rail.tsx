// SPDX-License-Identifier: Apache-2.0
// The rail: where the room is (status only; nothing here moves it) and the one box to say
// anything to your agent or the room. The host decides where a sentence goes, and says where.
import { type FormEvent, useState } from "react";
import { problemText, type SayReply } from "./api";
import { useTable } from "./context";
import { MOMENTS, momentIndex } from "./phase";

const WHERE: Record<SayReply["route"], string> = {
  private: "Kept private. Only your agent has it.",
  room: "Told the room.",
  change: "Sent as a change. Only what it touches will move.",
  other: "",
};

type Exchange = { said: string; reply: SayReply };

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

export function Say() {
  const { room, io } = useTable();
  const me = room.seats.find((s) => s.you);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<Exchange | null>(null);
  const [problem, setProblem] = useState("");
  const locked = room.phase === "ended" || room.phase === "gather" || !me?.signed;
  const why = room.phase === "ended" ? "The room has ended" : "Take your seat to speak";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const said = text.trim();
    if (!said || busy) return;
    setBusy(true);
    setProblem("");
    const r = await io.say(said);
    setBusy(false);
    if (!r.ok) {
      setProblem(problemText(r));
      return;
    }
    setLast({ said, reply: r.data });
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
        disabled={locked}
        placeholder={locked ? why : "Tell your agent, or the room"}
        onChange={(e) => setText(e.target.value)}
      />
      <button type="submit" className="btn" disabled={locked || busy || text.trim() === ""}>
        {busy ? "Sending…" : "Say"}
      </button>
      <div className="tb-sayreply" role="status" aria-live="polite">
        {problem && <span role="alert">{problem}</span>}
        {!problem && last && (
          <>
            <b data-stopped={last.reply.stopped === true}>
              {last.reply.stopped ? "Stopped by the Steward." : WHERE[last.reply.route]}
            </b>
            {last.reply.reply && <span> {last.reply.reply}</span>}
          </>
        )}
      </div>
    </form>
  );
}
