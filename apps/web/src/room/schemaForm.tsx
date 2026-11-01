// SPDX-License-Identifier: Apache-2.0
// The input form a pack adds to My part for the viewer's own offers. Built only from the catalog
// form field (sheet 04); labels come from the schema, and a value is checked before it is sent.
import { type FormEvent, useId, useState } from "react";
import { Field } from "../components/f04/fields";
import { fieldsOf, type JsonSchema, toExt, type Values, validate } from "./extSchema";

export function SchemaForm({
  schema,
  title = "Details for your offer",
  submitLabel = "Add to my offer",
  onSubmit,
}: {
  /** The pack's extension schema for offers, handed in by the caller. */
  schema: JsonSchema;
  title?: string;
  submitLabel?: string;
  /** Receives the typed `ext` body. Private fields are never part of it. */
  onSubmit: (ext: Values) => void;
}) {
  const heading = useId();
  const fields = fieldsOf(schema);
  const [values, setValues] = useState<Values>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  if (fields.length === 0) return null;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const found = validate(fields, values);
    setErrors(found);
    if (Object.keys(found).length === 0) onSubmit(toExt(fields, values));
  };

  return (
    <form className="room-panel room-ext" aria-labelledby={heading} noValidate onSubmit={submit}>
      <h2 id={heading}>{title}</h2>
      {fields.map((f) => (
        <Field
          key={f.key}
          field={{
            label: f.title,
            kind: f.kind,
            required: f.required && !f.private,
            private: f.private ? "vault" : "no",
            options: f.options,
            help: errors[f.key] ?? f.description,
          }}
          value={values[f.key]}
          change={(v) => setValues((old) => ({ ...old, [f.key]: v }))}
        />
      ))}
      {Object.keys(errors).length > 0 && (
        <ul className="room-ext-errors" role="alert">
          {Object.values(errors).map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      )}
      <button type="submit" className="btn btn-primary">
        {submitLabel}
      </button>
    </form>
  );
}
