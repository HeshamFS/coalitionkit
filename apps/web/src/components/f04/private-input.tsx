// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Frame, label, list, obj, text, type View } from "../f02/ui";
import "./details.css";

export function LimitField({ p, send }: View) {
  return (
    <Frame name="LimitField" state={list(p.queries).length ? "asked" : "set"}>
      <span className="lbl">Your limits for this coalition</span>
      {list(p.limits).map((limit, i) => (
        <button
          className="f04-limit-row"
          type="button"
          aria-label={`Edit ${label(limit)}`}
          key={text(limit.id)}
          onClick={() => send("limit.change", { id: limit.id })}
        >
          <span>{label(limit)}</span>
          <span className="row">
            {limit.disclose === "shared" ? (
              <span className="num">{text(obj(p.shared_values)[text(limit.id)])}</span>
            ) : (
              <span
                role="img"
                className="redact"
                style={{ width: i === 0 ? 40 : 28 }}
                aria-label="Private value"
              />
            )}
            <span className={`badge ${limit.disclose === "shared" ? "b-estimate" : "b-vault"}`}>
              {limit.disclose === "shared" ? "shared" : "vault"}
            </span>
          </span>
        </button>
      ))}
      {!!list(p.queries).length && (
        <>
          <div className="hr" />
          <span className="lbl">Asked so far</span>
        </>
      )}
      {list(p.queries).map((q, i) => (
        <div
          className="row small"
          key={text(q.id) || String(i)}
          title={[text(q.asker), text(q.time)].filter(Boolean).join(" · ")}
        >
          <span className={`badge ${q.answer === "over" ? "f04-over" : "b-measured"}`}>
            {text(q.answer)}
          </span>
          {text(q.question)}
        </div>
      ))}
    </Frame>
  );
}

export function DocumentShare({ p, send }: View) {
  const [editing, set] = useState(false);
  const [masks, update] = useState(list(p.masks));
  const preview = obj(p.preview);
  const rows = list(preview.rows).length ? list(preview.rows) : list(p.masks);
  return (
    <Frame name="DocumentShare" state={editing ? "editing" : "masked"}>
      <div className="f04-document-preview">
        <b>{text(preview.title) || `Document · ${text(p.document)}`}</b>
        {rows.map((row, i) => {
          const field = text(row.field ?? row.region);
          const hidden = masks.some((m) => text(m.field ?? m.region) === field);
          const originallyHidden = list(p.masks).some((m) => text(m.field ?? m.region) === field);
          return (
            <div className="row sp" key={field || String(i)}>
              <span>{field}</span>
              {hidden || originallyHidden || row.value === undefined ? (
                <span
                  role="img"
                  className="redact"
                  style={{ width: i === 0 ? 80 : 52 }}
                  aria-label="Hidden"
                />
              ) : (
                <span className="mono">{text(row.value)}</span>
              )}
              {editing && hidden && (
                <button
                  type="button"
                  className="f04-text-button"
                  onClick={() => update(masks.filter((m) => text(m.field ?? m.region) !== field))}
                >
                  Remove mask
                </button>
              )}
            </div>
          );
        })}
      </div>
      <span className="small">
        Your agent hid {masks.length} fields. {text(p.purpose)}
      </span>
      <div className="row">
        <button type="button" className="btn btn-sm" onClick={() => set(!editing)}>
          Edit what's hidden
        </button>
        <button
          type="button"
          className="btn btn-sm btn-primary f04-push"
          onClick={() => send("evidence.share", { document: p.document, masks })}
        >
          Share as evidence
        </button>
      </div>
    </Frame>
  );
}
