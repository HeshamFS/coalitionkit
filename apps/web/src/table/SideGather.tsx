// SPDX-License-Identifier: Apache-2.0
// Arrive: take your seat through the trusted consent sheet, then see who is still to come and, if
// you may, begin. Beginning is the owner's call and the host checks it; the screen only offers it.
import { useState } from "react";
import { AskCard } from "./Asks";
import { problemText } from "./api";
import { useTable } from "./context";

function BeginControls() {
  const { room, io } = useTable();
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");
  if (!room.begin?.can) return null;
  const open = room.begin.open_seats;
  const go = async (helpers: boolean) => {
    setBusy(true);
    setProblem("");
    const r = await io.begin(helpers);
    setBusy(false);
    if (!r.ok) setProblem(problemText(r));
  };
  return (
    <div className="tb-begin">
      <span className="tb-tag">You can begin</span>
      <p>
        {open > 0
          ? `${open} ${open === 1 ? "seat is" : "seats are"} still open. Beginning closes the door.`
          : "Everyone is seated."}
      </p>
      {open > 0 && (
        <button type="button" className="btn" disabled={busy} onClick={() => go(true)}>
          Begin, and let helpers take the open {open === 1 ? "seat" : "seats"}
        </button>
      )}
      <button
        type="button"
        className={open > 0 ? "btn tb-quietbtn" : "btn"}
        disabled={busy}
        onClick={() => go(false)}
      >
        {open > 0 ? "Begin with the people here" : "Begin"}
      </button>
      {open > 0 && (
        <p className="tb-note">
          A helper is an agent, labelled as one everywhere. It never decides for anyone. Not ready?
          Wait: the door stays open until you begin.
        </p>
      )}
      {problem && <p role="alert">{problem}</p>}
    </div>
  );
}

export function SideGather() {
  const { room, requests } = useTable();
  const me = room.seats.find((s) => s.you);
  const charter = requests.find((r) => r.kind === "charter");
  const waiting = room.seats.filter((s) => s.kind !== "open" && !s.signed && !s.you);
  const open = room.seats.filter((s) => s.kind === "open").length;
  if (me && !me.signed) {
    return (
      <>
        {charter ? (
          <AskCard request={charter} />
        ) : (
          <>
            <h2>Take your seat</h2>
            <p role="status">The host has not asked you yet. Your seat opens as soon as it does.</p>
          </>
        )}
      </>
    );
  }
  return (
    <>
      <h2>{me ? "You are seated" : "The table is filling"}</h2>
      <p>
        {waiting.length + open === 0
          ? "Everyone has taken a seat."
          : "Waiting on the others. You can leave: your seat holds."}
      </p>
      <ul className="tb-who" aria-label="Who is still to come">
        {waiting.map((s) => (
          <li key={s.seat}>
            <b>{s.label}</b>
            <span>
              {s.kind === "helper" ? "an agent, waiting to accept" : "has not signed yet"}
            </span>
          </li>
        ))}
        {open > 0 && (
          <li>
            <b>
              {open} open {open === 1 ? "seat" : "seats"}
            </b>
            <span>nobody has taken {open === 1 ? "it" : "them"} yet</span>
          </li>
        )}
      </ul>
      <BeginControls />
    </>
  );
}
