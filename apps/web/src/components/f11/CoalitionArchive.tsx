// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

function ended(value: unknown) {
  const raw = text(value);
  const date = new Date(raw);
  return /^\d{4}-\d{2}-\d{2}/.test(raw) && Number.isFinite(date.valueOf())
    ? new Intl.DateTimeFormat("en-GB", {
        weekday: "short",
        day: "numeric",
        month: "short",
        timeZone: "UTC",
      })
        .format(date)
        .replace(",", "")
    : raw;
}
export function CoalitionArchive({ p, send }: { p: Props; send: Send }) {
  return rows(p.items).length ? (
    <>
      <div className="family-table">
        <table className="tbl">
          <thead>
            <tr>
              <th>Coalition</th>
              <th>Pack</th>
              <th>Ended</th>
              <th>Outcome</th>
              <th className="f11-right">Your cost</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {rows(p.items).map((item, i) => (
              <tr key={text(item.coalition) || `${i}`}>
                <td>
                  {item.outcome === "reached" ? (
                    <b>{text(item.coalition)}</b>
                  ) : (
                    text(item.coalition)
                  )}
                </td>
                <td>{text(item.pack)}</td>
                <td className="num">
                  <time dateTime={text(item.ended)} title={text(item.ended)}>
                    {ended(item.ended)}
                  </time>
                </td>
                <td>
                  <span
                    className={item.outcome === "reached" ? "tag t-agreed" : "badge b-estimate"}
                  >
                    {item.outcome === "reached" ? "Agreed" : text(item.outcome)}
                  </span>
                </td>
                <td className="num f11-right">{text(item.yourCost)}</td>
                <td>
                  <button
                    type="button"
                    className="f11-link small"
                    aria-label={`Open ${text(item.coalition)}`}
                    onClick={() => send("archive.open", { id: item.coalition })}
                  >
                    Open
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row small">
        Sealed logs open read-only; nothing here is shared unless you export it
      </div>
    </>
  ) : (
    <div className="f11-empty card card-dashed">
      <svg width="46" height="46" viewBox="0 0 40 40" aria-hidden="true">
        <circle cx="24" cy="20" r="5" fill="var(--blue)" />
        {[
          [14, 9],
          [9, 17],
          [9, 25],
          [14, 32],
          [22, 35],
          [22, 5],
        ].map(([cx, cy]) => (
          <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="3" fill="var(--bg-dot)" />
        ))}
      </svg>
      <b>No coalitions yet</b>
      <span className="small">
        When one ends, its sealed log and what you chose to keep land here.
      </span>
      <a className="btn btn-sm btn-primary" href="/">
        Start one
      </a>
    </div>
  );
}
