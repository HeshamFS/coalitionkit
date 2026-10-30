// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";
import { Icon } from "../../ui/Icon";

const extra: Record<string, ReactNode> = {
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </>
  ),
  filter: <path d="M4 5h16l-6 8v6l-4-2v-4z" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  edit: <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />,
  trash: <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" />,
  right: <path d="M9 6l6 6-6 6" />,
  more: <path d="M5 12h.01M12 12h.01M19 12h.01" strokeWidth="3" />,
  copy: (
    <>
      <rect x="8" y="8" width="12" height="12" rx="2" />
      <path d="M16 8V5H5v11h3" />
    </>
  ),
  down: <path d="M6 9l6 6 6-6" />,
  warning: (
    <>
      <path d="M12 3l10 18H2z" />
      <path d="M12 10v4M12 17h.01" />
    </>
  ),
  blocked: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 8l8 8M16 8l-8 8" />
    </>
  ),
  information: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ),
  resource: (
    <>
      <path d="M3 21V8l9-5 9 5v13M9 21v-6h6v6" />
    </>
  ),
  square: <rect x="4" y="4" width="16" height="16" rx="3" />,
  offline: <path d="M2 2l20 20M8.5 16.5a5 5 0 0 1 7 0M5 12.5a10 10 0 0 1 5-2.7M12 20h.01" />,
  upload: <path d="M12 16V4M7 9l5-5 5 5M4 20h16" />,
};
export function Glyph({ name, size }: { name: string; size?: "sm" | "lg" }) {
  if (!(name in extra)) return <Icon name={name} size={size} />;
  return (
    <svg
      className={`ico${size ? ` ico-${size}` : ""}`}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {extra[name]}
    </svg>
  );
}
