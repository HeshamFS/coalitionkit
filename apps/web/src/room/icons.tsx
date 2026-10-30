// SPDX-License-Identifier: Apache-2.0
export function RoomLogo() {
  return (
    <svg width="26" height="26" viewBox="0 0 64 64" aria-hidden="true">
      {Array.from({ length: 7 }, (_, i) => {
        const angle = ((i + 1) * Math.PI) / 4;
        return (
          <circle
            key={angle}
            cx={32 + 23 * Math.cos(angle)}
            cy={32 + 23 * Math.sin(angle)}
            r="5"
            fill="var(--ink)"
          />
        );
      })}
      <circle cx="32" cy="32" r="9" fill="var(--blue)" />
    </svg>
  );
}
export function RoomIcon({ kind }: { kind: "stage" | "home" | "log" }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {kind === "stage" ? (
        [3, 14].flatMap((x) =>
          [4, 14].map((y) => <rect key={`${x}-${y}`} x={x} y={y} width="7" height="7" rx="1.5" />),
        )
      ) : kind === "home" ? (
        <path d="M3 10 12 3 21 10V21H15V14H9V21H3Z" />
      ) : (
        <>
          <path d="M8 6H21M8 12H21M8 18H21" />
          <path d="M3 6h.01M3 12h.01M3 18h.01" />
        </>
      )}
    </svg>
  );
}
