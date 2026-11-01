// SPDX-License-Identifier: Apache-2.0
import type { CSSProperties, ReactNode } from "react";
import { AccountMenu } from "../components/f02/templates";
import { Banner } from "../components/feedback";
import { AvatarStack, cx } from "../components/primitives";
import { RoomIcon, RoomLogo } from "../room/icons";
import { Icon } from "../ui/Icon";
import { Deck, type DeckGroup, type PresenceEntry, type Stage, StageBar, TopBar } from "./bars";

export type Connection = "live" | "reconnecting" | "watcher";

export type RoomShellProps = {
  title: string;
  meta?: string;
  stage: Stage;
  presence: PresenceEntry[];
  me?: { seat: PresenceEntry["seat"]; label: string };
  groups: DeckGroup[];
  selected: string;
  onSelect?: (id: string) => void;
  connection?: Connection;
  /** The generated canvas: an A2UI tree for this viewer. */
  children?: ReactNode;
  dock?: ReactNode;
  tray?: ReactNode;
  wiring?: ReactNode;
  wiringOpen?: boolean;
  onToggleWiring?: () => void;
  onInvite?: () => void;
  onSearch?: () => void;
  onSignOut?: () => void;
  /** Set only for the person who started the coalition. */
  onEnd?: () => void;
  style?: CSSProperties;
  layout?: "stage";
  navigation?: ReactNode;
  /** Phone only: the bottom bar. */
  bottomNav?: ReactNode;
  aside?: ReactNode;
};

function StageShell(p: RoomShellProps) {
  const rail = [
    { id: "Stage", node: <RoomIcon kind="stage" /> },
    { id: "My part", node: <Icon name="people" /> },
    { id: "Wiring", node: <RoomIcon kind="log" /> },
  ];
  const live = p.connection === "reconnecting" ? "reconnecting" : (p.connection ?? "live");
  const chip = (
    <span className="room-connection" role="status">
      <span className="live-dot" />
      {live}
    </span>
  );
  return (
    <div className="room-stage-shell">
      <nav className="room-rail" aria-label="Room tools">
        <RoomLogo />
        <span className="room-rail-rule" aria-hidden="true" />
        {rail.map((r) => (
          <button
            key={r.id}
            type="button"
            className="icon-btn"
            aria-label={r.id}
            aria-current={p.selected === r.id ? "page" : undefined}
            onClick={() => p.onSelect?.(r.id)}
          >
            {r.node}
          </button>
        ))}
      </nav>
      <div className="room-main">
        <header className="room-heading">
          <span className="room-heading-logo">
            <RoomLogo />
          </span>
          <div className="room-heading-title">
            <h1>{p.title}</h1>
            {p.meta && <span className="room-heading-sub">{p.meta}</span>}
          </div>
          <span className="room-stage-pill">
            <span className="room-stage-dot" />
            {p.stage}
          </span>
          {p.navigation}
          <span className="room-heading-live">{chip}</span>
          {p.onEnd && (
            <button type="button" className="btn btn-sm btn-ghost" onClick={p.onEnd}>
              End coalition
            </button>
          )}
          <details className="room-account">
            <summary className="icon-btn" aria-label="Account">
              <Icon name="people" />
            </summary>
            <AccountMenu
              p={{ identity: { label: "Your account" }, agents: [], channels: [] }}
              send={(_event, data) => {
                if (data?.id === "sign-out") p.onSignOut?.();
              }}
            />
          </details>
        </header>
        <div className="room-columns" data-aside={p.aside ? "on" : "off"}>
          <main className="room-canvas">{p.children}</main>
          {p.aside && (
            <aside className="room-aside" aria-label="Wiring and decisions">
              {p.aside}
            </aside>
          )}
        </div>
        {p.bottomNav}
      </div>
    </div>
  );
}

export function RoomShell(p: RoomShellProps) {
  if (p.layout === "stage") return <StageShell {...p} />;
  const connection = p.connection ?? "live";
  const watcher = connection === "watcher";
  const wiringShown = Boolean(p.wiringOpen && p.wiring);
  return (
    <div className={cx("shell", "shell-root")} style={p.style}>
      <TopBar
        title={p.title}
        meta={p.meta}
        stage={p.stage}
        presence={p.presence}
        me={p.me}
        onInvite={p.onInvite}
        onSearch={p.onSearch}
        onSignOut={p.onSignOut}
      />
      <div
        className={cx("shell-body", watcher && "no-dock")}
        style={
          wiringShown && !watcher ? { gridTemplateColumns: "188px 1fr 320px 300px" } : undefined
        }
      >
        <Deck
          groups={p.groups}
          selected={p.selected}
          onSelect={p.onSelect}
          footer={{
            item: { id: "wiring", label: "Wiring", icon: "terminal" },
            active: p.wiringOpen,
            onClick: () => p.onToggleWiring?.(),
          }}
        />
        <main className="canvas" aria-label="Canvas">
          <div className="canvas-scroll">
            {watcher && (
              <Banner
                tone="info"
                title="You are watching."
                body="You can read this room but not decide in it."
              />
            )}
            {p.children}
          </div>
          <div className="float row" style={{ right: 12, top: 12, gap: 4 }}>
            <span className="dock" role="status" data-connection={connection}>
              {connection === "live" && (
                <>
                  <span className="live-dot" />
                  <b>Live</b>
                </>
              )}
              {connection === "reconnecting" && (
                <>
                  <span
                    className="spinner"
                    style={{ color: "var(--warn-fg)", width: 10, height: 10 }}
                  />
                  <b>Reconnecting</b>
                </>
              )}
              {watcher && <b>Read only</b>}
            </span>
          </div>
          {!watcher && p.tray && <div className="float tray-dock">{p.tray}</div>}
        </main>
        {wiringShown && !watcher && p.wiring}
        {!watcher && p.dock}
      </div>
    </div>
  );
}

/* ---------- PhoneShell: the compact door ---------- */

export type PhoneTab = "Now" | "Plans" | "People" | "Agent";
const TAB_ICON = { Now: "canvas", Plans: "list", People: "people", Agent: "chat" } as const;

export function PhoneShell({
  title,
  stage,
  people,
  tab,
  onTab,
  children,
  tray,
  height,
  onSignOut,
}: {
  title: string;
  stage: Stage;
  people: { seat: PresenceEntry["seat"]; label: string }[];
  tab: PhoneTab;
  onTab?: (t: PhoneTab) => void;
  children?: ReactNode;
  tray?: ReactNode;
  height?: number | string;
  onSignOut?: () => void;
}) {
  return (
    <div className="phone-root compact" style={height ? { height } : undefined}>
      <header
        className="row"
        style={{
          padding: "6px 12px",
          background: "var(--surface)",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <b style={{ fontSize: 12.5 }}>{title}</b>
        <StageBar current={stage} compact />
        <span className="h-right">
          <AvatarStack people={people} size="xs" max={4} />
          {onSignOut && (
            <button type="button" className="btn btn-sm btn-ghost" onClick={onSignOut}>
              Sign out
            </button>
          )}
        </span>
      </header>
      <main className="phone-stack" aria-label={tab}>
        {children}
        {tray}
      </main>
      <div className="tabbar" aria-label="Sections" role="tablist">
        {(["Now", "Plans", "People", "Agent"] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={cx(tab === t && "on")}
            onClick={() => onTab?.(t)}
          >
            <Icon name={TAB_ICON[t]} />
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}
