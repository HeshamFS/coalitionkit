// SPDX-License-Identifier: Apache-2.0
// An invitation held up as a QR: the code inside the room's ring of seats. The link holds the
// secret, so it stays in the drawing and the clipboard and is never written out on the page.
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { PLATE, qrShapes, SEAT_RING, seatSpots, VIEW } from "./qr";
import "./door.css";

export function RoomQr({ link, seats, taken }: { link: string; seats: number; taken: number }) {
  const { marks, goal } = useMemo(() => qrShapes(link), [link]);
  return (
    <svg
      className="dr-qr"
      viewBox={`0 0 ${VIEW} ${VIEW}`}
      role="img"
      aria-label={`QR code for this invitation, in a ring of ${seats} seats, ${taken} taken`}
    >
      <circle className="dr-disc" cx={VIEW / 2} cy={VIEW / 2} r={SEAT_RING} />
      {seatSpots(seats).map((s, i) => (
        <circle key={`${s.x}-${s.y}`} cx={s.x} cy={s.y} r={s.r} data-taken={i < taken} />
      ))}
      <rect
        className="dr-plate"
        x={PLATE.x}
        y={PLATE.y}
        width={PLATE.size}
        height={PLATE.size}
        rx={PLATE.radius}
      />
      <g className="dr-modules">
        {marks.map((m) =>
          m.kind === "dot" ? (
            <circle key={`${m.x}-${m.y}`} cx={m.x} cy={m.y} r={m.r} />
          ) : (
            <rect key={`${m.x}-${m.y}`} x={m.x} y={m.y} width={m.size} height={m.size} />
          ),
        )}
      </g>
      <circle className="dr-plate" cx={goal.x} cy={goal.y} r={goal.clear} />
      <circle className="dr-goal" cx={goal.x} cy={goal.y} r={goal.dot} />
    </svg>
  );
}

export function QrCard({
  link,
  goal,
  seats,
  onClose,
}: {
  link: string;
  goal: string;
  seats: number;
  onClose: () => void;
}) {
  const card = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    card.current?.querySelector<HTMLButtonElement>("[data-close]")?.focus();
  }, []);
  return createPortal(
    // The keys belong to the dialog as a whole: Escape closes, and Tab stays inside it.
    <div
      className="dr-scrim"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dr-title"
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
        if (e.key !== "Tab") return;
        const stops = [...(card.current?.querySelectorAll("button") ?? [])];
        const at = stops.indexOf(document.activeElement as HTMLButtonElement);
        e.preventDefault();
        stops[(at + (e.shiftKey ? stops.length - 1 : 1)) % stops.length]?.focus();
      }}
    >
      <div className="dr-card" ref={card}>
        <RoomQr link={link} seats={seats} taken={1} />
        <div className="dr-side">
          <span className="dr-eyebrow">Hold this up</span>
          <h2 id="dr-title">Scan to take a seat</h2>
          {goal && <p className="dr-goal-line">{goal}</p>}
          <p>No app needed. Any phone camera works. This QR seats one person.</p>
          <div className="dr-actions">
            <button
              type="button"
              className="dr-btn"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(link);
                  setCopied(true);
                } catch {
                  setCopied(false);
                }
              }}
            >
              {copied ? "Copied" : "Copy link"}
            </button>
            <button type="button" className="dr-btn dr-primary" data-close onClick={onClose}>
              Done
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
