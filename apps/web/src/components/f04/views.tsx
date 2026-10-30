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
export function ValidationSummary({ p, send }: View) {
  return (
    <Frame name="ValidationSummary" tone="ck-error" state="shown">
      <b>Check these fields</b>
      <div role="alert">
        {list(p.errors).map((e) => (
          <Action key={text(e.field)} onClick={() => send("field.focus", { id: e.field })}>
            {text(e.text)}
          </Action>
        ))}
      </div>
    </Frame>
  );
}
export function Wizard({ p, send, build }: View) {
  const steps = list(p.steps);
  const [current, set] = useState(
    Math.max(
      0,
      steps.findIndex((s) => s.id === p.current),
    ),
  );
  const step = steps[current];
  const [values, change] = useState<Data>(obj(p.draft));
  return (
    <Frame name="Wizard" state="step">
      <ol className="ck-wizard-steps">
        {steps.map((s, i) => (
          <li key={text(s.id)} aria-current={i === current ? "step" : undefined}>
            {i < current ? "✓" : i + 1} {label(s)}
          </li>
        ))}
      </ol>
      {step && (
        <div>
          <h3>{label(step)}</h3>
          {list(step.fields).map((f) => (
            <Field
              key={text(f.id)}
              field={f}
              value={values[text(f.id)]}
              change={(v) => change({ ...values, [text(f.id)]: v })}
            />
          ))}
          {Array.isArray(step.components) &&
            step.components.map((id) => <div key={text(id)}>{build?.(text(id))}</div>)}
        </div>
      )}
      <div className="ck-row">
        <Action
          disabled={current === 0}
          onClick={() => {
            set(current - 1);
            send("wizard.back", { current: step?.id, draft: values });
          }}
        >
          Back
        </Action>
        <Action
          primary
          disabled={!step}
          onClick={() => {
            const last = current === steps.length - 1;
            send(last ? "wizard.finish" : "wizard.next", { current: step?.id, draft: values });
            if (!last) set(current + 1);
          }}
        >
          {current === steps.length - 1 ? "Finish" : "Next"}
        </Action>
      </div>
      <small>Draft saved by the host</small>
    </Frame>
  );
}
export function NeedForm({ p, send }: View) {
  const [value, set] = useState(text(p.text));
  const [pending, status] = useState(false);
  return (
    <Frame name="NeedForm" state={pending ? "checking" : "draft"}>
      <h3>What do you need?</h3>
      <label className="ck-field">
        Need
        <textarea value={value} onChange={(e) => set(e.target.value)} />
      </label>
      <Rows value={p.constraints} />
      <span className="ck-tag">{text(p.audience) || "me"}</span>
      <Action
        primary
        disabled={!value.trim() || pending}
        onClick={() => {
          status(true);
          send("coalition.need", {
            text: value,
            quantity: p.quantity,
            constraints: p.constraints,
            audience: p.audience,
          });
        }}
      >
        Publish need
      </Action>
    </Frame>
  );
}
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
export function AvailabilityGrid({ p, send }: View) {
  const [selected, set] = useState<Set<string>>(
    new Set(
      list(p.slots)
        .filter((s) => s.available)
        .map((s) => text(s.id)),
    ),
  );
  return (
    <Frame
      name="AvailabilityGrid"
      state={p.source === "calendar" ? "imported" : selected.size ? "painted" : "empty"}
    >
      <div className="ck-row">
        <b>Your availability</b>
        <span className="ck-tag">Vault · answer-only</span>
      </div>
      <div className="ck-availability">
        {list(p.days).map((day) => (
          <section key={text(day.id)}>
            <b>{label(day)}</b>
            {list(p.slots)
              .filter((s) => s.day === day.id)
              .map((slot) => (
                <Action
                  key={text(slot.id)}
                  pressed={selected.has(text(slot.id))}
                  onClick={() => {
                    const next = new Set(selected);
                    const id = text(slot.id);
                    if (next.has(id)) next.delete(id);
                    else next.add(id);
                    set(next);
                    send("availability.paint", { day: day.id, slot: id, available: next.has(id) });
                  }}
                >
                  {label(slot)}
                </Action>
              ))}
          </section>
        ))}
      </div>
      <Action onClick={() => send("availability.import")}>Import calendar</Action>
      <small>Only shared availability answers leave your vault.</small>
    </Frame>
  );
}
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
export function AcceptanceForm({ p, send }: View) {
  const [read, set] = useState(false);
  return (
    <Frame name="AcceptanceForm" state={read ? "acknowledged" : "pending"}>
      <Subject value={p.subject} />
      <h3>The charter changed</h3>
      {list(p.diff).map((d, i) => (
        <div className="ck-diff" key={text(d.rule) || `${i}`}>
          <b>{text(d.rule)}</b>
          <del>− {text(d.before)}</del>
          <ins>+ {text(d.after)}</ins>
        </div>
      ))}
      <p>{text(p.consequence)}</p>
      <label>
        <input type="checkbox" checked={read} onChange={(e) => set(e.target.checked)} />I read what
        changed
      </label>
      <div className="ck-row">
        <Action
          primary
          disabled={!read || expired(p.decision_deadline)}
          onClick={() => send("decide", { charter: p.charter, subject: p.subject })}
        >
          Accept revision {number(obj(p.subject).revision)}
        </Action>
        <Action onClick={() => send("leave")}>Leave instead</Action>
      </div>
    </Frame>
  );
}
export function ConsentSeal({ p, send }: View) {
  const [holding, set] = useState(false);
  const [review, confirm] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  const cancel = () => {
    clearTimeout(timer.current);
    timer.current = undefined;
    set(false);
  };
  const start = () => {
    if (timer.current || expired(p.decision_deadline)) return;
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
      <span className="ck-meta">You're committing to</span>
      <h3>{text(p.summary)}</h3>
      <Subject value={p.subject} />
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
          <circle cx="56" cy="56" r="48" />
          <path d="M42 56l10 10 18-20" />
        </svg>
      </button>
      <b>{holding ? "Keep holding" : "Hold to review"}</b>
      <small>Release to cancel · Enter to open confirmation</small>
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
export function Receipt({ p, send }: View) {
  return (
    <Frame name="Receipt" state="recorded" tone="ck-success">
      <h3>Your answer is recorded</h3>
      <Subject value={p.subject} />
      <dl>
        <dt>Log entry</dt>
        <dd>#{number(p.seq)}</dd>
        <dt>Receipt</dt>
        <dd>{text(obj(p.receipt).signature ?? obj(p.receipt).algorithm)}</dd>
        <dt>Hash</dt>
        <dd>
          <code>{text(p.hash)}</code>
        </dd>
        <dt>Waiting for</dt>
        <dd>{list(p.remaining).map(label).join(", ") || "Nobody"}</dd>
      </dl>
      <div className="ck-row">
        <Action onClick={() => send("receipt.verify", { receipt: p.receipt, hash: p.hash })}>
          Verify myself
        </Action>
        <Action
          disabled={expired(p.decision_deadline)}
          onClick={() => send("decide.change", { subject: p.subject })}
        >
          Change answer
        </Action>
      </div>
    </Frame>
  );
}
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
export function FeedbackForm({ p, send }: View) {
  const [values, set] = useState<Data>({});
  return (
    <Frame name="FeedbackForm" state="draft">
      <h3>What did you learn?</h3>
      {list(p.questions).map((q, i) => (
        <Field
          key={text(q.id) || `${i}`}
          field={{
            ...q,
            id: q.id ?? `q${i}`,
            label: q.label ?? q.text,
            kind: q.kind === "scale" ? "number" : q.kind,
          }}
          value={values[text(q.id) || `q${i}`]}
          change={(v) => set({ ...values, [text(q.id) || `q${i}`]: v })}
        />
      ))}
      <small>Shared with {text(p.audience) || "nobody"}</small>
      <Action
        primary
        onClick={() => send("feedback.save", { values, audience: p.audience ?? "me" })}
      >
        Save
      </Action>
    </Frame>
  );
}
