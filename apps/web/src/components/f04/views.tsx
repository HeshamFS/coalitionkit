// SPDX-License-Identifier: Apache-2.0
import { useEffect, useRef, useState } from "react";
import {
  Action,
  type Data,
  expired,
  Frame,
  label,
  list,
  number,
  obj,
  Rows,
  Subject,
  text,
  type View,
} from "../f02/ui";
import { Field } from "./fields";
import "../../styles/f02.css";
import "../../styles/f04.css";

export function Form({ p, send }: View) {
  const [values, set] = useState<Data>({});
  const [state, status] = useState("empty");
  return (
    <Frame name="Form" state={state}>
      <form
        onInvalid={() => status("invalid")}
        onSubmit={(e) => {
          e.preventDefault();
          status("submitting");
          send("form.submit", { values });
        }}
      >
        <h3>{text(p.title)}</h3>
        {list(p.fields).map((f) => (
          <Field
            key={text(f.id)}
            field={f}
            value={values[text(f.id)]}
            change={(value) => {
              status("filling");
              set({ ...values, [text(f.id)]: value });
            }}
          />
        ))}
        <button type="submit" className="ck-action ck-primary" disabled={state === "submitting"}>
          {state === "submitting" ? "Submitting…" : "Submit"}
        </button>
      </form>
    </Frame>
  );
}
export { NeedForm } from "./need";
export { ValidationSummary } from "./validation";
export { Wizard } from "./wizard";
export function OfferForm({ p, send }: View) {
  const [what, set] = useState(text(p.what));
  return (
    <Frame name="OfferForm" state="draft">
      <h3>Make an offer</h3>
      <span className="ck-tag">For {text(p.target)}</span>
      <label className="ck-field">
        What can you offer?
        <textarea value={what} onChange={(e) => set(e.target.value)} />
      </label>
      <Rows value={p.conditions} />
      <small>
        {text(obj(p.cost).kind)} {number(obj(p.cost).amount)} · expires {text(p.expires)}
      </small>
      <Action
        primary
        disabled={!what.trim() || expired(p.expires)}
        onClick={() =>
          send("coalition.offer", {
            what,
            target: p.target,
            conditions: p.conditions,
            cost: p.cost,
            expires: p.expires,
          })
        }
      >
        Publish offer
      </Action>
    </Frame>
  );
}
export { AvailabilityGrid } from "./availability";

export function LimitField({ p, send }: View) {
  return (
    <Frame name="LimitField" state={list(p.queries).length ? "asked" : "set"}>
      <b>Private limits</b>
      {list(p.limits).map((limit) => (
        <div className="ck-row" key={text(limit.id)}>
          <span>{label(limit)}</span>
          <span className="ck-tag">{text(limit.disclose)}</span>
          <Action onClick={() => send("limit.change", { id: limit.id })}>Edit in vault</Action>
        </div>
      ))}
      {list(p.queries).map((q, i) => (
        <div className="ck-query" key={text(q.id) || `${i}`}>
          <span>{text(q.question)}</span>
          <b>{text(q.answer)}</b>
          <small>
            {text(q.asker)} · {text(q.time)}
          </small>
        </div>
      ))}
    </Frame>
  );
}
export function DocumentShare({ p, send }: View) {
  const [editing, set] = useState(false);
  const [masks, update] = useState(list(p.masks));
  return (
    <Frame name="DocumentShare" state={editing ? "editing" : "masked"}>
      <div className="ck-document">
        <b>Document · {text(p.document)}</b>
        {masks.map((mask, i) => (
          <div className="ck-row" key={text(mask.field ?? mask.region) || `${i}`}>
            <span>{text(mask.field ?? mask.region)}</span>
            <span className="ck-redaction" role="img" aria-label="Hidden" />
            {editing && (
              <Action onClick={() => update(masks.filter((m) => m !== mask))}>Remove mask</Action>
            )}
          </div>
        ))}
      </div>
      <p>{text(p.purpose)}</p>
      <small>{masks.length} fields hidden. Masks are applied by the host.</small>
      <div className="ck-row">
        <Action onClick={() => set(!editing)}>Edit what's hidden</Action>
        <Action primary onClick={() => send("evidence.share", { document: p.document, masks })}>
          Share as evidence
        </Action>
      </div>
    </Frame>
  );
}
export { AcceptanceForm } from "./acceptance";
export function ConsentSeal({ p, send }: View) {
  const [holding, set] = useState(false);
  const [review, confirm] = useState(false);
  const [elapsed, tick] = useState(0);
  const [summary, ...description] = text(p.summary).split("\n");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    if (!holding) return;
    const started = Date.now();
    const interval = setInterval(() => tick(Date.now() - started), 100);
    return () => clearInterval(interval);
  }, [holding]);
  useEffect(() => () => clearTimeout(timer.current), []);
  const cancel = () => {
    clearTimeout(timer.current);
    timer.current = undefined;
    set(false);
  };
  const start = () => {
    if (timer.current || expired(p.decision_deadline)) return;
    tick(0);
    set(true);
    timer.current = setTimeout(
      () => {
        set(false);
        confirm(true);
        timer.current = undefined;
      },
      Math.max(0, number(p.holdMs, 1200)),
    );
  };
  return (
    <Frame name="ConsentSeal" state={holding ? "holding" : "idle"}>
      <span className="f04-seal-eyebrow">You're committing to</span>
      <b className="f04-seal-title">{summary}</b>
      {!!description.length && (
        <span className="f04-seal-description">{description.join(" ")}</span>
      )}
      <span className="f04-seal-subject">
        <Subject value={p.subject} />
      </span>
      <button
        type="button"
        className="ck-seal"
        aria-label="Hold to review consent"
        disabled={expired(p.decision_deadline)}
        onPointerDown={start}
        onPointerUp={cancel}
        onPointerLeave={cancel}
        onPointerCancel={cancel}
        onKeyDown={(e) => {
          if (e.key === " " && !e.repeat) {
            e.preventDefault();
            start();
          }
          if (e.key === "Enter") confirm(true);
        }}
        onKeyUp={(e) => {
          if (e.key === " ") cancel();
        }}
        onBlur={cancel}
      >
        <svg aria-hidden="true" viewBox="0 0 112 112">
          <circle className="f04-seal-track" cx="56" cy="56" r="48" />
          {holding && (
            <circle
              className="f04-seal-progress"
              cx="56"
              cy="56"
              r="48"
              transform="rotate(-90 56 56)"
            />
          )}
          <path d="M42 56l10 10 18-20" />
        </svg>
      </button>
      <b className="f04-seal-label">
        {holding ? `Keep holding · ${(elapsed / 1000).toFixed(1)} s` : "Hold to review"}
      </b>
      <span className="f04-seal-footnote">signs with your owner key · release to cancel</span>
      {review && (
        <fieldset aria-label="Confirm consent">
          <p>Review this revision with your owner key.</p>
          <Action
            primary
            disabled={expired(p.decision_deadline)}
            onClick={() => {
              if (!expired(p.decision_deadline)) send("decide", { subject: p.subject });
              confirm(false);
            }}
          >
            Confirm
          </Action>
          <Action onClick={() => confirm(false)}>Cancel</Action>
        </fieldset>
      )}
    </Frame>
  );
}
export function OwnerSign({ p, send }: View) {
  return (
    <Frame name="OwnerSign" state={p.kid ? "ready" : "failed closed"}>
      <h3>Sign as yourself</h3>
      <p>This decision is binding. Your device signs it; the agent can't.</p>
      <Subject value={p.subject} />
      <dl>
        <dt>Answer</dt>
        <dd>{text(p.answer)}</dd>
        <dt>Key</dt>
        <dd>{text(p.kid) || "No key available"}</dd>
        <dt>Device</dt>
        <dd>{text(p.method)}</dd>
      </dl>
      <Action
        primary
        disabled={!p.kid || expired(p.decision_deadline)}
        onClick={() =>
          send("sign.confirm", {
            subject: p.subject,
            answer: p.answer,
            kid: p.kid,
            method: p.method,
          })
        }
      >
        Confirm with {text(p.method) || "owner key"}
      </Action>
      <small>No key, no decision.</small>
    </Frame>
  );
}
export { Receipt } from "./receipt";
export function ReviewStep({ p, send }: View) {
  const passed = obj(p.precheck).passed === true;
  return (
    <Frame name="ReviewStep" state={passed ? "ready" : "blocked"}>
      <div className="ck-review">
        <Rows value={p.sections} />
        <div>
          <p>{text(p.notice)}</p>
          <span className="ck-tag">Steward pre-check · {passed ? "Passed" : "Blocked"}</span>
          <Action primary disabled={!passed} onClick={() => send("wizard.finish")}>
            Publish charter
          </Action>
        </div>
      </div>
    </Frame>
  );
}
export { FeedbackForm } from "./feedback";
