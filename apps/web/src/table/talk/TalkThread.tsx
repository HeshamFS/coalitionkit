// SPDX-License-Identifier: Apache-2.0
// The thread panel: every line the agents said, in order, drawn with the catalog's
// `CoalitionThread`. It says whether the room is talking now, which round it is in, whose offers
// moved because of the talk, and the viewer's own whisper while their agent has not said it yet.
import { useEffect, useRef } from "react";
import { CoalitionThread } from "../../components/f03/thread";
import { useTable } from "../context";
import type { RoomSeat } from "../room";
import { EMPTY_TALK, INTENT_WORDS, type Talk, type TalkLine } from "./talk";
import "./talk.css";

const seatVar = (seats: RoomSeat[], seat: string) => {
  const people = seats.filter((s) => s.kind !== "open");
  const i = people.findIndex((s) => s.seat === seat);
  return i < 0 ? "seat-3" : `seat-${(i % 4) + 1}`;
};

function nameOf(seats: RoomSeat[], seat: string): string {
  const s = seats.find((x) => x.seat === seat);
  if (!s) return "An agent";
  return s.you ? "Your agent" : `${s.label}'s agent`;
}

function message(line: TalkLine, seats: RoomSeat[]) {
  const to = line.to === "room" ? "everyone" : nameOf(seats, line.to).replace(/'s agent$/, "");
  const name = nameOf(seats, line.from);
  return {
    id: line.id,
    author: {
      label: name,
      kind: "agent",
      seat: seatVar(seats, line.from),
      initial: name.slice(0, 1),
      role: INTENT_WORDS[line.intent],
    },
    text: `To ${to}: ${line.text}`,
    time: line.stage === "change" ? "after the change" : `#${line.seq}`,
  };
}

function status(talk: Talk): string {
  if (talk.open) {
    const round = talk.rounds > 1 ? `round ${talk.round} of ${talk.rounds}` : "one round";
    const waiting = talk.waiting_for.length
      ? `, waiting for ${talk.waiting_for.length} outside agent${talk.waiting_for.length === 1 ? "" : "s"}`
      : "";
    return `The agents are talking (${round}${waiting}). Plans come after.`;
  }
  return talk.thread.length ? "The agents talked before the plans." : "";
}

export function TalkThread() {
  const { room } = useTable();
  const talk = room.talk ?? EMPTY_TALK;
  const box = useRef<HTMLElement>(null);
  const count = talk.thread.length;
  // Where the thread scrolls in its own share (a wide window), keep the newest line in view.
  useEffect(() => {
    const el = box.current;
    if (el && count > 0) el.scrollTop = el.scrollHeight;
  }, [count]);
  if (!talk.open && talk.thread.length === 0 && !talk.mine.whisper) return null;
  // Only the newest few: the full list of revisions is in the log.
  const moved = talk.revised.slice(-3).map((r) => {
    const titles = r.needs.map((id) => room.needs.find((n) => n.id === id)?.title ?? "a need");
    return `${nameOf(room.seats, r.seat)} changed its offer on ${titles.join(" and ")}.`;
  });
  return (
    <section
      ref={box}
      className="tk-thread"
      aria-label="What the agents said"
      data-open={talk.open}
    >
      <header>
        <h3>The agents talk</h3>
        <p role="status">{status(talk)}</p>
      </header>
      <CoalitionThread
        p={{ messages: talk.thread.map((line) => message(line, room.seats)) }}
        send={() => undefined}
      />
      {moved.length > 0 && (
        <ul className="tk-moved" aria-label="Offers changed by the talk">
          {moved.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      )}
      {talk.mine.whisper && (
        <p className="tk-whisper">
          Your agent will say this next: <q>{talk.mine.whisper}</q>
        </p>
      )}
    </section>
  );
}
