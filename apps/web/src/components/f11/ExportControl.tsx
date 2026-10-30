// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { type Props, rows, type Send, text, usePreviewState } from "../f08/shared";
import "../../styles/f11.css";
export function ExportControl({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  const items = rows(p.items);
  const [selected, setSelected] = useState(items.map((i) => Boolean(i.included)));
  const [confirm, setConfirm] = useState(false);
  if (preview === "wiped") return <span className="small">Vault wiped</span>;
  if (preview === "exporting") return <span role="status">Preparing your export…</span>;
  return (
    <>
      <b className="f11-control-title">Your data from this coalition</b>
      <div className="f11-export-items">
        {items.map((item, i) => (
          <label className="row" key={text(item.kind)}>
            <input
              type="checkbox"
              checked={selected[i] ?? false}
              onChange={(e) =>
                setSelected((old) => old.map((v, j) => (j === i ? e.target.checked : v)))
              }
            />
            <span className="small">{text(item.kind)}</span>
          </label>
        ))}
      </div>
      <div className="row">
        <button
          type="button"
          className="btn btn-sm btn-primary"
          aria-label="Download ZIP"
          onClick={() =>
            send("export.zip", {
              items: items
                .filter((_, i) => selected[i])
                .map((item) => ({ ...item, included: true })),
            })
          }
        >
          Export .zip
        </button>
        <button type="button" className="btn btn-sm btn-danger" onClick={() => setConfirm(true)}>
          Wipe my vault data
        </button>
      </div>
      {confirm && (
        <fieldset className="card" aria-label="Confirm vault wipe">
          <span className="small">Permanently remove your vault data?</span>
          <div className="row">
            <button
              type="button"
              className="btn btn-sm btn-danger"
              onClick={() => {
                send("vault.wipe");
                setConfirm(false);
              }}
            >
              Confirm wipe
            </button>
            <button type="button" className="btn btn-sm" onClick={() => setConfirm(false)}>
              Cancel
            </button>
          </div>
        </fieldset>
      )}
      <span className="st">the shared log can't be erased; it never held your vault values</span>
    </>
  );
}
