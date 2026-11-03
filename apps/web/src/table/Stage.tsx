// SPDX-License-Identifier: Apache-2.0
// The sheet: the dotted ground, the seat ring with an agent dot at each person's seat, the needs
// on the inner ring, the goal at the centre. It is a drawing of the room's real state; the motion
// comes from `room.activity`, `common`, `stops` and `change` and from nothing else.
import { type ReactNode, useLayoutEffect, useRef, useState } from "react";
import { Logo } from "../landing/marks";
import { changeLine, commonLine } from "./beams";
import { captionFor } from "./caption";
import { fitScale, type Layout } from "./geometry";
import { humanStatus } from "./phase";
import type { Room } from "./room";
import { Beams, Crossing, StopBeam, Waves } from "./StageLayers";
import { GoalDisc, NeedNode, SeatNode, seatColor } from "./StageNodes";
import { useCurrentStop, useStageFx } from "./useStageFx";

function useFit(layout: Layout, reserve: number) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(layout.compact ? 0.85 : 0.8);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const width = el.clientWidth || layout.W;
      const height = layout.compact ? 9999 : Math.max(380, window.innerHeight - reserve);
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
  }, [layout, reserve]);
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
          <small>{humanStatus(n.status) || n.kind}</small>
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
  plans,
  plansCount,
}: {
  room: Room;
  layout: Layout;
  viewing: string | null;
  onSeat: (seat: string) => void;
  plans: ReactNode;
  plansCount: number;
}) {
  const decide = room.phase === "decide";
  const ended = room.phase === "ended";
  const fx = useStageFx(room, layout);
  const {
    centre,
    home,
    needPts,
    list,
    where,
    busy,
    making,
    beams,
    moved,
    crossing,
    wave,
    waveFrom,
    stops,
    finished,
    initialNeeds,
    initialSeats,
  } = fx;

  const caption = captionFor(room, plansCount, finished);
  const lit = ["commit", "make", "live", "ended"].includes(room.phase);
  const commonText = commonLine(room);
  const counter = changeLine(room);

  return (
    <>
      <div className="tb-caption" role="status" aria-live="polite">
        {caption.text}
        <small>{caption.sub}</small>
      </div>
      <Beams beams={decide || ended ? [] : beams} />
      {crossing && !decide && !ended && (
        <Crossing
          seats={list.filter((s) => s.kind !== "open").map((s) => home.get(s.seat) ?? centre)}
          centre={centre}
          loop={crossing === "forever" ? "forever" : "once"}
        />
      )}
      {wave && !decide && !ended && <Waves origin={waveFrom} loop={wave} layout={layout} />}
      {!decide &&
        !ended &&
        stops.map((x) => (
          <StopBeam key={x.stop.id} from={x.from} toward={x.toward} current={x.current} />
        ))}
      {!decide && !ended && <GoalDisc at={centre} text={lit ? "plan signed" : "goal"} lit={lit} />}
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
          hidden={decide || ended}
          offers={n.offers}
        />
      ))}
      {list.map((s, i) => (
        <SeatNode
          key={s.seat}
          seat={s}
          at={where(s.seat, i)}
          color={seatColor(s, i)}
          viewing={viewing === s.seat}
          stops={room.stops.filter((x) => x.seat === s.seat)}
          fresh={!initialSeats.has(`${s.seat}:${s.kind}`)}
          busy={busy.has(s.seat)}
          fold={ended}
          onPick={() => onSeat(s.seat)}
        />
      ))}
      {commonText && !decide && !ended && (
        <div className="tb-chipnote" style={{ left: layout.W * 0.6, top: layout.H - 40 }}>
          {commonText}
        </div>
      )}
      {counter && !decide && !ended && (
        <div className="tb-counter" style={{ left: layout.W * 0.6, top: layout.H - 12 }}>
          {counter}
        </div>
      )}
      {decide && !layout.compact && plans}
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
  tray,
}: {
  room: Room;
  layout: Layout;
  viewing: string | null;
  onSeat: (seat: string) => void;
  /** Plan cards drawn over the stage while people decide (wide layout only). */
  plans: ReactNode;
  plansCount: number;
  tray: ReactNode;
}) {
  const decide = room.phase === "decide";
  const { ref, scale } = useFit(layout, 190 + (tray ? 92 : 0) + 56);
  const steward = useCurrentStop(room);
  return (
    <main className="tb-sheet" aria-label="The table">
      <div className="tb-dots" />
      <div className="tb-heat" style={{ "--reach": `${reachOf(room, decide)}px` } as never} />
      <div className="tb-stagewrap" ref={ref} style={{ minHeight: Math.round(layout.H * scale) }}>
        <div
          className="tb-stage"
          data-ended={room.phase === "ended"}
          style={{ width: layout.W, height: layout.H, transform: `scale(${scale})` }}
        >
          <StageContents
            room={room}
            layout={layout}
            viewing={viewing}
            onSeat={onSeat}
            plans={plans}
            plansCount={plansCount}
          />
        </div>
      </div>
      {steward && room.phase !== "ended" && (
        <p className="tb-stewardbar" role="status">
          <b>Stopped by the Steward</b>
          <code>{steward.policy}</code>
          {steward.explain && <span>{steward.explain}</span>}
        </p>
      )}
      {layout.compact && !decide && <NeedList room={room} />}
      {tray}
      {room.checked > 0 && <div className="tb-stamp">{room.checked} events checked</div>}
    </main>
  );
}
