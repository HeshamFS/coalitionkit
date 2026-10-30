// SPDX-License-Identifier: Apache-2.0
import { list, obj, type Props, type Send, text } from "./shared";
export function OverlapView({ p }: { p: Props; send: Send }) {
  const tokens = list(p.tokens);
  const matches = tokens.filter((t) => obj(t).match);
  const countOnly = p.mode === "count-only";
  if (!p.result)
    return (
      <span className="small" role="status">
        Matching private inputs…
      </span>
    );
  return (
    <svg viewBox="0 0 620 200" className="f08-psi" role="img" aria-label="Private matching">
      <title>Private matching: only shared results leave the vault</title>
      <g fontSize="10.5" fontFamily="var(--font-ui)">
        <g fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-3)">
          <text x="10" y="16">
            {text(list(p.parties)[0]).toUpperCase()}'S SLOTS (STAY)
          </text>
          <text x="236" y="16">
            BLINDED, ON THE WIRE
          </text>
          <text x="470" y="16">
            WHAT ANYONE LEARNS
          </text>
        </g>
        {tokens.map((token, i) => {
          const t = obj(token);
          const y = 28 + i * 32;
          return (
            <g key={text(token)}>
              <rect
                x="10"
                y={y}
                width="150"
                height="26"
                rx="6"
                fill="var(--surface)"
                stroke="var(--line)"
              />
              <text x="20" y={y + 17} fill="var(--ink)">
                {text(t.local)}
              </text>
              <path
                d={`M160 ${y + 13} H236`}
                stroke="var(--line-strong)"
                strokeDasharray="4 5"
                strokeWidth="1.5"
              />
              <rect
                x="236"
                y={y}
                width="180"
                height="26"
                rx="6"
                fill={t.match ? "var(--blue-tint)" : "var(--surface-2)"}
                stroke={t.match ? "var(--blue)" : "none"}
              />
              <text
                x="246"
                y={y + 17}
                fontFamily="var(--font-mono)"
                fontSize="9.5"
                fill={t.match ? "var(--blue-text)" : "var(--ink-2)"}
              >
                {text(token)}
                {t.match ? "  ✓ match" : ""}
              </text>
            </g>
          );
        })}
        <rect
          x="470"
          y="60"
          width="140"
          height="60"
          rx="10"
          fill="var(--blue-tint)"
          stroke="var(--blue-line)"
        />
        <text x="482" y="84" fontWeight="700" fontSize="16" fill="var(--blue-text)">
          {matches.length} shared slot{matches.length === 1 ? "" : "s"}
        </text>
        {!countOnly && (
          <text x="482" y="104" fill="var(--blue-text)">
            {text(obj(matches[0]).local)} · to {list(p.parties).length} members
          </text>
        )}
        <text x="470" y="140" fill="var(--ink-3)" fontSize="9.5">
          count-only mode: "{matches.length}", no slot
        </text>
        <text x="10" y="180" fill="var(--ink-3)" fontSize="9.5">
          Busy times, and slots that didn't match, are never sent and can't be recovered from the
          tokens.
        </text>
      </g>
    </svg>
  );
}
