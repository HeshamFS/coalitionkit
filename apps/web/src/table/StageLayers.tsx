// SPDX-License-Identifier: Apache-2.0
// Beams, the blinded crossing, the stopped beam and the wave. Each one is drawn from a real entry
// of the room (an activity, `common`, a stop, `change`); with none, none of these is on screen.
import type { Beam } from "./beams";
import { at, beamBox, type Layout, type Pt } from "./geometry";

const SPARKS = [0, 1, 2];

export function Beams({ beams }: { beams: Beam[] }) {
  return (
    <>
      {beams.map((beam) => {
        const b = beamBox(beam.from, beam.to);
        return (
          <div
            key={beam.key}
            className="tb-beam"
            data-state={beam.state}
            style={{ left: b.x, top: b.y, width: b.w, transform: `rotate(${b.a}deg)` }}
          >
            <i className="tb-bl" />
            {beam.state === "running" &&
              SPARKS.map((k) => (
                <i key={k} className="tb-spark" style={{ animationDelay: `${-k * 0.37}s` }} />
              ))}
            {beam.spark && <i key={beam.id} className="tb-spark" data-once="true" />}
          </div>
        );
      })}
    </>
  );
}

/** Every seat to the centre and back, with nothing visible but the sparks: the vaults compare blind. */
export function Crossing({
  seats,
  centre,
  loop,
}: {
  seats: Pt[];
  centre: Pt;
  loop: "forever" | "once";
}) {
  return (
    <div className="tb-cross" data-loop={loop} aria-hidden="true">
      {seats.map((p, i) => {
        const b = beamBox(p, centre);
        return (
          <div
            // biome-ignore lint/suspicious/noArrayIndexKey: seats are positional here
            key={i}
            className="tb-beam"
            data-state="cross"
            style={{ left: b.x, top: b.y, width: b.w, transform: `rotate(${b.a}deg)` }}
          >
            <i className="tb-bl" />
            {SPARKS.map((k) => (
              <i
                key={k}
                className="tb-spark"
                data-dir={k % 2 ? "back" : "out"}
                style={{ animationDelay: `${-(k * 0.4 + i * 0.13)}s` }}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}

/** The red beam, stopped part of the way. The rule that stopped it is named in the Steward bar and
 * on the seat's badge, never over the table. */
export function StopBeam({ from, toward, current }: { from: Pt; toward: Pt; current: boolean }) {
  const stuck = at(from, toward, 0.26);
  const b = beamBox(from, toward, 0.26);
  return (
    <>
      <div
        className="tb-beam"
        data-state="stopped"
        data-current={current}
        style={{ left: b.x, top: b.y, width: b.w, transform: `rotate(${b.a}deg)` }}
      >
        <i className="tb-bl" />
      </div>
      <i
        className="tb-spark"
        data-bad="true"
        data-current={current}
        style={{ left: stuck.x, top: stuck.y }}
      />
    </>
  );
}

export function Waves({
  origin,
  loop,
  layout,
}: {
  origin: Pt;
  loop: "forever" | "twice";
  layout: Layout;
}) {
  return (
    <div className="tb-waves" data-loop={loop} aria-hidden="true">
      {[0, 1, 2].map((k) => (
        <span
          key={k}
          className="tb-wave"
          style={{
            left: origin.x,
            top: origin.y,
            width: layout.compact ? 360 : 600,
            height: layout.compact ? 360 : 600,
            animationDelay: `${k * 0.75}s`,
          }}
        />
      ))}
    </div>
  );
}
