// SPDX-License-Identifier: Apache-2.0
import { Fragment, useState } from "react";
import "./shell.css";
import { Children, Frame, label, list, number, text, type View } from "./ui";

export function ShellIcon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    Canvas: "M3 3h18v18H3zM3 9h18",
    Charter: "M12 3l8 4v6c0 4-4 7-8 8-4-1-8-4-8-8V7z",
    People: "M3 20a6 6 0 0 1 12 0M17 5a3 3 0 0 1 0 6M21 20a6 6 0 0 0-4-6",
    Needs: "M12 8v4l3 2",
    Offers: "M12 5v14M5 12h14",
    Plans: "M4 6h16M4 12h10M4 18h7",
    Tasks: "M5 12l5 5 9-10",
    Log: "M4 4h16v16H4zM8 9h8M8 13h8M8 17h5",
    Vault: "M5 11h14v10H5zM8 11V8a4 4 0 0 1 8 0v3",
    Wiring: "M4 17l6-6-6-6M12 19h8",
    Search: "M20 20l-4-4",
    Invite:
      "M10 14a4 4 0 0 0 6 0l3-3a4 4 0 0 0-6-6l-1 1M14 10a4 4 0 0 0-6 0l-3 3a4 4 0 0 0 6 6l1-1",
    Send: "M5 12h14M13 6l6 6-6 6",
    Agent: "M3 5h18v12H7l-4 4z",
  };
  return (
    <svg className="f02-icon" aria-hidden="true" viewBox="0 0 24 24">
      <path d={paths[name] ?? paths.Charter} />
      {name === "People" && <circle cx="9" cy="8" r="3" />}
      {name === "Needs" && <circle cx="12" cy="12" r="9" />}
      {name === "Search" && <circle cx="11" cy="11" r="7" />}
    </svg>
  );
}

export function CoalitionMark() {
  return (
    <svg width="22" height="22" viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="24" cy="20" r="5" fill="var(--blue)" />
      {[
        [14, 9],
        [9, 17],
        [9, 25],
        [14, 32],
        [22, 35],
        [22, 5],
      ].map(([x, y], i) => (
        <circle
          key={`${x}-${y}`}
          cx={x}
          cy={y}
          r="3"
          fill={i === 5 ? "var(--ink)" : `var(--seat-${i + 1})`}
        />
      ))}
    </svg>
  );
}

export function StageBar({ p }: View) {
  const stages = (text(p.stages) || "Gather|Negotiate|Decide|Act|Live").split("|").filter(Boolean);
  const current = stages.indexOf(text(p.current));
  return (
    <Frame name="StageBar">
      <ol className="ck-stages">
        {stages.map((stage, i) => (
          <li
            key={stage}
            data-state={i < current ? "done" : i === current ? "now" : "next"}
            aria-current={i === current ? "step" : undefined}
          >
            {i < current ? "✓ " : i === current ? <span className="f02-live" /> : null}
            {stage}
          </li>
        ))}
      </ol>
    </Frame>
  );
}

export function TopBar({ p, send, roomActions = false }: View & { roomActions?: boolean }) {
  const people = list(p.presence);
  return (
    <Frame name="TopBar">
      <header className="f02-topline">
        <CoalitionMark />
        <b>{text(p.title)}</b>
        {people.length > 0 && <span className="f02-meta">· {people.length} people</span>}
        <StageBar p={{ current: p.stage }} send={send} />
        <div className="f02-top-actions">
          <div className="f02-people">
            {people.map((person, i) => (
              <span
                key={label(person)}
                className="ck-avatar"
                style={{ background: `var(--seat-${(i % 5) + 1})` }}
                title={label(person)}
              >
                {label(person).slice(0, 1)}
                <i data-away={person.presence === "away" || undefined} />
              </span>
            ))}
          </div>
          {roomActions && (
            <>
              <button
                type="button"
                className="f02-search"
                aria-label="Search"
                onClick={() => send("search.open")}
              >
                <ShellIcon name="Search" />
                <kbd>⌘K</kbd>
              </button>
              <button type="button" className="ck-action" onClick={() => send("invite.open")}>
                <ShellIcon name="Invite" />
                Invite
              </button>
            </>
          )}
          {people[0] && <span className="ck-avatar f02-me">{label(people[0]).slice(0, 1)}</span>}
        </div>
      </header>
    </Frame>
  );
}

export function Deck({ p, send }: View) {
  const [selected, set] = useState(text(p.selected) || "canvas");
  return (
    <Frame name="Deck">
      <nav aria-label="Sections">
        {list(p.sections).map((s) => (
          <Fragment key={text(s.id)}>
            {Boolean(s.group) && <div className="f02-deck-heading">{text(s.group)}</div>}
            <button
              type="button"
              className="f02-deck-item"
              aria-pressed={selected === s.id}
              onClick={() => {
                set(text(s.id));
                send("deck.select", { id: s.id });
              }}
            >
              <ShellIcon name={label(s)} />
              {label(s)}{" "}
              {s.count != null && (
                <span className="f02-count">
                  {text(s.prefix)}
                  {number(s.count)}
                </span>
              )}
            </button>
          </Fragment>
        ))}
      </nav>
    </Frame>
  );
}

export function RoomShell({ p, send, build }: View) {
  return (
    <Frame name="RoomShell" state="live">
      <TopBar
        roomActions
        p={{ title: p.coalition, presence: p.presence, stage: p.stage }}
        send={send}
      />
      <div className="ck-room-body">
        <Deck p={{ sections: p.deck }} send={send} />
        <div className="ck-canvas">
          <Children value={p.canvas} build={build} />
          <div className="ck-room-tray">
            <Children value={p.tray} build={build} />
          </div>
        </div>
        <aside className="ck-room-agent">
          <Children value={p.dock} build={build} />
        </aside>
      </div>
    </Frame>
  );
}

export function AgentDock({ p, send }: View) {
  const [message, set] = useState("");
  return (
    <Frame name="AgentDock">
      <header className="f02-agent-head">
        <span className="f02-agent-avatar">Y</span>
        <b>Your agent</b>
        <span>private to you</span>
      </header>
      <div className="f02-messages">
        {list(p.messages).map((m, i) => (
          <div
            key={text(m.id) || String(i)}
            className={`f02-message f02-message-${text(m.role) || "agent"}`}
          >
            {m.role === "tool" && <span className="f02-tool">tool</span>}
            {label(m)}
          </div>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (message.trim()) {
            send("agent.say", { text: message });
            set("");
          }
        }}
      >
        <div className="f02-agent-input">
          <input
            aria-label="Message your agent"
            placeholder="Ask your agent…"
            value={message}
            onChange={(e) => set(e.target.value)}
          />
          <button type="submit" aria-label="Send" disabled={!message.trim()}>
            <ShellIcon name="Send" />
          </button>
        </div>
      </form>
    </Frame>
  );
}

export function PhoneShell({ p, send, build }: View) {
  const tabs = (text(p.tabs) || "Now|Plans|People|Agent").split("|");
  const [tab, set] = useState(tabs[0]);
  return (
    <Frame name="PhoneShell">
      <div className="ck-phone">
        <div className="f02-phone-status">
          <span>22:21</span>
          <span>5G ▮▮▮</span>
        </div>
        <Children value={p.header} build={build} />
        <div className="ck-phone-stack">
          <Children value={p.stack} build={build} />
        </div>
        <nav aria-label="Phone tabs">
          {tabs.map((t) => (
            <button
              type="button"
              key={t}
              aria-pressed={t === tab}
              onClick={() => {
                set(t);
                send("tab.select", { id: t });
              }}
            >
              <ShellIcon name={t === "Now" ? "Canvas" : t} />
              {t}
            </button>
          ))}
        </nav>
      </div>
    </Frame>
  );
}
