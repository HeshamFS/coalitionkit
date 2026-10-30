// SPDX-License-Identifier: Apache-2.0
import { Fragment, useId, useState } from "react";
import { type Data, Frame, label, list, obj, text, type View } from "../f02/ui";
import { Field } from "./fields";
import "./wizard.css";

function SuggestionText({ value }: { value: Data }) {
  const phrase = text(value.emphasis);
  const content = text(value.text);
  const index = phrase ? content.indexOf(phrase) : -1;
  return index < 0 ? (
    content
  ) : (
    <>
      {content.slice(0, index)}
      <b>{phrase}</b>
      {content.slice(index + phrase.length)}
    </>
  );
}

function WizardFields({
  fields,
  values,
  change,
}: {
  fields: Data[];
  values: Data;
  change: (id: string, value: unknown) => void;
}) {
  const group = useId();
  return (
    <>
      {fields.map((field) =>
        field.kind === "choice" && list(field.options).some((option) => option.description) ? (
          <fieldset key={text(field.id)} className="f04-wizard-options" aria-label={label(field)}>
            {list(field.options).map((option) => (
              <label
                key={text(option.id)}
                className={`f04-wizard-option${values[text(field.id)] === option.id ? " f04-wizard-selected" : ""}`}
              >
                <input
                  type="radio"
                  name={`${group}-${text(field.id)}`}
                  checked={values[text(field.id)] === option.id}
                  onChange={() => change(text(field.id), option.id)}
                />
                <span>
                  <b>{label(option)}</b>
                  <span>{text(option.description)}</span>
                </span>
              </label>
            ))}
          </fieldset>
        ) : (
          <Field
            key={text(field.id)}
            field={field}
            value={values[text(field.id)]}
            change={(value) => change(text(field.id), value)}
          />
        ),
      )}
    </>
  );
}

export function Wizard({ p, send, build }: View) {
  const steps = list(p.steps);
  const [current, set] = useState(
    Math.max(
      0,
      steps.findIndex((step) => step.id === p.current),
    ),
  );
  const [values, change] = useState<Data>(obj(p.draft));
  const step = steps[current];
  const suggestion = obj(step?.suggestion);
  const summary = list(step?.summary);
  return (
    <Frame name="Wizard" state="step">
      <ol className="f04-wizard-rail">
        {steps.map((item, index) => (
          <Fragment key={text(item.id)}>
            {index > 0 && (
              <li
                className={`f04-wizard-line${index <= current ? " f04-wizard-line-done" : ""}`}
                aria-hidden="true"
              />
            )}
            <li
              className={`f04-wizard-step${index < current ? " f04-wizard-done" : ""}`}
              aria-current={index === current ? "step" : undefined}
            >
              <i>{index < current ? "✓" : index + 1}</i>
              {label(item)}
            </li>
          </Fragment>
        ))}
      </ol>
      {step && (
        <div className="f04-wizard-grid">
          <div className="f04-wizard-column">
            <b className="f04-wizard-title">{text(step.prompt) || label(step)}</b>
            <WizardFields
              fields={list(step.fields)}
              values={values}
              change={(id, value) => change({ ...values, [id]: value })}
            />
            {Array.isArray(step.components) &&
              step.components.map((id) => <div key={text(id)}>{build?.(text(id))}</div>)}
          </div>
          <div className="f04-wizard-column">
            {!!suggestion.text && (
              <aside className="f04-wizard-aside">
                <span className="f04-wizard-eyebrow">Your agent suggests</span>
                <span className="f04-wizard-suggestion">
                  <SuggestionText value={suggestion} />
                </span>
                <span className="badge b-model">Model output</span>
              </aside>
            )}
            {!!summary.length && (
              <aside className="f04-wizard-aside f04-wizard-summary">
                <span className="f04-wizard-eyebrow">Charter so far</span>
                {summary.map((item) => (
                  <span
                    key={label(item)}
                    className={item.current === true ? "f04-wizard-current" : undefined}
                  >
                    {label(item)}
                  </span>
                ))}
              </aside>
            )}
          </div>
        </div>
      )}
      <div className="f04-wizard-footer">
        <button
          className="ck-action"
          type="button"
          disabled={current === 0}
          onClick={() => {
            set(current - 1);
            send("wizard.back", { current: step?.id, draft: values });
          }}
        >
          Back
        </button>
        <span>Saved as draft</span>
        <button
          className="ck-action ck-primary"
          type="button"
          aria-label={current === steps.length - 1 ? "Finish" : "Next"}
          disabled={!step}
          onClick={() => {
            const last = current === steps.length - 1;
            send(last ? "wizard.finish" : "wizard.next", { current: step?.id, draft: values });
            if (!last) set(current + 1);
          }}
        >
          {current === steps.length - 1
            ? "Finish"
            : `Next: ${label(steps[current + 1] ?? {}).toLowerCase()}`}
        </button>
      </div>
    </Frame>
  );
}
