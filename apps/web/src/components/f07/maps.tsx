// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Frame, list, num, obj, type Props, rows, str } from "../f05/shared";
import { PlacePinMap } from "./place-pin-map";

const xy = (v: unknown) => {
  const r = obj(v);
  return `${num(r.x ?? r.lng)},${num(r.y ?? r.lat)}`;
};
const routePath = (path: unknown) =>
  rows(path)
    .map((point, index) =>
      index === 0
        ? `M${xy(point)}`
        : point.control1 && point.control2
          ? `C${xy(point.control1)} ${xy(point.control2)} ${xy(point)}`
          : `L${xy(point)}`,
    )
    .join(" ");
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
              d={
                r.id === selected
                  ? "M-12 0a12 12 0 1 1 24 0c0 9-12 20-12 20S-12 9-12 0"
                  : "M-10 0a10 10 0 1 1 20 0c0 8-10 17-10 17S-10 9-10 0"
              }
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
function MapAreas({ p, send }: Props) {
  return (
    <>
      {rows(p.areas).map((a) => (
        <g key={str(a.label)}>
          <polygon
            key={str(a.label)}
            points={list(a.polygon).map(xy).join(" ")}
            fill="var(--blue)"
            fillOpacity=".1"
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
    </>
  );
}
function MapCanvas({ p, send, zoom }: Props & { zoom: number }) {
  const points = rows(p.points);
  return (
    <svg
      style={{ display: "block", width: "100%", height: "100%" }}
      viewBox={`0 0 ${600 / zoom} ${330 / zoom}`}
      role="img"
      aria-label="Places and routes"
    >
      <rect width="600" height="330" fill="var(--f07-map)" />
      <path d="M0 250 C120 230 200 280 330 240 S520 200 600 220 V330 H0Z" fill="var(--f07-water)" />
      <g stroke="var(--surface)" strokeWidth="9" fill="none" strokeLinecap="round">
        <path d="M-10 120 L610 160 M180 -10 L230 340 M420 -10 C400 120 470 200 440 340" />
      </g>
      <g stroke="var(--surface)" strokeWidth="4">
        <path d="M0 60 L600 90 M60 0 L110 330 M300 0 L320 330 M520 0 L560 330 M0 200 L600 230" />
      </g>
      {points
        .filter((point) => point.kind === "origin")
        .map((point) => (
          <g key={str(point.id)}>
            <rect
              x={num(point.lng) - 80}
              y={num(point.lat) - 50}
              width="120"
              height="80"
              rx="6"
              fill="var(--f07-landmark)"
            />
            <text
              x={num(point.lng) - 68}
              y={num(point.lat) - 30}
              fontSize="10"
              fill="var(--f07-landmark-label)"
            >
              {str(point.label)}
            </text>
          </g>
        ))}
      <MapAreas p={p} send={send} />
      {rows(p.routes).map((r) => (
        <g key={str(r.mode)} fill="none" strokeLinecap="round">
          <path d={routePath(r.path)} stroke="var(--blue)" strokeWidth="4" />
          <path
            d={routePath(r.path)}
            stroke="var(--surface)"
            strokeWidth="2"
            strokeDasharray="3 8"
          />
        </g>
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
  );
}
export function MapView({ p, send }: Props) {
  const points = rows(p.points),
    [zoom, setZoom] = useState(1),
    state = p.points === undefined ? "loading" : points.length ? "ready" : "no-location";
  return (
    <Frame name="MapView" state={state}>
      <div className="f07-map">
        <MapCanvas p={p} send={send} zoom={zoom} />
        <div className="f07-map-legend row">
          <span className="dock">
            <span className="pin f07-origin-pin" />
            origin
          </span>
          <span className="dock">
            <span className="pin f07-plan-pin" />
            in plan
          </span>
          <span className="dock">
            <span className="pin f07-other-pin" />
            other offers
          </span>
          <span className="dock">
            <span className="pin f07-you-pin" />
            you{obj(p.you).accuracy ? `, ±${str(obj(p.you).accuracy)} m` : ""}
          </span>
        </div>
        <span className="st f07-map-credit">illustrative · tiles by the map provider</span>
        <div
          className="f07-map-controls col"
          style={{ position: "absolute", right: 8, top: 8, gap: 2 }}
        >
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
          <button
            type="button"
            className="icon-btn"
            aria-label="Reset map view"
            onClick={() => setZoom(1)}
          >
            <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
            </svg>
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
                fill={
                  r.kind === "exit"
                    ? "var(--ink)"
                    : r.kind === "queue"
                      ? "var(--warn-bg)"
                      : "var(--f07-room)"
                }
                stroke={r.selected ? "var(--blue)" : "none"}
                strokeWidth={r.selected ? 2 : undefined}
              />
              <text
                x={num(r.x, 24 + i * 68) + 8}
                y={num(r.y, 34) + num(r.height, 38) / 2 + 3}
                fill={
                  r.kind === "exit"
                    ? "var(--on-fill)"
                    : r.kind === "queue"
                      ? "var(--warn-fg)"
                      : r.selected
                        ? "var(--blue-text)"
                        : "var(--ink-2)"
                }
                fontSize="9"
                fontWeight={r.selected ? 600 : undefined}
              >
                {str(r.label)}
              </text>
              <foreignObject
                x={num(r.x, 24 + i * 68)}
                y={num(r.y, 34)}
                width={num(r.width, 60)}
                height={num(r.height, 38)}
              >
                <button
                  type="button"
                  className="f07-map-hit"
                  aria-label={str(r.label)}
                  onClick={() => send("map.select", { room: r.id })}
                />
              </foreignObject>
            </g>
          ))}
          <polyline
            points={list(p.path).map(xy).join(" ")}
            fill="none"
            stroke="var(--blue)"
            strokeWidth="3"
            strokeDasharray="6 4"
            strokeLinecap="round"
          />
          {Boolean(p.you) && (
            <circle
              cx={num(obj(p.you).x)}
              cy={num(obj(p.you).y)}
              r="5"
              fill="var(--blue)"
              stroke="var(--surface)"
              strokeWidth="2"
            />
          )}
        </svg>
      </div>
      {rows(p.liveLayers).map((r) => (
        <div className="row small" key={str(r.label)}>
          <span className="num">{str(r.value)} min</span>
          <span>{str(r.label)}</span>
          <span className="h-right badge b-measured">{str(r.source)}</span>
        </div>
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
                    {r.distance != null && <>{str(r.distance)} km · </>}
                    {list(r.facts).map(str).join(" · ")}
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
        <PlacePinMap results={rows(p.results)} picked={picked} pin={obj(p.pin)} send={send} />
      </div>
    </Frame>
  );
}
