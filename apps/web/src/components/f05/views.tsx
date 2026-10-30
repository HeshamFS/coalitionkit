// SPDX-License-Identifier: Apache-2.0
import { Frame, list, num, obj, type Props, rows, str, texts } from "./shared";
import "../../styles/f05.css";
import "./fonts.css";
export function CoalitionHeader({ p, send }: Props) {
  const counts = obj(p.counts),
    budget = obj(p.budget);
  return (
    <Frame name="CoalitionHeader" className="card f05-header">
      <div className="row f05-header-top">
        <svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">
          <circle cx="24" cy="20" r="5" fill="var(--blue)" />
          {[
            [14, 9, 3],
            [9, 17, 1],
            [9, 25, 5],
            [14, 32, 0],
            [22, 35, 0],
            [22, 5, -1],
          ].map(([x, y, seat]) => (
            <circle
              key={`${x}-${y}`}
              cx={x}
              cy={y}
              r="3"
              fill={
                seat === 0
                  ? "var(--line-strong)"
                  : seat === -1
                    ? "var(--ink)"
                    : `var(--seat-${seat})`
              }
            />
          ))}
        </svg>
        <div className="col grow">
          <span className="eyebrow">Coalition · pack: {str(p.pack)}</span>
          <h2>{str(p.title)}</h2>
          <span className="small">{str(p.goal)}</span>
        </div>
        <div className="col f05-header-state">
          <span
            className={`tag ${p.yourState === "needs-you" ? "t-needs" : p.yourState === "agreed" ? "t-agreed" : p.yourState === "changed" ? "t-changed" : p.yourState === "blocked" ? "t-blocked" : "t-private"}`}
          >
            {str(p.yourState)
              .split("-")
              .map((word, i) => (i === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word))
              .join(" ")}
          </span>
          {Boolean(counts.days) && (
            <span className="st">
              day {str(obj(counts.days).elapsed)} of {str(obj(counts.days).total)}
            </span>
          )}
        </div>
      </div>
      <div className="row wrap f05-header-counts">
        <span className="small">
          <b>{str(counts.people)}</b> members · <b>{str(counts.agents)}</b> agents ·{" "}
          <b>{str(counts.watchers)}</b> watcher
        </span>
        <span className="small">
          <b>{str(counts.tasks)}</b> tasks · <b>{str(counts.plans)}</b> plans
        </span>
        <span className="small">
          budget <b>€{str(budget.used)}</b> of €{str(budget.cap)}
        </span>
        <button
          type="button"
          className="f05-text-action h-right"
          onClick={() => send("charter.open")}
        >
          Charter r{str(p.revision)}
        </button>
      </div>
    </Frame>
  );
}
export function StageTrack({ p }: Props) {
  const stages = list(p.stages),
    current = str(p.current);
  return (
    <Frame name="StageTrack">
      <ol className="f05-stages">
        {stages.map((s) => {
          const r = obj(s),
            label = str(r.label ?? s),
            active = current === str(r.id ?? s) || r.state === "now";
          return (
            <li key={label} aria-current={active ? "step" : undefined}>
              <span className="f05-stage-bar">
                <span
                  style={{
                    width: r.state === "done" ? "100%" : active ? "55%" : "0%",
                    background: active ? "var(--blue)" : "var(--ink-3)",
                  }}
                />
              </span>
              <span className="st">
                {label}
                {active &&
                  (r.deciders
                    ? ` ${str(p.progress)}/${str(r.deciders)}`
                    : ` ${str(p.progress)} answered`)}
              </span>
            </li>
          );
        })}
      </ol>
    </Frame>
  );
}
export function ParticipantCard({ p, send }: Props) {
  const state = str(p.state);
  const role = texts(p.roles);
  return (
    <Frame name="ParticipantCard" state={state} className="card f05-participant">
      <div className="row">
        <span
          className={`av av-lg f05-avatar-${state}`}
          style={{
            background: state === "left" ? "var(--surface-3)" : `var(--seat-${num(p.seat, 1)})`,
          }}
        >
          {str(p.participant).slice(-1)}
        </span>
        <div className="col grow">
          <button
            type="button"
            className="f05-person"
            onClick={() => send("participant.open", { participant: p.participant })}
          >
            {str(p.participant)}
          </button>
          <span className="st">{role}</span>
        </div>
        {state === "acting" && <span className="spinner" role="status" aria-label="Acting" />}
      </div>
      {!["watcher", "invited", "left"].includes(state) && (
        <div className="row wrap">
          {list(p.capabilities).map((c) => (
            <span className="chip" key={str(c)}>
              {str(c)}
            </span>
          ))}
        </div>
      )}
      {state === "watcher" && <span className="small">sees results, never raw data</span>}
      {state === "invited" && <span className="small">{str(p.act)}</span>}
      {state === "left" && <span className="small">{str(p.act)}</span>}
      {state === "acting" ? (
        <span className="small blue">{str(p.act)}</span>
      ) : state === "invited" ? (
        <button
          type="button"
          className="f05-text-action"
          onClick={() => send("participant.open", { participant: p.participant })}
        >
          Resend
        </button>
      ) : (
        <span
          className={`tag ${{ agreed: "t-agreed", owes: "t-needs", watcher: "t-private", left: "t-blocked" }[state] ?? ""}`}
        >
          {{ agreed: "Agreed", owes: "Needs you", watcher: "Private", left: "Blocked" }[state] ??
            state}
        </span>
      )}
    </Frame>
  );
}
export function VendorBadge({ p }: Props) {
  return (
    <Frame name="VendorBadge">
      <span className="badge b-estimate">
        {p.framework === "ADK" && (
          <svg className="ico f05-vendor-icon" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="4" y="4" width="16" height="16" rx="4" />
          </svg>
        )}
        {str(p.transport)} · {str(p.framework)}
      </span>
    </Frame>
  );
}
export function AgentPresence({ p }: Props) {
  return (
    <Frame name="AgentPresence" state={str(p.state)}>
      <div className="row">
        <span
          className={`av av-sq presence ${p.state === "idle" ? "s3 presence-away" : p.state === "offline" ? "s5 presence-off" : "s1"}`}
        >
          {str(p.agent).split(" · ")[0]?.slice(-1)}
        </span>
        <div className="col f05-agent-details">
          <span className="lbl">{str(p.agent)}</span>
          <div className="st">
            {str(p.state)}
            {p.state === "idle" && Boolean(p.nextReadingAt) && (
              <>
                {" "}
                · next reading{" "}
                <time dateTime={str(p.nextReadingAt)} title={str(p.nextReadingAt)}>
                  {str(p.nextReadingAt).match(/T(\d{2}:\d{2})/)?.[1] ?? str(p.nextReadingAt)}
                </time>
              </>
            )}
            {p.latencyMs ? ` · ${str(p.latencyMs)} ms` : ""}
            {p.pinnedKid
              ? ` · card pinned ${str(p.pinnedKid)}`
              : p.state === "offline"
                ? " · answers queue"
                : ""}
          </div>
        </div>
      </div>
    </Frame>
  );
}
export function RoleChip({ p }: Props) {
  return (
    <Frame name="RoleChip" state={p.open ? "open" : "held"}>
      <span className={`chip ${p.open ? "f05-open" : p.role === "organizer" ? "chip-on" : ""}`}>
        {str(p.role)}
        {p.open ? " (open)" : ""}
      </span>
    </Frame>
  );
}
export function CharterCard({ p, send }: Props) {
  return (
    <Frame name="CharterCard" className="card f05-charter">
      <div className="row">
        <svg className="ico blue" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3l8 4v6c0 4-3.5 7-8 8-4.5-1-8-4-8-8V7z" />
        </svg>
        <b>Charter</b>
        <span className="h-right badge b-signed">
          r{str(p.revision)} · signed by {list(p.signedBy).length}
        </span>
      </div>
      <ol>
        {rows(p.rules).map((r) => (
          <li key={str(r.n)}>
            <span className="num st">{str(r.n)}</span>
            <span>{str(r.text)}</span>
          </li>
        ))}
      </ol>
      <div className="row">
        <span className="small">
          Roles:{" "}
          {rows(p.roles)
            .map(
              (r) =>
                `${str(r.name)}${num(r.min) > 1 && num(r.min) === num(r.max) ? ` ×${num(r.min)}` : ""}`,
            )
            .join(", ")}
        </span>
        <button
          className="f05-text-action h-right"
          type="button"
          onClick={() => send("charter.history")}
        >
          History
        </button>
      </div>
    </Frame>
  );
}
export function RoleMatrix({ p }: Props) {
  return (
    <Frame name="RoleMatrix">
      <div className="f05-scroll">
        <table className="tbl">
          <thead>
            <tr>
              <th>Can</th>
              {list(p.roles).map((r) => (
                <th key={str(r)}>
                  {{ organizer: "Org", member: "Member", watcher: "Watch" }[str(r)] ?? str(r)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows(p.rights).map((r) => (
              <tr key={str(r.action)}>
                <td>{str(r.action)}</td>
                {list(p.roles).map((role) => (
                  <td
                    key={str(role)}
                    className={
                      str(obj(r.rights)[str(role)]) === "✓" ||
                      str(obj(r.rights)[str(role)]) === "propose"
                        ? undefined
                        : "mut3"
                    }
                  >
                    {str(obj(r.rights)[str(role)]) || "–"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Frame>
  );
}
export { ActsForGraph, SeatRing } from "./graphs";
export { InviteList, LeaveControl, PackChip, Roster } from "./membership";
