// SPDX-License-Identifier: Apache-2.0
// The talk on the ring: a beam from the speaker to the seat a line is for (or to the goal when it
// is for the whole room), and a bubble by each speaker holding their newest line. Drawn from
// `room.talk` only; with no line said, nothing is on screen.
import { beamBox, type Pt } from "../geometry";
import { beamLines, INTENT_WORDS, latestBySeat, type Talk } from "./talk";
import "./talk.css";

export function TalkLayer({
  talk,
  home,
  centre,
  compact,
}: {
  talk: Talk;
  home: ReadonlyMap<string, Pt>;
  centre: Pt;
  compact: boolean;
}) {
  if (talk.thread.length === 0) return null;
  const newest = talk.thread.at(-1)?.id;
  return (
    <>
      {beamLines(talk).map((line) => {
        const from = home.get(line.from);
        if (!from) return null;
        const to = (line.to !== "room" && home.get(line.to)) || centre;
        const b = beamBox(from, to);
        return (
          <div
            key={line.id}
            className="tb-beam tk-beam"
            data-state="talk"
            data-room={line.to === "room"}
            data-newest={line.id === newest}
            style={{ left: b.x, top: b.y, width: b.w, transform: `rotate(${b.a}deg)` }}
          >
            <i className="tb-bl" />
            {line.id === newest && <i key={line.id} className="tb-spark" data-once="true" />}
          </div>
        );
      })}
      {latestBySeat(talk, compact ? 2 : 3).map((line) => {
        const at = home.get(line.from);
        if (!at) return null;
        const above = at.y > centre.y;
        return (
          <figure
            key={line.id}
            className="tk-bubble"
            data-above={above}
            data-left={at.x > centre.x}
            data-newest={line.id === newest}
            style={{ left: at.x, top: at.y }}
          >
            <figcaption>{INTENT_WORDS[line.intent]}</figcaption>
            <blockquote>{line.text}</blockquote>
          </figure>
        );
      })}
    </>
  );
}
