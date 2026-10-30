// SPDX-License-Identifier: Apache-2.0
import { Action, Fields, type Props, rows, type Send, text } from "./shared";
import "../../styles/f08.css";

export function DurableConsent({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      {rows(p.grants).map((g, i) => (
        <div className="card" key={text(g.grantee) || `${i}`}>
          <Fields
            values={{
              Grantee: g.grantee,
              Action: g.action,
              Scope: g.scope,
              Expires: g.expires,
            }}
          />
          <Action label="Revoke" event="grant.revoke" send={send} data={g} />
        </div>
      ))}
      {rows(p.requests).map((r, i) => (
        <div className="row" key={text(r.id) || `${i}`}>
          <span>{text(r.action)}</span>
          <Action label="Allow" event="grant.allow" send={send} data={r} />
        </div>
      ))}
    </>
  );
}
