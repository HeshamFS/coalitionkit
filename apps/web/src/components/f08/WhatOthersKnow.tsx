// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "./shared";
export function WhatOthersKnow({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="family-table">
        <table className="tbl">
          <thead>
            <tr>
              {["Who", "Knows", "Doesn't know", "Because"].map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows(p.rows).map((r, i) => (
              <tr key={text(r.participant)}>
                <td>
                  <span className="row">
                    <span
                      className={`av av-xs ${r.participant === "Host" ? "av-sq sh" : `s${[1, 5, 4][i % 3]}`}`}
                    >
                      {text(r.participant).split(" ").at(-1)?.slice(0, 1)}
                    </span>
                    {text(r.participant)}
                  </span>
                </td>
                <td>{text(r.knows)}</td>
                <td>{text(r.notKnows)}</td>
                <td>
                  {text(r.because).startsWith("task:") ? (
                    <>
                      <span className="scope">{text(r.because).split(" · ")[0]}</span> PSI
                    </>
                  ) : (
                    text(r.because)
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row small">
        <span>Built from the log and your vault answers, not from guesses</span>
        <button className="h-right f08-link" type="button" onClick={() => send("view.export")}>
          Export this view
        </button>
      </div>
    </>
  );
}
