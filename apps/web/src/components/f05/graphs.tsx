// SPDX-License-Identifier: Apache-2.0
import { Frame, list, num, type Props, rows, str } from "./shared";

function SeatGlyph({
  seat,
  x,
  y,
  i,
  send,
}: {
  seat?: Record<string, unknown>;
  x: number;
  y: number;
  i: number;
  send: Props["send"];
}) {
  const name = str(seat?.participant);
  return (
    <g>
      <circle
        cx={x}
        cy={y}
        r={seat ? 15 : 13}
        fill={seat ? `var(--seat-${num(seat.seat, 1)})` : "none"}
        stroke={seat?.state === "acting" ? "var(--blue)" : seat ? "none" : "var(--line-strong)"}
        strokeWidth={seat?.state === "acting" ? 3 : 1}
        strokeDasharray={seat ? undefined : "3 3"}
      />
      {seat?.state === "owes" && (
        <circle
          cx={x}
          cy={y}
          r="19"
          fill="none"
          stroke="var(--warn-fg)"
          strokeWidth="1.5"
          strokeDasharray="2 3"
        />
      )}
      {seat && (
        <text
          x={x}
          y={y + 4}
          textAnchor="middle"
          fill="var(--on-fill)"
          fontSize="10"
          fontWeight="700"
        >
          {name.slice(-1)}
        </text>
      )}
      {seat && (
        <text
          x={i === 0 ? 148 : i === 1 ? 4 : i === 2 ? 6 : x + 14}
          y={i === 0 ? 22 : i === 1 ? 20 : i === 2 ? 128 : y + 4}
          fontSize="9"
          fill="var(--ink-2)"
        >
          {`${name}${seat.state === "acting" ? " · acting" : ""}`}
        </text>
      )}
      {seat && (
        <foreignObject x={x - 15} y={y - 15} width="30" height="30">
          <button
            type="button"
            className="f05-seat-hit"
            aria-label={`${name} · ${str(seat.state)}`}
            onClick={() => send("seat.open", { participant: seat.participant })}
          />
        </foreignObject>
      )}
    </g>
  );
}
export function SeatRing({ p, send }: Props) {
  const seats = rows(p.seats),
    visible = seats.slice(0, 7);
  const total = visible.length + Math.max(0, Math.min(7 - visible.length, num(p.openSeats)));
  const positions =
    total === 5
      ? [
          [128, 26],
          [62, 44],
          [40, 100],
          [62, 156],
          [128, 174],
        ]
      : Array.from({ length: total }, (_, i) => {
          const angle = -Math.PI / 2 - (i * Math.PI) / Math.max(1, total - 1);
          return [120 + 78 * Math.cos(angle), 100 + 74 * Math.sin(angle)];
        });
  return (
    <Frame name="SeatRing">
      <svg className="f05-ring" viewBox="0 0 220 200" aria-label="Coalition seats">
        <path
          d="M150 40 A78 78 0 1 0 150 160"
          fill="none"
          stroke="var(--line)"
          strokeWidth="2"
          strokeDasharray="3 5"
        />
        <circle cx="120" cy="100" r="26" fill="var(--blue-tint)" stroke="var(--blue-line)" />
        <text
          x="120"
          y="96"
          textAnchor="middle"
          fill="var(--blue-text)"
          fontSize="10"
          fontWeight="600"
        >
          Goal
        </text>
        <text
          x="120"
          y="110"
          textAnchor="middle"
          fill="var(--blue-text)"
          fontSize="8"
          className="mono"
        >
          {str(p.goal)}
        </text>
        {positions.map(([x = 0, y = 0], i) => (
          <SeatGlyph key={`${x}-${y}`} seat={visible[i]} x={x} y={y} i={i} send={send} />
        ))}
      </svg>
      <div className="row wrap small f05-ring-legend">
        <span className="row">
          <i className="pin acting" />
          acting now
        </span>
        <span className="row">
          <i className="pin owes" />
          owes an answer
        </span>
        <span className="row">
          <i className="pin open" />
          open seat
        </span>
        {seats.length > 7 && <span>+{seats.length - 7}</span>}
      </div>
    </Frame>
  );
}
export function ActsForGraph({ p, send }: Props) {
  const people = rows(p.people),
    agents = rows(p.agents),
    height = Math.max(230, agents.length * 46 + 28, people.length * 62 + 40);
  const agentY = (i: number) => (i === 0 ? 28 : 24 + i * 46);
  return (
    <Frame name="ActsForGraph">
      <svg
        viewBox={`0 0 640 ${height}`}
        className="f05-acts"
        aria-label="People, agents and runtimes"
      >
        <g className="f05-graph-label">
          <text x="20" y="16">
            PEOPLE · OWNER KEYS
          </text>
          <text x="250" y="16">
            AGENTS · CARD KEYS
          </text>
          <text x="480" y="16">
            RUNS ON
          </text>
        </g>
        {agents.map((agent, i) => {
          const owners = Array.isArray(agent.actsFor) ? list(agent.actsFor) : [agent.actsFor];
          return (
            <g
              key={str(agent.card)}
              fill="none"
              stroke={p.acting === agent.card ? "var(--blue)" : "var(--line-strong)"}
              strokeWidth={p.acting === agent.card ? 2 : 1.5}
              strokeDasharray={p.acting === agent.card ? "3 8" : undefined}
            >
              {owners.map((owner) => {
                const index = people.findIndex((person) => person.participant === owner);
                return index < 0 ? null : (
                  <path
                    key={str(owner)}
                    d={`M190 ${52 + index * 62} C220 ${52 + index * 62},220 ${agentY(i) + 17},250 ${agentY(i) + 17}`}
                  />
                );
              })}
              <path d={`M430 ${agentY(i) + 17} H472`} />
            </g>
          );
        })}
        {people.map((person, i) => (
          <g key={str(person.participant)}>
            <rect
              x="20"
              y={30 + i * 62}
              width="170"
              height="44"
              rx="10"
              fill="var(--surface)"
              stroke="var(--line)"
            />
            <circle cx="40" cy={52 + i * 62} r="10" fill={`var(--seat-${[3, 1, 5][i % 3]})`} />
            <text x="40" y={56 + i * 62} textAnchor="middle" fill="var(--on-fill)" fontSize="9">
              {str(person.participant).slice(-1)}
            </text>
            <text x="58" y={49 + i * 62} fill="var(--ink)" fontSize="11" fontWeight="600">
              {str(person.participant)}
            </text>
            <text x="58" y={63 + i * 62} className="f05-graph-label">
              owner {str(person.ownerKid)}
            </text>
          </g>
        ))}
        {agents.map((agent, i) => (
          <g key={str(agent.card)}>
            <foreignObject x="250" y={agentY(i)} width="180" height="34">
              <button
                type="button"
                className={`f05-agent ${agent.card === p.acting ? "acting" : ""}`}
                onClick={() => send("agent.inspect", { card: agent.card })}
              >
                {str(agent.card)}
              </button>
            </foreignObject>
            <text x="480" y={agentY(i) + 21} fill="var(--ink-2)" fontSize="11">
              {[str(agent.vendor), str(agent.runtime)]
                .filter(Boolean)
                .join(agent.vendor === "hosted" ? " " : " · ")}
            </text>
          </g>
        ))}
      </svg>
      <p className="row small">
        <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="8" cy="15" r="4" />
          <path d="M11 12l9-9M17 6l3 3" />
        </svg>
        Agents act; only owner keys decide. One person may run several agents; an owner key belongs
        to one person.
      </p>
    </Frame>
  );
}
