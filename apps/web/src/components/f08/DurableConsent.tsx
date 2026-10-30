// SPDX-License-Identifier: Apache-2.0
import { Action, type Props, rows, type Send, text } from "./shared";
export function DurableConsent({ p, send }: { p: Props; send: Send }) {
  const entries = [
    ...rows(p.grants).map((g) => ({ ...g, pending: false })),
    ...rows(p.requests).map((r) => ({ ...r, pending: true })),
  ];
  return (
    <>
      <div className="family-table">
        <table className="tbl">
          <thead>
            <tr>
              {["Lets", "Do", "For", "Until", ""].map((h, i) => (
                <th key={h || i}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, i) => {
              const g: Props = entry;
              return (
                <tr key={text(g.id) || i} className={g.pending ? "hov" : undefined}>
                  <td>
                    <span className="row">
                      <span className={`av av-xs ${g.pending ? "s1" : "av-sq sh"}`}>
                        {text(g.grantee).split(" ").at(-1)?.slice(0, 1)}
                      </span>
                      {text(g.grantee)}
                    </span>
                  </td>
                  <td>{text(g.action)}</td>
                  <td>{text(g.scope)}</td>
                  <td>{text(g.expires) || "—"}</td>
                  <td>
                    {g.pending ? (
                      <Action
                        label="Allow"
                        event="grant.allow"
                        send={send}
                        data={rows(p.requests)[i - rows(p.grants).length]}
                      />
                    ) : (
                      <button
                        className="f08-link small"
                        type="button"
                        onClick={() => send("grant.revoke", rows(p.grants)[i])}
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="row small">
        <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3l8 4v6c0 4-3.5 7-8 8-4.5-1-8-4-8-8V7z" />
        </svg>
        Stored on the host, signed by you, checked on every use. Revoking takes effect on the next
        request.
      </div>
    </>
  );
}
