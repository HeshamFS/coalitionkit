// SPDX-License-Identifier: Apache-2.0
// The logo and its working form. On the map, the mark reports a room: its dots are seats, filled
// when taken, and the centre lights once a plan is signed. The open side stays open.

export function Logo({ size = 24 }: { size?: number }) {
  const seats = [
    [48.3, 15.7],
    [32, 9],
    [15.7, 15.7],
    [9, 32],
    [15.7, 48.3],
    [32, 55],
    [48.3, 48.3],
  ];
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className="ld-logo">
      {seats.map(([cx, cy]) => (
        <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="5.5" fill="currentColor" />
      ))}
      <circle cx="32" cy="32" r="8" fill="none" stroke="currentColor" strokeWidth="4" />
    </svg>
  );
}

const GAP = 46;

export function RoomMark({
  seats,
  filled,
  lit = false,
  size = 38,
}: {
  seats: number;
  filled: number;
  lit?: boolean;
  size?: number;
}) {
  const span = 360 - 2 * GAP;
  const dot = Math.min(3.3, Math.max(1.4, ((2 * Math.PI * 18.5 * (span / 360)) / seats) * 0.36));
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" className="ld-roommark">
      {Array.from({ length: seats }, (_, i) => {
        const angle = ((GAP + (seats > 1 ? (span * i) / (seats - 1) : span / 2)) * Math.PI) / 180;
        return (
          <circle
            // biome-ignore lint/suspicious/noArrayIndexKey: seats are positional
            key={i}
            cx={(24 + 18.5 * Math.cos(-angle)).toFixed(2)}
            cy={(24 + 18.5 * Math.sin(-angle)).toFixed(2)}
            r={dot.toFixed(2)}
            data-taken={i < filled}
          />
        );
      })}
      <circle cx="24" cy="24" r={lit ? 7.5 : 5.5} className="ld-goal" data-lit={lit} />
    </svg>
  );
}
