// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Action, Frame, list, num, obj, Person, type Props, rows, str } from "./shared";
export function Roster({ p, send }: Props) {
  const members = rows(p.members);
  const revision = Math.max(0, ...members.map((member) => num(member.acceptedRevision)));
  return (
    <Frame name="Roster" className="f05-roster">
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
            {members.map((r, i) => (
              <tr key={str(r.participant)} className={r.state === "changed" ? "hov" : undefined}>
                <td>
                  <Person name={r.participant} seat={[3, 1, 5, 4][i % 4]} />
                </td>
                <td>{list(r.roles).map(str).join(", ")}</td>
                <td>{str(r.agents)}</td>
                <td className="num">
                  r{str(r.acceptedRevision)}{" "}
                  {num(r.acceptedRevision) < revision ? (
                    <span className="badge b-estimate">old</span>
                  ) : (
                    "✓"
                  )}
                </td>
                <td className="r num">{r.state === "watcher" ? "–" : `${str(r.load)} h`}</td>
                <td>
                  <span
                    className={`tag ${r.state === "agreed" ? "t-agreed" : r.state === "changed" ? "t-changed" : r.state === "watcher" ? "t-private" : "t-needs"}`}
                  >
                    {r.state === "watcher"
                      ? "Private"
                      : r.state === "owes"
                        ? "Needs you"
                        : r.state === "changed"
                          ? "Changed"
                          : "Agreed"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {members
        .filter((member) => num(member.acceptedRevision) < revision)
        .map((member) => (
          <div className="row small" key={str(member.participant)}>
            <span>
              {str(member.participant)}'s offers don't count until it accepts r{revision}
            </span>
            <button
              type="button"
              className="f05-text-action h-right"
              onClick={() => send("member.remind", { participant: member.participant })}
            >
              Remind {str(member.participant)}
            </button>
          </div>
        ))}
    </Frame>
  );
}
export function PackChip({ p, send }: Props) {
  const pack = obj(p.pack);
  return (
    <Frame name="PackChip" className="f05-pack">
      <div className="row wrap">
        <button
          type="button"
          className="chip chip-on"
          onClick={() => send("pack.open", { pack: pack.id })}
        >
          <PackageIcon small />
          {str(pack.name)}
        </button>
        {rows(pack.alternatives).map((alternative) => (
          <button
            type="button"
            className="chip"
            key={str(alternative.id)}
            onClick={() => send("pack.open", { pack: alternative.id })}
          >
            {str(alternative.name)}
          </button>
        ))}
      </div>
      <article className="card">
        <div className="row">
          <PackageIcon />
          <b>{str(pack.name)}</b>
          <span className="h-right st">v{str(pack.version)}</span>
        </div>
        {Boolean(pack.description) && <span className="small">{str(pack.description)}</span>}
        <dl className="kv">
          <dt>Views</dt>
          <dd>{list(pack.views).length}</dd>
          <dt>Policies</dt>
          <dd>{list(pack.policies).length} (allow, redact only)</dd>
          <dt>Signed by</dt>
          <dd className="mono">pack author {str(pack.authorKid)}</dd>
        </dl>
      </article>
    </Frame>
  );
}
function PackageIcon({ small = false }: { small?: boolean }) {
  return (
    <svg className={`ico${small ? " ico-sm" : ""}`} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M21 8l-9-5-9 5 9 5zM3 8v8l9 5 9-5V8" />
    </svg>
  );
}
export function LeaveControl({ p, send }: Props) {
  const [confirm, setConfirm] = useState(false);
  return (
    <Frame name="LeaveControl" state={confirm ? "confirming" : "ready"} className="f05-leave">
      <article className="card">
        <b>Leave the coalition</b>
        <ul>
          {list(p.consequences).map((c, i) => (
            <li className="row small" key={str(c)}>
              <svg
                className={`ico ico-sm ${i === list(p.consequences).length - 1 ? "f05-safe" : "f05-warning"}`}
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  d={i === list(p.consequences).length - 1 ? "M5 12l5 5 9-10" : "M12 3l10 18H2z"}
                />
              </svg>
              <span>{str(c)}</span>
            </li>
          ))}
        </ul>
        <button type="button" className="btn btn-sm btn-danger" onClick={() => setConfirm(true)}>
          Leave…
        </button>
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
      <div className="card card-2">
        <span className="small">
          Members can't remove each other. The organizer can propose a new charter; anyone who
          doesn't accept it leaves.
        </span>
      </div>
    </Frame>
  );
}
export function InviteList({ p, send }: Props) {
  const invitations = rows(p.invitations);
  const invitation = (r: Record<string, unknown>) => (
    <div className="f05-invite" key={str(r.participant)}>
      <span className={`av ${r.state === "joined" ? "s4" : "s2 f05-invited-avatar"}`}>
        {str(r.participant).slice(-1)}
      </span>
      <div className="col grow">
        <span className="h-title">
          {str(r.participant)}
          {r.state !== "joined" ? ` · ${str(r.role)} role` : ""}
        </span>
        <span className="st">
          {r.state === "joined"
            ? `joined ${str(r.sentAt)} · observe only`
            : `${str(r.channel)} sent ${str(r.sentAt)} · single use · expires in ${str(r.expires)}`}
        </span>
      </div>
      <span className={`badge ${r.state === "joined" ? "b-signed" : "b-estimate"}`}>
        {str(r.state)}
      </span>
      {r.state === "invited" && (
        <button
          className="btn btn-sm btn-ghost"
          type="button"
          onClick={() => send("invite.revoke", { participant: r.participant })}
        >
          Revoke
        </button>
      )}
    </div>
  );
  return (
    <Frame name="InviteList" className="f05-invites">
      <div>
        {invitations.filter((r) => r.state !== "joined").map(invitation)}
        {list(p.openSeats).map((role) => (
          <div className="f05-invite" key={str(role)}>
            <span className="av f05-empty-avatar">?</span>
            <div className="col grow">
              <span className="h-title">Open seat · {str(role)}</span>
              <span className="st">
                anyone with the pack's {str(role)} capability can be invited
              </span>
            </div>
            <Action onClick={() => send("invite.send", { role })}>Invite</Action>
          </div>
        ))}
        {invitations.filter((r) => r.state === "joined").map(invitation)}
      </div>
      <div className="row small">
        <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3l8 4v6c0 4-3.5 7-8 8-4.5-1-8-4-8-8V7z" />
        </svg>
        Joins are checked against the invitation and the agent's pinned card; a used or revoked link
        does nothing.
      </div>
    </Frame>
  );
}
