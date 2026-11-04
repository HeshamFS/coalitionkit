// SPDX-License-Identifier: Apache-2.0
// A mic mark by a seat whose newest words to the room were said by voice (or a camera mark for a
// photo). It is drawn from `room.activity` entries the host marked with that source and nothing
// else; a new entry bursts once, then the mark stays small until that seat says something else.
import type { Pt } from "../geometry";
import type { Room } from "../room";
import { MicIcon } from "./Buttons";

export type Mark = { seat: string; id: string; source: "voice" | "camera" };

const SPOKEN = new Set(["saying", "changing"]);

/** The newest say or change of each seat, when it came from the phone. */
export function voiceMarks(room: Room): Mark[] {
  const newest = new Map<string, Room["activity"][number]>();
  for (const a of room.activity) {
    if (a.seat && SPOKEN.has(a.verb)) newest.set(a.seat, a);
  }
  const out: Mark[] = [];
  for (const [seat, a] of newest) {
    if (a.via) out.push({ seat, id: a.id, source: a.via });
  }
  return out;
}

export function VoiceMarks({ room, home }: { room: Room; home: ReadonlyMap<string, Pt> }) {
  return (
    <>
      {voiceMarks(room).map((m) => {
        const at = home.get(m.seat);
        if (!at) return null;
        return (
          <span
            key={m.id}
            className="ck-in-mark"
            data-source={m.source}
            style={{ left: at.x + 26, top: at.y - 30 }}
            role="img"
            aria-label={m.source === "voice" ? "said by voice" : "shown with a photo"}
          >
            <i className="ck-in-burst" aria-hidden="true" />
            {m.source === "voice" ? <MicIcon size={14} /> : "◉"}
          </span>
        );
      })}
    </>
  );
}
