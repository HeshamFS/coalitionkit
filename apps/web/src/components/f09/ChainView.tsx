// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";
export function ChainView({ p, send }: { p: Props; send: Send }) {
  const entries = rows(p.entries);
  return (
    <button
      type="button"
      className="f09-chain"
      aria-label="Verify chain"
      onClick={() => send("chain.verify")}
      title={`genesis ${text(p.genesis)}`}
    >
      <svg
        viewBox={`0 0 ${Math.max(640, entries.length * 160)} 150`}
        role="img"
        aria-label="Hash-linked entries"
      >
        <title>Hash-linked entries</title>
        {entries.map((e, i) => {
          const x = 6 + i * 160;
          const broken = e.verified === false;
          const color = broken ? "var(--bad-fg)" : e.selected ? "var(--blue-text)" : "var(--ink-3)";
          return (
            <g key={text(e.seq) || `${i}`} fontFamily="var(--font-mono)" fontSize="9.5">
              <rect
                x={x}
                y="30"
                width="130"
                height="80"
                rx="10"
                fill={e.selected ? "var(--blue-tint)" : "var(--surface)"}
                stroke={
                  broken ? "var(--bad-line)" : e.selected ? "var(--blue)" : "var(--line-strong)"
                }
                strokeWidth={e.selected ? 2 : 1}
                strokeDasharray={broken ? "4 3" : undefined}
              />
              <text x={x + 12} y="50" fill={color}>
                #{text(e.seq)}
                {broken ? " ?" : ""}
              </text>
              <text
                x={x + 12}
                y="68"
                fill={broken || e.selected ? color : "var(--ink)"}
                fontWeight={e.selected ? 600 : 400}
              >
                {broken ? "tampered copy" : `${text(e.type)} · ${text(e.actor)}`}
              </text>
              <text x={x + 12} y="86" fill={color}>
                prev {text(e.prev_hash)}
              </text>
              <text x={x + 12} y="100" fill={color}>
                {broken ? "✗ link broken" : `hash ${text(e.hash)}`}
              </text>
              {i < entries.length - 1 && (
                <path
                  d={`M${x + 130} 70 h30`}
                  stroke={entries[i + 1]?.verified === false ? "var(--bad-fg)" : "var(--blue)"}
                  strokeWidth="2"
                  strokeDasharray={entries[i + 1]?.verified === false ? "3 3" : undefined}
                />
              )}
            </g>
          );
        })}
        <text x="6" y="140" fontFamily="var(--font-ui)" fontSize="10.5" fill="var(--ink-2)">
          Each entry carries the hash of the one before. Change anything and every later link
          breaks, visibly.
        </text>
      </svg>
    </button>
  );
}
