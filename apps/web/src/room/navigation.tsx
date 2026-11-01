// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";
import { Icon } from "../ui/Icon";
import { RoomIcon } from "./icons";

/** Desktop: the segmented Stage | My part | Agents | Plans | What happened, then whatever sits beside it (View as). */
export function RoomNavigation({
  selected,
  onSelect,
  children,
}: {
  selected: string;
  onSelect: (tab: string) => void;
  children?: ReactNode;
}) {
  return (
    <div className="room-nav">
      <nav className="room-tabs" aria-label="Room sections">
        {["Stage", "My part", "Agents", "Plans", "Wiring"].map((tab) => (
          <button
            type="button"
            key={tab}
            aria-pressed={selected === tab}
            onClick={() => onSelect(tab)}
          >
            {tab === "Wiring" ? "What happened" : tab}
          </button>
        ))}
      </nav>
      {children}
    </div>
  );
}

const PHONE_TABS = [
  { tab: "My part", label: "My part" },
  { tab: "Agents", label: "Agents" },
  { tab: "Plans", label: "Plans" },
  { tab: "Wiring", label: "What happened" },
] as const;

/** Phone: the bottom bar of the Room board. */
export function PhoneNav({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (tab: string) => void;
}) {
  return (
    <nav className="room-bottom-nav" aria-label="Room">
      {PHONE_TABS.map(({ tab, label }) => (
        <button
          type="button"
          key={tab}
          aria-current={selected === tab ? "page" : undefined}
          onClick={() => onSelect(tab)}
        >
          {tab === "Plans" ? (
            <Icon name="canvas" />
          ) : tab === "Agents" ? (
            <Icon name="people" />
          ) : (
            <RoomIcon kind={tab === "My part" ? "home" : "log"} />
          )}
          {label}
        </button>
      ))}
    </nav>
  );
}
