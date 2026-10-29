// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";

const PATHS: Record<string, ReactNode> = {
  shield: <path d="M12 3l8 4v6c0 4-3.5 7-8 8-4.5-1-8-4-8-8V7z" />,
  shieldCheck: (
    <>
      <path d="M12 3l8 4v6c0 4-3.5 7-8 8-4.5-1-8-4-8-8V7z" />
      <path d="M9 12l2 2 4-4" />
    </>
  ),
  check: <path d="M5 12l5 5 9-10" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v5M12 16h.01" />
    </>
  ),
  x: <path d="M6 6l12 12M18 6L6 18" />,
  retry: <path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5" />,
  tray: <path d="M4 4h16v16H4zM8 9h8M8 13h8M8 17h5" />,
  canvas: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <path d="M3 9h18" />
    </>
  ),
  people: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20a6 6 0 0 1 12 0M17 11a3 3 0 1 0 0-6M21 20a6 6 0 0 0-4-5.6" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v4l3 2" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  list: <path d="M4 6h16M4 12h10M4 18h7" />,
  lock: (
    <>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
  terminal: <path d="M4 17l6-6-6-6M12 19h8" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-4-4" />
    </>
  ),
  link: (
    <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
  ),
  mic: (
    <>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </>
  ),
  send: <path d="M5 12h14M13 6l6 6-6 6" />,
  chat: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
  branch: <path d="M6 3v12M18 9a3 3 0 1 0 0 .01M6 18a3 3 0 1 0 0 .01M18 12c0 4-6 3-12 6" />,
  inbox: <path d="M4 13l2-8h12l2 8v6H4zM4 13h5l1 3h4l1-3h5" />,
};

export type IconName = keyof typeof PATHS;

export function Icon({ name, size }: { name: IconName; size?: "sm" | "lg" }) {
  const cls = size === "sm" ? "ico ico-sm" : size === "lg" ? "ico ico-lg" : "ico";
  return (
    <svg className={cls} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {PATHS[name]}
    </svg>
  );
}

/** The Coalition C mark: one blue seat and up to six outer dots. */
export function Mark({ size = 22, muted = false }: { size?: number; muted?: boolean }) {
  const dot = (cx: number, cy: number, fill: string, r = 3) => (
    <circle
      key={`${cx}-${cy}`}
      cx={cx}
      cy={cy}
      r={r}
      style={{ fill: muted ? "var(--bg-dot)" : fill }}
    />
  );
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" role="img" aria-label="CoalitionKit">
      <circle cx="24" cy="20" r="5" fill="#0B63F6" />
      {dot(14, 9, "#0D7A82")}
      {dot(9, 17, "#A4520F")}
      {dot(9, 25, "#B02A64")}
      {dot(14, 32, "#5B3EA6")}
      {dot(22, 35, "#3E5C76")}
      {dot(22, 5, "var(--ink)")}
    </svg>
  );
}
