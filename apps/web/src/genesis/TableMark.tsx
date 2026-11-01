// SPDX-License-Identifier: Apache-2.0
// The round table: the Coalition C at stage size. Seats arrive one by one as the Gardener reads
// the goal; the goal lights last, when the coalition starts (design system, "The mark").

const SEATS: [number, number][] = [
  [48.3, 15.7],
  [32, 9],
  [15.7, 15.7],
  [9, 32],
  [15.7, 48.3],
  [32, 55],
  [48.3, 48.3],
];

export function TableMark({
  filled,
  lit,
  reading,
  size = 300,
}: {
  /** Seats found so far (0 to 7; more than seven people still fill seven seats). */
  filled: number;
  /** The coalition has started: the goal lights blue. */
  lit: boolean;
  /** The Gardener is reading the sentence: the goal pulses softly. */
  reading: boolean;
  size?: number;
}) {
  const n = Math.max(0, Math.min(7, filled));
  const label = lit
    ? `The coalition has started with ${n} seat${n === 1 ? "" : "s"} at the table`
    : `${n} of 7 seats found so far`;
  return (
    <svg
      className="gn-table"
      data-lit={lit}
      data-reading={reading}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label={label}
    >
      <circle className="gn-halo" cx="32" cy="32" r="14" />
      {SEATS.map(([cx, cy], i) => (
        <circle
          key={`${cx}-${cy}`}
          className="gn-seat"
          data-on={i < n}
          style={{ transitionDelay: `${i * 90}ms` }}
          cx={cx}
          cy={cy}
          r="4.5"
        />
      ))}
      <circle className="gn-goal" cx="32" cy="32" r="8.5" />
    </svg>
  );
}
