// SPDX-License-Identifier: Apache-2.0
// The sheet: the dotted ground, the seat ring with an agent dot at each person's seat, the needs
// on the inner ring, the goal at the centre. It is a drawing of the room's real state; the motion
// comes from `room.activity`, `common`, `stops` and `change` and from nothing else.
import { type ReactNode, useLayoutEffect, useRef, useState } from "react";
import { Logo } from "../landing/marks";
import { changeLine, commonLine } from "./beams";
import { captionFor } from "./caption";
import { fitScale, type Layout } from "./geometry";
import { needStatus } from "./needWords";
import { SharedSets } from "./psi/SharedSets";
import type { Room } from "./room";
import { Beams, Crossing, StopBeam, Waves } from "./StageLayers";
import { GoalDisc, NeedNode, SeatNode, seatColor } from "./StageNodes";
import { useCurrentStop, useStageFx } from "./useStageFx";

/** The scale that fits the stage into the room the sheet has left, measured on the sheet itself. */
function useFit(layout: Layout) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(layout.compact ? 0.85 : 0.7);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const width = el.clientWidth || layout.W;
      const height = layout.compact ? 9999 : el.clientHeight || layout.H;
      setScale(fitScale(width, height, layout));
    };
    measure();
    const watch = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure);
    watch?.observe(el);
    window.addEventListener("resize", measure);
    return () => {
      watch?.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [layout]);
  return { ref, scale };
}

const reachOf = (room: Room, plansUp: boolean) =>
  room.phase === "gather" ? 150 : room.lights === "night" ? 470 : plansUp ? 340 : 240;

export function NeedList({ room }: { room: Room }) {
  if (room.needs.length === 0) return null;
  return (
    <ol className="tb-needlist" aria-label="What needs doing">
      {room.needs.map((n, i) => (
        <li key={n.id} data-done={n.result !== null}>
          <span>{i + 1}</span>
          <b>{n.title}</b>
          <small>{needStatus(n.status, n.offers, n.kind)}</small>
        </li>
      ))}
    </ol>
  );
}

function StageContents({
  room,
  layout,
  viewing,
  onSeat,
}: {
  room: Room;
  layout: Layout;
  viewing: string | null;
  onSeat: (seat: string) => void;
}) {
  const ended = room.phase === "ended";
  const fx = useStageFx(room, layout);
  const {
    centre,
    home,
    needPts,
    list,
    busy,
    making,
    beams,
    moved,
    crossing,
    wave,
    waveFrom,
    stops,
    initialNeeds,
    initialSeats,
  } = fx;

  const lit = ["commit", "make", "live", "ended"].includes(room.phase);
  const commonText = commonLine(room);
  const counter = changeLine(room);

  return (
    <>
      <Beams beams={ended ? [] : beams} />
      {crossing && !ended && (
        <Crossing
          seats={list.filter((s) => s.kind !== "open").map((s) => home.get(s.seat) ?? centre)}
          centre={centre}
          loop={crossing === "forever" ? "forever" : "once"}
        />
      )}
      {wave && !ended && <Waves origin={waveFrom} loop={wave} layout={layout} />}
      {!ended &&
        stops.map((x) => (
          <StopBeam key={x.stop.id} from={x.from} toward={x.toward} current={x.current} />
        ))}
      {!ended && <GoalDisc at={centre} text={lit ? "plan signed" : "goal"} lit={lit} />}
      {ended && (
        <div className="tb-mark" style={{ left: centre.x, top: centre.y }}>
          <Logo size={layout.compact ? 84 : 120} />
          <span>done</span>
        </div>
      )}
      {room.needs.map((n, i) => (
        <NeedNode
          key={n.id}
          need={n}
          index={i}
          at={needPts.get(n.id) ?? centre}
          compact={layout.compact}
          hit={moved.has(n.id)}
          making={making.has(n.id)}
          fresh={!initialNeeds.has(n.id)}
          hidden={ended}
          offers={n.offers}
        />
      ))}
      {list.map((s, i) => (
        <SeatNode
          key={s.seat}
          seat={s}
          at={ended ? centre : (home.get(s.seat) ?? centre)}
          color={seatColor(s, i)}
          viewing={viewing === s.seat}
          stops={room.stops.filter((x) => x.seat === s.seat)}
          fresh={!initialSeats.has(`${s.seat}:${s.kind}`)}
          busy={busy.has(s.seat)}
          fold={ended}
          onPick={() => onSeat(s.seat)}
        />
      ))}
      {commonText && !ended && (
        <div className="tb-chipnote" style={{ left: layout.W * 0.6, top: layout.H - 40 }}>
          {commonText}
        </div>
      )}
      {counter && !ended && (
        <div className="tb-counter" style={{ left: layout.W * 0.6, top: layout.H - 12 }}>
          {counter}
        </div>
      )}
    </>
  );
}

export function Stage({
  room,
  layout,
  viewing,
  onSeat,
  plans,
  plansCount,
  waiting,
  tray,
}: {
  room: Room;
  layout: Layout;
  viewing: string | null;
  onSeat: (seat: string) => void;
  /** Plan cards laid under the stage while people decide (wide layout only). */
  plans: ReactNode;
  plansCount: number;
  /** Something is waiting for this viewer's yes or answer. */
  waiting: boolean;
  tray: ReactNode;
}) {
  const decide = room.phase === "decide";
  const { ref, scale } = useFit(layout);
  const steward = useCurrentStop(room);
  const caption = captionFor(room, { plans: plansCount, waiting });
  return (
    <main className="tb-sheet" aria-label="The table">
      <div className="tb-dots" />
      <div className="tb-heat" style={{ "--reach": `${reachOf(room, decide)}px` } as never} />
      <div className="tb-caption" role="status" aria-live="polite">
        <span className="tb-plate">
          {caption.text}
          <small>{caption.sub}</small>
        </span>
      </div>
      <div
        className="tb-stagewrap"
        ref={ref}
        style={layout.compact ? { height: Math.round(layout.H * scale) } : undefined}
      >
        <div
          className="tb-stage"
          data-ended={room.phase === "ended"}
          style={{
            width: layout.W,
            height: layout.H,
            transform: `translateX(-50%) scale(${scale})`,
          }}
        >
          <StageContents room={room} layout={layout} viewing={viewing} onSeat={onSeat} />
        </div>
      </div>
      {decide && !layout.compact && <div className="tb-planstrip">{plans}</div>}
      {steward && room.phase !== "ended" && (
        <p className="tb-stewardbar" role="status">
          <b>Stopped by the Steward</b>
          <code>{steward.policy}</code>
          {steward.explain && <span>{steward.explain}</span>}
        </p>
      )}
      {room.phase !== "ended" && <SharedSets room={room} />}
      {layout.compact && <NeedList room={room} />}
      {tray}
      {room.checked > 0 && <div className="tb-stamp">{room.checked} events checked</div>}
    </main>
  );
}
