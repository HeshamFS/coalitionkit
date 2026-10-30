// SPDX-License-Identifier: Apache-2.0
import { useId, useState } from "react";
import { type Data, Frame, label, list, text, type View } from "../f02/ui";
import "./feedback.css";

export function FeedbackForm({ p, send }: View) {
  const prefix = useId();
  const [values, set] = useState<Data>({});
  const questions = list(p.questions);
  const change = (id: string, value: unknown) => set((previous) => ({ ...previous, [id]: value }));
  const answer = (question: Data, index: number) => {
    const id = text(question.id) || `q${index}`;
    const domId = `${prefix}-${id}`;
    const value = values[id];
    return (
      <div className="f04-feedback-question" key={id}>
        <label id={`${domId}-label`} htmlFor={question.kind === "text" ? domId : undefined}>
          {label(question)}
          {question.kind === "text" && (p.audience === "me" || !p.audience) && (
            <span className="badge b-vault">kept for your agent</span>
          )}
        </label>
        {question.kind === "text" ? (
          <textarea
            id={domId}
            value={text(value)}
            onChange={(event) => change(id, event.target.value)}
          />
        ) : (
          <fieldset
            aria-labelledby={`${domId}-label`}
            className={question.kind === "scale" ? "f04-feedback-scale" : "f04-feedback-choice"}
          >
            {(question.kind === "scale"
              ? [1, 2, 3, 4, 5].map((n) => ({ id: String(n), label: String(n) }))
              : list(question.options)
            ).map((option) => (
              <button
                key={text(option.id)}
                type="button"
                aria-pressed={value === option.id}
                onClick={() => change(id, option.id)}
              >
                {label(option)}
              </button>
            ))}
          </fieldset>
        )}
      </div>
    );
  };
  return (
    <Frame name="FeedbackForm" state="draft">
      <div className="f04-feedback-grid">
        <div className="f04-feedback-column">
          {questions.map((q, i) => (q.kind !== "text" ? answer(q, i) : null))}
        </div>
        <div className="f04-feedback-column">
          {questions.map((q, i) => (q.kind === "text" ? answer(q, i) : null))}
          <div className="f04-feedback-footer">
            <span>
              {p.audience === "me" || !p.audience
                ? "Shared with nobody unless you choose"
                : `Shared with ${text(p.audience)}`}
            </span>
            <button
              className="ck-action ck-primary"
              type="button"
              onClick={() => send("feedback.save", { values, audience: p.audience ?? "me" })}
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </Frame>
  );
}
