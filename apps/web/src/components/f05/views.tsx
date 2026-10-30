// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import {
  Action,
  Frame,
  list,
  Mark,
  Meter,
  num,
  obj,
  Person,
  type Props,
  rows,
  str,
  texts,
} from "./shared";
import "../../styles/f05.css";
export function CoalitionHeader({ p, send }: Props) {
  const counts = obj(p.counts),
    budget = obj(p.budget);
  return (
    <Frame name="CoalitionHeader" className="f05-header">
      <div className="row sp">
        <h2>{str(p.title)}</h2>
        <Mark state={p.yourState} />
      </div>
      <p>{str(p.goal)}</p>
      <div className="row wrap">
        {Object.entries(counts).map(([k, v]) => (
          <span key={k}>
            {str(v)} {k}
          </span>
        ))}
      </div>
      <div className="row sp">
        <span>{str(p.pack)}</span>
        <Action onClick={() => send("charter.open")}>Charter r{str(p.revision)}</Action>
        <span>
          Budget {str(budget.used)} / {str(budget.cap)}
        </span>
      </div>
      <Meter label="Budget used" value={(100 * num(budget.used)) / Math.max(1, num(budget.cap))} />
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
              <span>{label}</span>
              {active && <small>{str(p.progress)} answered</small>}
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
        {str(p.transport)} · {str(p.framework)}
      </span>
    </Frame>
  );
}
export function AgentPresence({ p }: Props) {
  return (
    <Frame name="AgentPresence" state={str(p.state)}>
      <div className="row">
        <span className={`f05-presence ${str(p.state)}`} />
        <div>
          <b>{str(p.agent)}</b>
          <div className="small">
            {str(p.state)}
            {p.latencyMs ? ` · ${str(p.latencyMs)} ms` : ""} · card pinned {str(p.pinnedKid)}
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
            .map((r) => str(r.name))
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
                <th key={str(r)}>{str(r)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows(p.rights).map((r) => (
              <tr key={str(r.action)}>
                <td>{str(r.action)}</td>
                {list(p.roles).map((role) => (
                  <td key={str(role)}>{str(obj(r.rights)[str(role)]) || "–"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Frame>
  );
}
export function Roster({ p, send }: Props) {
  return (
    <Frame name="Roster">
      <div className="f05-scroll">
        <table className="tbl">
          <thead>
            <tr>
              {["Member", "Roles", "Agents", "Accepted charter", "Hours held", "State"].map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows(p.members).map((r, i) => (
              <tr key={str(r.participant)}>
                <td>
                  <Person name={r.participant} seat={i + 1} />
                </td>
                <td>{texts(r.roles)}</td>
                <td>{str(r.agents)}</td>
                <td>r{str(r.acceptedRevision)}</td>
                <td>{str(r.load)} h</td>
                <td>
                  <Mark state={r.state} />
                  {r.state === "owes" && (
                    <Action onClick={() => send("member.remind", { participant: r.participant })}>
                      Remind {str(r.participant)}
                    </Action>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Frame>
  );
}
export function PackChip({ p, send }: Props) {
  const pack = obj(p.pack);
  return (
    <Frame name="PackChip">
      <Action onClick={() => send("pack.open", { pack: pack.id })}>{str(pack.name)}</Action>
      <article className="card">
        <div className="row sp">
          <b>{str(pack.name)}</b>
          <small>v{str(pack.version)}</small>
        </div>
        <dl className="kv">
          <dt>Views</dt>
          <dd>{list(pack.views).length}</dd>
          <dt>Policies</dt>
          <dd>{list(pack.policies).length} (allow, redact only)</dd>
          <dt>Signed by</dt>
          <dd>{str(pack.authorKid)}</dd>
        </dl>
      </article>
    </Frame>
  );
}
export function LeaveControl({ p, send }: Props) {
  const [confirm, setConfirm] = useState(false);
  return (
    <Frame name="LeaveControl" state={confirm ? "confirming" : "ready"}>
      <article className="card">
        <b>Leave the coalition</b>
        <ul>
          {list(p.consequences).map((c) => (
            <li key={str(c)}>{str(c)}</li>
          ))}
        </ul>
        <Action onClick={() => setConfirm(true)}>Leave…</Action>
        {confirm && (
          <div role="dialog" aria-modal="true" aria-label="Confirm leaving">
            <p>Leave permanently? You cannot rejoin.</p>
            <Action onClick={() => setConfirm(false)}>Cancel</Action>
            <Action
              onClick={() => {
                send("coalition.leave");
                setConfirm(false);
              }}
            >
              Confirm leave
            </Action>
          </div>
        )}
      </article>
      <p className="small">
        Members cannot remove each other. A new charter requires each member's acceptance.
      </p>
    </Frame>
  );
}
export function InviteList({ p, send }: Props) {
  return (
    <Frame name="InviteList">
      {rows(p.invitations).map((r) => (
        <div className="f05-invite" key={str(r.participant)}>
          <Person name={r.participant} />
          <span>
            {str(r.role)}
            <small>
              {str(r.channel)} · {str(r.sentAt)} · expires {str(r.expires)}
            </small>
          </span>
          <Mark state={r.state} />
          {r.state === "invited" && (
            <Action onClick={() => send("invite.revoke", { participant: r.participant })}>
              Revoke
            </Action>
          )}
        </div>
      ))}
      {list(p.openSeats).map((r) => (
        <div className="f05-invite" key={str(r)}>
          <span>Open seat · {str(r)}</span>
          <Action onClick={() => send("invite.send", { role: r })}>Invite</Action>
        </div>
      ))}
    </Frame>
  );
}
export { ActsForGraph, SeatRing } from "./graphs";
