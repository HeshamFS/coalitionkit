// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Action, Frame, list, num, obj, type Props, rows, str } from "../f05/shared";

const xy = (v: unknown) => {
  const r = obj(v);
  return `${num(r.x ?? r.lng)},${num(r.y ?? r.lat)}`;
};
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
          <g stroke="var(--surface)" strokeWidth="9">
            <path d="M0 120 L600 160 M180 0 L230 330 M420 0 L440 330" />
          </g>
          <g stroke="var(--surface)" strokeWidth="4">
            <path d="M0 60 L600 90 M60 0 L110 330 M300 0 L320 330 M520 0 L560 330 M0 200 L600 230" />
          </g>
          {rows(p.areas).map((a) => (
            <polygon
              key={str(a.label)}
              points={list(a.polygon).map(xy).join(" ")}
              fill="var(--blue-tint)"
              stroke="var(--blue)"
              strokeDasharray="4 3"
            />
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
          {points.map((r) => (
            <g key={str(r.id)}>
              <circle
                cx={num(r.lng)}
                cy={num(r.lat)}
                r="12"
                fill={r.id === p.selected ? "var(--blue)" : "var(--ink-3)"}
              />
              <text x={num(r.lng) + 16} y={num(r.lat) + 4} fill="var(--ink)" fontSize="11">
                {str(r.label)}
              </text>
            </g>
          ))}
          {Boolean(p.you) && (
            <circle
              cx={num(obj(obj(p.you).position).lng)}
              cy={num(obj(obj(p.you).position).lat)}
              r="8"
              fill="var(--blue)"
              stroke="var(--surface)"
              strokeWidth="3"
            />
          )}
        </svg>
        <div className="f07-map-controls">
          <Action onClick={() => setZoom(Math.min(3, zoom + 0.25))}>Zoom in</Action>
          <Action onClick={() => setZoom(Math.max(1, zoom - 0.25))}>Zoom out</Action>
        </div>
      </div>
      {state !== "ready" && (
        <p role="status">{state === "loading" ? "Loading map…" : "No location shared"}</p>
      )}
      <div className="row wrap">
        {points.map((r) => (
          <Action key={str(r.id)} onClick={() => send("map.select", { point: r })}>
            {str(r.label)}
          </Action>
        ))}
        {rows(p.areas).map((a) => (
          <Action key={str(a.label)} onClick={() => send("map.area", { polygon: a.polygon })}>
            {str(a.label)}
          </Action>
        ))}
      </div>
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
  const [query, setQuery] = useState(str(p.query)),
    [picked, setPicked] = useState<unknown>(obj(p.pin).ref);
  return (
    <Frame
      name="PlacePicker"
      state={picked ? "pinned" : list(p.results).length ? "results" : "searching"}
    >
      <label className="col">
        Search places
        <input className="input" value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      {rows(p.results)
        .filter((r) => !query || str(r.place).toLowerCase().includes(query.toLowerCase()))
        .map((r) => (
          <article className={`card ${picked === r.place ? "card-live" : ""}`} key={str(r.place)}>
            <b>{str(r.place)}</b>
            <small>
              {str(r.distance)} · {list(r.facts).map(str).join(" · ")}
            </small>
            <span className="badge b-vault">{str(r.limitCheck)}</span>
            <Action
              onClick={() => {
                setPicked(r.place);
                send("place.pick", { ref: r.place });
              }}
            >
              Use {str(r.place)}
            </Action>
          </article>
        ))}
    </Frame>
  );
}
