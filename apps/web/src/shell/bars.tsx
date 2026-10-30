// SPDX-License-Identifier: Apache-2.0
import { Avatar, cx, type Seat } from "../components/primitives";
import { Icon, type IconName, Mark } from "../ui/Icon";

export const STAGES = [
  "Germinate",
  "Gather",
  "Negotiate",
  "Decide",
  "Act",
  "Live",
  "Dissolve",
] as const;
export type Stage = (typeof STAGES)[number];

export function StageBar({ current, compact }: { current: Stage; compact?: boolean }) {
  const at = STAGES.indexOf(current);
  const shown = compact ? STAGES.filter((s) => s === current) : STAGES;
  return (
    <ol
      className="stagebar"
      aria-label="Stage"
      style={{ listStyle: "none", margin: 0, padding: 0 }}
    >
      {shown.map((s, i) => {
        const index = STAGES.indexOf(s);
        const state = index < at ? "done" : index === at ? "now" : "next";
        return (
          <li
            key={s}
            style={{ display: "contents" }}
            aria-current={state === "now" ? "step" : undefined}
          >
            {i > 0 && <span className="sg-sep" aria-hidden="true" />}
            <span
              className={cx("sg", state === "done" && "sg-done", state === "now" && "sg-now")}
              data-state={state}
            >
              {state === "done" && <span aria-hidden="true">{"✓"}</span>}
              {state === "now" && (
                <span
                  className="live-dot pulse"
                  style={{ width: 6, height: 6 }}
                  aria-hidden="true"
                />
              )}
              {s}
              <span className="sr-only">
                {state === "done" ? " (done)" : state === "now" ? " (current stage)" : " (next)"}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export type PresenceEntry = { seat: Seat; label: string; presence: "live" | "away" | "off" };

export function TopBar({
  title,
  meta,
  stage,
  presence,
  me,
  onInvite,
  onSearch,
  onSignOut,
  room,
}: {
  title: string;
  meta?: string;
  stage: Stage;
  presence: PresenceEntry[];
  me?: { seat: Seat; label: string };
  onInvite?: () => void;
  onSearch?: () => void;
  onSignOut?: () => void;
  room?: boolean;
}) {
  return (
    <header className="topbar">
      <Mark />
      <b style={{ fontSize: 13.5, whiteSpace: "nowrap" }}>{title}</b>
      {meta && (
        <span className="small">
          {"·"} {meta}
        </span>
      )}
      <div style={{ marginLeft: 14 }}>
        <StageBar current={stage} compact={room} />
      </div>
      {!room && (
        <span className="h-right">
          {/* biome-ignore lint/a11y/useSemanticElements: a stack of avatars is a labelled group */}
          <div className="stack" role="group" aria-label="Who is here">
            {presence.map((p) => (
              <Avatar key={p.label} seat={p.seat} label={p.label} presence={p.presence} />
            ))}
          </div>
          <button
            type="button"
            className="dock"
            style={{ boxShadow: "none", cursor: "pointer" }}
            aria-label="Search"
            onClick={onSearch}
          >
            <Icon name="search" size="sm" />
            <span className="kbd">{"⌘"}K</span>
          </button>
          <button type="button" className="btn btn-sm" onClick={onInvite}>
            <Icon name="link" size="sm" />
            Invite
          </button>
          {me && <Avatar seat={me.seat} label={me.label} size="lg" />}
          {onSignOut && (
            <button type="button" className="btn btn-sm btn-ghost" onClick={onSignOut}>
              Sign out
            </button>
          )}
        </span>
      )}
    </header>
  );
}

export type DeckItem = {
  id: string;
  label: string;
  icon: IconName;
  count?: number | string;
  tone?: "blue";
};
export type DeckGroup = { heading: string; items: DeckItem[] };

export function Deck({
  groups,
  selected,
  collapsed,
  onSelect,
  footer,
}: {
  groups: DeckGroup[];
  selected: string;
  collapsed?: boolean;
  onSelect?: (id: string) => void;
  footer?: { item: DeckItem; active?: boolean; onClick: () => void };
}) {
  return (
    <nav
      className="deck"
      aria-label="Sections"
      data-collapsed={collapsed || undefined}
      style={collapsed ? { width: 52 } : undefined}
    >
      {groups.map((g) => (
        <div key={g.heading} className="col" style={{ gap: 2 }}>
          {!collapsed && <div className="deck-h">{g.heading}</div>}
          {g.items.map((it) => (
            <button
              type="button"
              key={it.id}
              className={cx("deck-i", selected === it.id && "deck-on")}
              aria-current={selected === it.id ? "page" : undefined}
              aria-label={collapsed ? it.label : undefined}
              title={it.label}
              onClick={() => onSelect?.(it.id)}
            >
              <Icon name={it.icon} size="sm" />
              {!collapsed && it.label}
              {!collapsed && it.count !== undefined && (
                <span className={cx("count", it.tone === "blue" && "count-blue")}>{it.count}</span>
              )}
            </button>
          ))}
        </div>
      ))}
      {footer && (
        <button
          type="button"
          className={cx("deck-i", footer.active && "deck-on")}
          style={{ marginTop: "auto" }}
          aria-pressed={footer.active}
          aria-label={collapsed ? footer.item.label : undefined}
          title={footer.item.label}
          onClick={footer.onClick}
        >
          <Icon name={footer.item.icon} size="sm" />
          {!collapsed && footer.item.label}
        </button>
      )}
    </nav>
  );
}
