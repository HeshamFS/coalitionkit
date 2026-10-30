// SPDX-License-Identifier: Apache-2.0
import { useId } from "react";
import { type Data, label, list, text } from "../f02/ui";

export function Field({
  field,
  value,
  change,
}: {
  field: Data;
  value: unknown;
  change: (value: unknown) => void;
}) {
  const id = useId();
  const kind = text(field.kind);
  const help = `${id}-help`;
  if (field.private && field.private !== "no") {
    return (
      <div className="ck-field">
        <label htmlFor={id}>
          {label(field)} <span className="ck-tag">{text(field.private)}</span>
        </label>
        <input id={id} disabled placeholder="Set in your local vault" aria-describedby={help} />
        <small id={help}>Private values require the local vault connection.</small>
      </div>
    );
  }
  return (
    <div className="ck-field">
      <label htmlFor={id}>
        {label(field)}
        {field.required ? " *" : ""}
        {field.private && field.private !== "no" ? (
          <span className="ck-tag">{text(field.private)}</span>
        ) : null}
      </label>
      {kind === "choice" || kind === "multi" ? (
        <select
          id={id}
          multiple={kind === "multi"}
          required={!!field.required}
          value={kind === "multi" ? (Array.isArray(value) ? value.map(text) : []) : text(value)}
          aria-describedby={help}
          onChange={(e) =>
            change(
              kind === "multi"
                ? Array.from(e.target.selectedOptions, (o) => o.value)
                : e.target.value,
            )
          }
        >
          <option value="">Choose…</option>
          {list(field.options).map((o) => (
            <option key={text(o.id ?? o.value)} value={text(o.value ?? o.id)}>
              {label(o)}
            </option>
          ))}
        </select>
      ) : kind === "bool" ? (
        <input
          id={id}
          type="checkbox"
          checked={value === true}
          required={!!field.required}
          onChange={(e) => change(e.target.checked)}
          aria-describedby={help}
        />
      ) : (
        <input
          id={id}
          type={
            kind === "datetime"
              ? "datetime-local"
              : kind === "number" || kind === "money"
                ? "number"
                : "text"
          }
          required={!!field.required}
          value={text(value)}
          onChange={(e) => change(e.target.value)}
          aria-describedby={help}
        />
      )}
      <small id={help}>{text(field.help)}</small>
    </div>
  );
}
