// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Action, Frame, list, num, obj, type Props, rows, str } from "../f05/shared";

const xy = (v: unknown) => {
  const r = obj(v);
  return `${num(r.x ?? r.lng)},${num(r.y ?? r.lat)}`;
};
function MapPoints({
  points,
  selected,
  send,
}: {
  points: Record<string, unknown>[];
  selected: unknown;
  send: Props["send"];
}) {
  return (
    <>
      {points.map((r, i) => (
        <g key={str(r.id)} transform={`translate(${num(r.lng)} ${num(r.lat)})`}>
          {i === 0 ? (
            <circle r="11" fill="var(--ink)" />
          ) : (
            <path
              d="M-12 0a12 12 0 1 1 24 0c0 9-12 20-12 20S-12 9-12 0"
              fill={r.id === selected ? "var(--blue)" : "var(--ink-3)"}
            />
          )}
          <text y="4" textAnchor="middle" fill="var(--on-fill)" fontSize="10" fontWeight="700">
            {i === 0 ? "P1" : "P"}
          </text>
          <foreignObject x="-14" y="-14" width="28" height="38">
            <button
              type="button"
              className="f07-map-hit"
              aria-label={str(r.label)}
              onClick={() => send("map.select", { point: r })}
            />
          </foreignObject>
          {r.id === selected && (
            <g>
              <rect
                x="12"
                y="-16"
                width="104"
                height="34"
                rx="6"
                fill="var(--surface)"
                stroke="var(--line)"
              />
              <text x="20" y="-2" fontSize="10" fontWeight="600" fill="var(--ink)">
                {str(r.label)}
              </text>
              <text x="20" y="11" fontSize="10" fill="var(--ink-3)">
                {str(r.ref)}
              </text>
            </g>
          )}
        </g>
      ))}
    </>
  );
}
export function MapView({ p, send }: Props) {
  const points = rows(p.points),
    [zoom, setZoom] = useState(1),
    state = p.points === undefined ? "loading" : points.length ? "ready" : "no-location";
  return (
    <Frame name="MapView" state={state}>
      <div className="f07-map">
        <svg viewBox={`0 0 ${600 / zoom} ${330 / zoom}`} role="img" aria-label="Places and routes">
          <rect width="600" height="330" fill="var(--f07-map)" />
          <path
            d="M0 250 C120 230 200 280 330 240 S520 200 600 220 V330 H0Z"
            fill="var(--f07-water)"
          />
          <g stroke="var(--surface)" strokeWidth="9" fill="none" strokeLinecap="round">
            <path d="M-10 120 L610 160 M180 -10 L230 340 M420 -10 C400 120 470 200 440 340" />
          </g>
          <g stroke="var(--surface)" strokeWidth="4">
            <path d="M0 60 L600 90 M60 0 L110 330 M300 0 L320 330 M520 0 L560 330 M0 200 L600 230" />
          </g>
          {rows(p.areas).map((a) => (
            <g key={str(a.label)}>
              <polygon
                key={str(a.label)}
                points={list(a.polygon).map(xy).join(" ")}
                fill="var(--blue-tint)"
                stroke="var(--blue)"
                strokeDasharray="4 3"
              />
              <foreignObject
                x={num(obj(list(a.polygon)[0]).x) + 8}
                y={num(obj(list(a.polygon)[0]).y) + 8}
                width="120"
                height="20"
              >
                <button
                  type="button"
                  className="f07-map-label"
                  onClick={() => send("map.area", { polygon: a.polygon })}
                >
                  {str(a.label)}
                </button>
              </foreignObject>
            </g>
          ))}
          {rows(p.routes).map((r) => (
            <polyline
              key={str(r.mode)}
              points={list(r.path).map(xy).join(" ")}
              fill="none"
              stroke="var(--blue)"
              strokeWidth="4"
            />
          ))}
          <MapPoints points={points} selected={p.selected} send={send} />
          {Boolean(p.you) && (
            <g>
              <circle
                cx={num(obj(obj(p.you).position).lng)}
                cy={num(obj(obj(p.you).position).lat)}
                r="22"
                fill="var(--blue)"
                opacity=".14"
              />
              <circle
                cx={num(obj(obj(p.you).position).lng)}
                cy={num(obj(obj(p.you).position).lat)}
                r="6"
                fill="var(--blue)"
                stroke="var(--surface)"
                strokeWidth="2"
              />
            </g>
          )}
        </svg>
        <div className="f07-map-legend row">
          <span className="dock">origin</span>
          <span className="dock">in plan</span>
          <span className="dock">other offers</span>
          <span className="dock">you</span>
        </div>
        <div className="f07-map-controls">
          <button
            type="button"
            className="icon-btn"
            aria-label="Zoom in"
            onClick={() => setZoom(Math.min(3, zoom + 0.25))}
          >
            +
          </button>
          <button
            type="button"
            className="icon-btn"
            aria-label="Zoom out"
            onClick={() => setZoom(Math.max(1, zoom - 0.25))}
          >
            −
          </button>
        </div>
      </div>
      {state !== "ready" && (
        <p role="status">{state === "loading" ? "Loading map…" : "No location shared"}</p>
      )}
    </Frame>
  );
}
export function IndoorMap({ p, send }: Props) {
  return (
    <Frame name="IndoorMap">
      <div className="f07-indoor">
        <svg viewBox="0 0 300 250" role="img" aria-label={`Indoor plan ${str(p.plan)}`}>
          <rect
            x="10"
            y="20"
            width="280"
            height="150"
            rx="10"
            fill="var(--surface)"
            stroke="var(--line-strong)"
          />
          {rows(p.rooms).map((r, i) => (
            <g key={str(r.id)}>
              <rect
                x={num(r.x, 24 + i * 68)}
                y={num(r.y, 34)}
                width={num(r.width, 60)}
                height={num(r.height, 38)}
                rx="4"
                fill="var(--surface-3)"
              />
              <text
                x={num(r.x, 24 + i * 68) + 8}
                y={num(r.y, 34) + 22}
                fill="var(--ink-2)"
                fontSize="9"
              >
                {str(r.label)}
              </text>
            </g>
          ))}
          <polyline
            points={list(p.path).map(xy).join(" ")}
            fill="none"
            stroke="var(--blue)"
            strokeWidth="3"
            strokeDasharray="6 4"
          />
          {Boolean(p.you) && (
            <circle cx={num(obj(p.you).x)} cy={num(obj(p.you).y)} r="5" fill="var(--blue)" />
          )}
        </svg>
      </div>
      <div className="row wrap">
        {rows(p.rooms).map((r) => (
          <Action key={str(r.id)} onClick={() => send("map.select", { room: r.id })}>
            {str(r.label)}
          </Action>
        ))}
      </div>
      {rows(p.liveLayers).map((r) => (
        <small key={str(r.label)}>
          {str(r.label)} · {str(r.value)} · {str(r.source)}
        </small>
      ))}
    </Frame>
  );
}
export function PlacePicker({ p, send }: Props) {
  const [query, setQuery] = useState(str(p.query));
  const [picked, setPicked] = useState<unknown>(obj(p.pin).ref);
  return (
    <Frame
      name="PlacePicker"
      state={picked ? "pinned" : list(p.results).length ? "results" : "searching"}
    >
      <div className="f07-picker">
        <div className="col">
          <div className="input f07-search">
            <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-4-4" />
            </svg>
            <input
              aria-label="Search places"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          {rows(p.results)
            .filter((r) => !query || str(r.place).toLowerCase().includes(query.toLowerCase()))
            .map((r) => (
              <button
                type="button"
                className={`card f07-place ${picked === r.place ? "selected" : ""}`}
                key={str(r.place)}
                onClick={() => {
                  setPicked(r.place);
                  send("place.pick", { ref: r.place });
                }}
                aria-label={`Use ${str(r.place)}`}
              >
                <span className="f07-place-image" aria-hidden="true" />
                <span className="col grow">
                  <b>{str(r.place)}</b>
                  <span className="small">
                    {str(r.distance)} km · {list(r.facts).map(str).join(" · ")}
                  </span>
                  <span
                    className={`badge ${r.limitCheck === "over your limit" ? "f07-over" : r.limitCheck === "no limit asked" ? "b-estimate" : "b-vault"}`}
                  >
                    {str(r.limitCheck)}
                  </span>
                </span>
              </button>
            ))}
        </div>
        <div className="f07-pin-map">
          <svg viewBox="0 0 280 260" aria-label="Place search map">
            <g stroke="var(--surface)" strokeWidth="7">
              <path d="M0 90 280 120M110 0 130 260" />
            </g>
            <g stroke="var(--surface)" strokeWidth="3">
              <path d="M0 200 280 210M220 0 240 260" />
            </g>
            {rows(p.results).map((r, i) => {
              const x = [150, 60, 236][i % 3],
                y = [96, 170, 40][i % 3];
              return (
                <g key={str(r.place)} transform={`translate(${x} ${y})`}>
                  <path
                    d="M-12 0a12 12 0 1 1 24 0c0 9-12 20-12 20S-12 9-12 0"
                    fill={picked === r.place ? "var(--blue)" : "var(--ink-3)"}
                  />
                  <circle r="4" fill="var(--on-blue)" />
                </g>
              );
            })}
          </svg>
          <div className="f07-pin-actions">
            <span className="dock">Choose a place</span>
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
      </div>
    </Frame>
  );
}
