// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { ShellIcon } from "./shell";
import { Children, Frame, label, list, number, obj, text, type View } from "./ui";
import "./templates.css";

export function PageHeader({ p }: View) {
  const tabs = list(p.tabs);
  return (
    <Frame name="PageHeader">
      <nav className="f02-crumbs" aria-label="Breadcrumb">
        {list(p.crumbs).map((crumb, i) => (
          <span key={label(crumb)}>
            {i > 0 && <i>/</i>}
            {label(crumb)}
          </span>
        ))}
      </nav>
      <div className="f02-page-heading">
        <div>
          <span className="f02-eyebrow">{text(p.eyebrow)}</span>
          <h2>{text(p.title)}</h2>
        </div>
        <div className="f02-page-actions">
          {number(p.actions) > 0 && <span className="ck-action">Share</span>}
          {number(p.actions) > 1 && <span className="ck-action ck-primary">Decide</span>}
        </div>
      </div>
      {tabs.length > 0 && (
        <div className="f02-page-tabs">
          {tabs.map((tab, i) => (
            <span key={label(tab)} aria-current={i === 0 ? "page" : undefined}>
              {label(tab)}
              {tab.count != null && <span className="f02-count">{number(tab.count)}</span>}
            </span>
          ))}
        </div>
      )}
    </Frame>
  );
}

export function SplitView({ p, send, build }: View) {
  const [picked, setPicked] = useState<string | null>(null);
  const selected = picked ?? text(p.selected);
  return (
    <Frame name="SplitView">
      <div className="f02-split-frame" data-selected={Boolean(selected)}>
        <nav aria-label="Items">
          {list(p.items).map((item) => (
            <button
              type="button"
              key={text(item.id)}
              aria-pressed={selected === item.id}
              onClick={() => {
                setPicked(text(item.id));
                send("split.select", { id: item.id });
              }}
            >
              {label(item)}
              {item.badge ? <span className="f02-count">{text(item.badge)}</span> : null}
            </button>
          ))}
        </nav>
        <div className="f02-split-detail">
          <button
            className="f02-split-back f02-text-action"
            type="button"
            onClick={() => {
              setPicked("");
              send("split.select", { id: "" });
            }}
          >
            Back to list
          </button>
          <Children value={p.detail} build={build} />
        </div>
      </div>
    </Frame>
  );
}

function Emphasis({ value, emphasis }: { value: string; emphasis: string }) {
  const at = emphasis ? value.indexOf(emphasis) : -1;
  return at < 0 ? (
    value
  ) : (
    <>
      {value.slice(0, at)}
      <b>{emphasis}</b>
      {value.slice(at + emphasis.length)}
    </>
  );
}

export function NotificationCenter({ p, send }: View) {
  const items = list(p.items);
  const [read, setRead] = useState(false);
  const [open, setOpen] = useState(true);
  const unread = read
    ? 0
    : items.filter((item) => !item.read).reduce((total, item) => total + number(item.count, 1), 0);
  return (
    <Frame name="NotificationCenter" state={unread ? "unread" : "empty"}>
      <button
        type="button"
        className="f02-bell"
        aria-label="Notifications"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <ShellIcon name="Bell" />
        {unread > 0 && <span>{unread}</span>}
      </button>
      {open && (
        <div className="f02-notification-menu">
          <header>
            <b>Updates</b>
            <button
              type="button"
              className="f02-text-action"
              onClick={() => {
                setRead(true);
                send("notifications.read");
              }}
            >
              Mark all read
            </button>
          </header>
          {items.length ? (
            items.map((item, i) => (
              <button
                type="button"
                className="f02-notification"
                key={text(item.ref) || String(i)}
                data-read={read || Boolean(item.read)}
                onClick={() => send("notification.open", { ref: item.ref })}
              >
                <i />
                <span>
                  <span>
                    <Emphasis value={label(item)} emphasis={text(item.emphasis)} />
                  </span>
                  <small>
                    {text(item.time)}
                    {item.summary ? ` · ${text(item.summary)}` : ""}
                  </small>
                </span>
              </button>
            ))
          ) : (
            <p>You're all caught up.</p>
          )}
        </div>
      )}
    </Frame>
  );
}

export function AccountMenu({ p, send }: View) {
  const identity = obj(p.identity);
  const agents = list(p.agents);
  const [expanded, setExpanded] = useState(false);
  const pick = (id: unknown) => send("account.pick", { id });
  return (
    <Frame name="AccountMenu" state="open">
      <header>
        <span className="ck-avatar">
          {label(identity)
            .replace(/^Member /, "")
            .slice(0, 1)}
        </span>
        <div>
          <b>{label(identity)}</b>
          <small>owner key {text(identity.kid)}</small>
        </div>
      </header>
      <hr />
      <button
        type="button"
        aria-label={agents.length === 1 ? label(agents[0] ?? {}) : "My agents"}
        onClick={() => {
          setExpanded(!expanded);
          if (agents.length === 1) pick(agents[0]?.id);
        }}
      >
        My agents<span>{agents.length}</span>
      </button>
      {expanded &&
        agents.length > 1 &&
        agents.map((agent) => (
          <button type="button" key={text(agent.id)} onClick={() => pick(agent.id)}>
            {label(agent)}
          </button>
        ))}
      <button type="button" onClick={() => pick("vault")}>
        Vault and data
      </button>
      <button type="button" onClick={() => pick("channels")}>
        Channels<span>{list(p.channels).map(label).join(" · ")}</span>
      </button>
      <button type="button" onClick={() => pick("appearance")}>
        Appearance<span>{text(p.appearance) || "system"}</span>
      </button>
      <hr />
      <button type="button" onClick={() => pick("export")}>
        Export my log
      </button>
      <button type="button" className="f02-sign-out" onClick={() => pick("sign-out")}>
        Sign out
      </button>
    </Frame>
  );
}

export function BoardTemplate({ p, send }: View) {
  return (
    <Frame name="BoardTemplate">
      <div className="f02-board">
        {list(p.columns).map((column) => {
          const cards = list(p.cards).filter((card) => card.status === column.id);
          return (
            <section key={text(column.id)}>
              <header>
                <b>{label(column)}</b>
                <span className="f02-count">{cards.length}</span>
              </header>
              {cards.length ? (
                cards.map((card) => (
                  <button
                    type="button"
                    className={`f02-board-card${card.status === "negotiating" ? " f02-board-live" : ""}`}
                    key={text(card.id)}
                    onClick={() => send("card.open", { id: card.id })}
                  >
                    <b>{label(card)}</b>
                    {card.meta ? <small>{text(card.meta)}</small> : null}
                    {card.status === "decided" && <span className="f02-agreed">Agreed</span>}
                    {Array.isArray(card.people) && (
                      <span className="f02-board-people">
                        {list(card.people).map((person) => (
                          <span className="ck-avatar" key={label(person)}>
                            {label(person)}
                          </span>
                        ))}
                        <small>{text(card.offers)}</small>
                      </span>
                    )}
                  </button>
                ))
              ) : (
                <div className="f02-board-empty">Nothing done yet</div>
              )}
            </section>
          );
        })}
      </div>
    </Frame>
  );
}
