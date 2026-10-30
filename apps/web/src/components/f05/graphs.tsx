// SPDX-License-Identifier: Apache-2.0
import { Action, Frame, list, num, type Props, rows, str } from "./shared";
export function SeatRing({ p, send }: Props) {
  const seats = rows(p.seats),
    visible = seats.slice(0, 7),
    open = Math.min(7 - visible.length, num(p.openSeats)),
    total = visible.length + open;
  return (
    <Frame name="SeatRing">
      <div className="f05-ring">
        <svg viewBox="0 0 220 200" role="img" aria-label="Coalition seats">
          <path
            d="M150 40 A78 78 0 1 0 150 160"
            fill="none"
            stroke="var(--line)"
            strokeWidth="2"
            strokeDasharray="3 5"
          />
          <circle cx="120" cy="100" r="26" fill="var(--blue-tint)" stroke="var(--blue-line)" />
          <text x="120" y="96" textAnchor="middle" fill="var(--blue-text)" fontSize="10">
            Goal
          </text>
          <text x="120" y="110" textAnchor="middle" fill="var(--blue-text)" fontSize="8">
            {str(p.goal)}
          </text>
          {Array.from({ length: total }, (_, i) => {
            const angle = -Math.PI / 2 - (i * Math.PI) / Math.max(1, total - 1),
              x = 120 + 78 * Math.cos(angle),
              y = 100 + 74 * Math.sin(angle),
              seat = visible[i];
            return (
              <g key={seat ? str(seat.participant) : `open-${i}`}>
                <circle
                  cx={x}
                  cy={y}
                  r="15"
                  fill={seat ? `var(--seat-${num(seat.seat, 1)})` : "var(--surface)"}
                  stroke={
                    seat?.state === "acting"
                      ? "var(--blue)"
                      : seat?.state === "owes"
                        ? "var(--warn-fg)"
                        : "var(--line-strong)"
                  }
                  strokeWidth="3"
                  strokeDasharray={seat ? undefined : "3 3"}
                />
                <text
                  x={x}
                  y={y + 4}
                  textAnchor="middle"
                  fill={seat ? "var(--on-fill)" : "var(--ink-2)"}
                >
                  {seat ? str(seat.participant).slice(-1) : "?"}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="row wrap">
        {visible.map((s) => (
          <Action
            key={str(s.participant)}
            onClick={() => send("seat.open", { participant: s.participant })}
          >
            {str(s.participant)} · {str(s.state)}
          </Action>
        ))}
        {seats.length > 7 && <span>+{seats.length - 7}</span>}
      </div>
    </Frame>
  );
}
export function ActsForGraph({ p, send }: Props) {
  const people = rows(p.people),
    agents = rows(p.agents),
    height = Math.max(230, agents.length * 44 + 40, people.length * 62 + 40);
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
            >
              {owners.map((owner) => {
                const index = people.findIndex((person) => person.participant === owner);
                return index < 0 ? null : (
                  <path
                    key={str(owner)}
                    d={`M190 ${52 + index * 62} C220 ${52 + index * 62},220 ${45 + i * 44},250 ${45 + i * 44}`}
                  />
                );
              })}
              <path d={`M430 ${45 + i * 44} H472`} />
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
            <foreignObject x="250" y={28 + i * 44} width="180" height="34">
              <button
                type="button"
                className={`f05-agent ${agent.card === p.acting ? "acting" : ""}`}
                onClick={() => send("agent.inspect", { card: agent.card })}
              >
                {str(agent.card)}
              </button>
            </foreignObject>
            <text x="480" y={49 + i * 44} fill="var(--ink-2)" fontSize="11">
              {str(agent.vendor)} · {str(agent.runtime)}
            </text>
          </g>
        ))}
      </svg>
      <p className="small">
        Agents act; only owner keys decide. One person may run several agents; an owner key belongs
        to one person.
      </p>
    </Frame>
  );
}
