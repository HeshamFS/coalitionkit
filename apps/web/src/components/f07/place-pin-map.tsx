// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import "./place-pin-map.css";
import { num, type Props, str } from "../f05/shared";

/** Coordinates are in the illustrative plan's 280 × 260 coordinate space. */
export function PlacePinMap({
  results,
  picked,
  pin,
  send,
}: {
  results: Record<string, unknown>[];
  picked: unknown;
  pin: Record<string, unknown>;
  send: Props["send"];
}) {
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [dragging, setDragging] = useState(false);
  const selected = results.findIndex((r) => r.place === picked);
  const initial = {
    x:
      pin.x == null || picked !== pin.ref
        ? ([150, 60, 236][Math.max(0, selected) % 3] ?? 150)
        : num(pin.x),
    y:
      pin.y == null || picked !== pin.ref
        ? ([96, 170, 40][Math.max(0, selected) % 3] ?? 96)
        : num(pin.y),
  };
  const position = positions[str(picked)] ?? initial;
  const move = (x: number, y: number, commit = false) => {
    const next = { x: Math.max(14, Math.min(266, x)), y: Math.max(14, Math.min(236, y)) };
    setPositions((previous) => ({ ...previous, [str(picked)]: next }));
    if (commit) send("place.adjust", { ref: picked, ...next });
  };
  return (
    <div className="f07-pin-map">
      <svg
        viewBox="0 0 280 260"
        aria-label="Place search map"
        onPointerMove={(event) => {
          if (!dragging) return;
          const point = new DOMPoint(event.clientX, event.clientY);
          const matrix = event.currentTarget.getScreenCTM();
          if (matrix) {
            const local = point.matrixTransform(matrix.inverse());
            move(local.x, local.y);
          }
        }}
        onPointerUp={() => {
          if (dragging) move(position.x, position.y, true);
          setDragging(false);
        }}
        onPointerCancel={() => setDragging(false)}
      >
        <g stroke="var(--surface)" strokeWidth="7">
          <path d="M0 90 280 120M110 0 130 260" />
        </g>
        <g stroke="var(--surface)" strokeWidth="3">
          <path d="M0 200 280 210M220 0 240 260" />
        </g>
        {results.map((result, index) => {
          const active = picked === result.place;
          const point = active
            ? position
            : (positions[str(result.place)] ?? {
                x: [150, 60, 236][index % 3],
                y: [96, 170, 40][index % 3],
              });
          return (
            <g key={str(result.place)} transform={`translate(${point.x} ${point.y})`}>
              <path
                d={
                  active
                    ? "M-14 0a14 14 0 1 1 28 0c0 11-14 24-14 24S-14 13-14 0"
                    : "M-9 0a9 9 0 1 1 18 0c0 7-9 15-9 15S-9 8-9 0"
                }
                fill={active ? "var(--blue)" : "var(--ink-3)"}
              />
              {active && (
                <>
                  <circle r="5" fill="var(--on-blue)" />
                  <PinHandle
                    picked={picked}
                    position={position}
                    move={move}
                    startDrag={() => setDragging(true)}
                  />
                </>
              )}
            </g>
          );
        })}
      </svg>
      <div className="f07-pin-actions">
        <span className="dock">Drag the pin to adjust</span>
        <button
          type="button"
          className="btn btn-sm btn-primary"
          disabled={!picked}
          onClick={() => send("place.pick", { ref: picked })}
        >
          Use this place
        </button>
      </div>
    </div>
  );
}

function PinHandle({
  picked,
  position,
  move,
  startDrag,
}: {
  picked: unknown;
  position: { x: number; y: number };
  move: (x: number, y: number, commit: boolean) => void;
  startDrag: () => void;
}) {
  return (
    <foreignObject x="-18" y="-18" width="36" height="44">
      <button
        type="button"
        className="f07-pin-handle"
        aria-label={`Adjust ${str(picked)} pin`}
        onPointerDown={(event) => {
          event.currentTarget.setPointerCapture(event.pointerId);
          startDrag();
        }}
        onKeyDown={(event) => {
          const delta: Record<string, [number, number]> = {
            ArrowLeft: [-5, 0],
            ArrowRight: [5, 0],
            ArrowUp: [0, -5],
            ArrowDown: [0, 5],
          };
          const step = delta[event.key];
          if (step) {
            event.preventDefault();
            move(position.x + step[0], position.y + step[1], true);
          }
        }}
      />
    </foreignObject>
  );
}
