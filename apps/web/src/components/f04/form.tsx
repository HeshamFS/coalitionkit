// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { type Data, Frame, label, list, number, text, type View } from "../f02/ui";
import { Field } from "./fields";
import "./form.css";

function Schema({ p }: { p: Data }) {
  const quoted = (value: unknown) => (
    <span className="f04-code-string">{JSON.stringify(value)}</span>
  );
  return (
    <div className="f04-schema">
      <div className="f04-code-comment">{"// schema the agent sends (A2UI Form)"}</div>
      <div>
        {"{ "}
        <span>"component"</span>: {quoted("Form")},
      </div>
      <div>
        &nbsp;&nbsp;<span>"title"</span>: {quoted(p.title)},
      </div>
      <div>
        &nbsp;&nbsp;<span>"fields"</span>: [
      </div>
      {list(p.fields).map((field, i, fields) => (
        <div key={text(field.id)}>
          &nbsp;&nbsp;&nbsp;{"{ "}
          <span>"id"</span>: {quoted(field.id)}, <span>"kind"</span>: {quoted(field.kind)}
          {field.private ? (
            <>
              ,<br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span>"private"</span>: {quoted(field.private)}
            </>
          ) : null}
          {field.options ? (
            <>
              ,<br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span>"options"</span>: [
              {list(field.options).map((o, j) => (
                <span key={text(o.id)}>
                  {j ? "," : ""}
                  {quoted(o.id)}
                </span>
              ))}
              ]
            </>
          ) : null}
          {" }"}
          {i < fields.length - 1 ? "," : " ],"}
        </div>
      ))}
      <div>
        &nbsp;&nbsp;<span>"submit_event"</span>: {quoted(p.submit_event)}
        {" }"}
      </div>
    </div>
  );
}

function FormField({
  field,
  value,
  change,
}: {
  field: Data;
  value: unknown;
  change: (v: unknown) => void;
}) {
  if (field.private && field.private !== "no" && !field.display_value) {
    return <Field field={field} value={undefined} change={() => {}} />;
  }
  if (field.private && field.private !== "no")
    return (
      <div className="field">
        <span className="lbl row">
          {label(field)} <span className="badge b-vault">private</span>
        </span>
        <div className="input">
          <span className="mut3">€</span>
          <span className="num">{field.display_value ? number(field.display_value) : "•••"}</span>
          <span className="unit">{text(field.unit)}</span>
        </div>
        <span className="help">{text(field.help) || "Edit in your local vault"}</span>
      </div>
    );
  if (field.kind === "choice")
    return (
      <div className="field">
        <span className="lbl">{label(field)}</span>
        <fieldset className="seg" aria-label={label(field)}>
          {list(field.options).map((o) => (
            <button
              key={text(o.id)}
              type="button"
              aria-pressed={value === o.id}
              onClick={() => change(o.id)}
            >
              {label(o)}
            </button>
          ))}
        </fieldset>
      </div>
    );
  if (field.kind === "bool")
    return (
      <label className="row sp">
        <span className="lbl">{label(field)}</span>
        <input
          className="f04-switch"
          type="checkbox"
          checked={value === true}
          onChange={(e) => change(e.target.checked)}
        />
      </label>
    );
  if (field.display_label)
    return (
      <label className="field">
        <span>{label(field)}</span>
        <span className="input">
          <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="5" width="18" height="16" rx="2" />
            <path d="M3 10h18" />
          </svg>
          <input
            aria-label={label(field)}
            value={text(value)}
            onChange={(e) => change(e.target.value)}
          />
        </span>
      </label>
    );
  return <Field field={field} value={value} change={change} />;
}

function VoiceForm({ p }: { p: Data }) {
  return (
    <div className="card f04-voice-form">
      {list(p.conversation).map((turn, i) => (
        <div
          className={`row small ${turn.role === "user" ? "f04-voice-answer" : ""}`}
          key={String(i)}
        >
          {turn.role !== "user" && <span className="av av-xs sh">Y</span>}
          <span className={turn.role === "user" ? "f04-voice-bubble" : ""}>
            {turn.private ? "Private answer saved in your vault" : text(turn.text)}
          </span>
        </div>
      ))}
      <div className="hr" />
      <dl>
        {list(p.fields).map((field) => (
          <div className="f04-readback" key={text(field.id)}>
            <dt>{text(field.id)}</dt>
            <dd
              className="mono"
              data-pending={(!field.private || field.private === "no") && !field.readback}
            >
              {field.private && field.private !== "no"
                ? "vault ✓"
                : text(field.readback) || "asking…"}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function Form({ p, send }: View) {
  const fields = list(p.fields);
  const [values, set] = useState<Data>(() =>
    Object.fromEntries(
      fields
        .filter((f) => !f.private || f.private === "no")
        .map((f) => [text(f.id), f.initial ?? f.display_label ?? ""]),
    ),
  );
  const [state, status] = useState("empty");
  return (
    <Frame name="Form" state={state}>
      {p.presentation === "voice" ? (
        <VoiceForm p={p} />
      ) : (
        <div className={p.show_schema ? "f04-form-layout" : ""}>
          {!!p.show_schema && <Schema p={p} />}
          <form
            className="card f04-generated-form"
            onInvalid={() => status("invalid")}
            onSubmit={(e) => {
              e.preventDefault();
              status("submitting");
              const publicValues = Object.fromEntries(
                fields
                  .filter((f) => !f.private || f.private === "no")
                  .map((f) => [text(f.id), values[text(f.id)]]),
              );
              send("form.submit", { values: publicValues });
            }}
          >
            <b>{text(p.title)}</b>
            {!!p.description && <span className="small">{text(p.description)}</span>}
            {fields.map((f) => (
              <FormField
                key={text(f.id)}
                field={f}
                value={values[text(f.id)]}
                change={(value) => {
                  status("filling");
                  set({ ...values, [text(f.id)]: value });
                }}
              />
            ))}
            <div className="row">
              {!!p.scope && <span className="scope">{text(p.scope)}</span>}
              <div className="row f04-form-actions">
                {!!p.submit_label && (
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost"
                    onClick={() => send("form.later")}
                  >
                    Later
                  </button>
                )}
                <button
                  type="submit"
                  className="btn btn-sm btn-primary"
                  disabled={state === "submitting"}
                >
                  {state === "submitting" ? "Submitting…" : text(p.submit_label) || "Submit"}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}
    </Frame>
  );
}
