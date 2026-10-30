// SPDX-License-Identifier: Apache-2.0
import { Banner } from "../feedback";
import { Avatar, Badge, cx, Tag } from "../primitives";
import type { Participant } from "../work";

export type Subject = { kind: string; id: string; revision: number };
export type ConsentState = "open" | "answered" | "stale" | "expired";

const KIND_WORD: Record<string, string> = {
  plan: "Plan",
  tension_option: "Choice",
  commitment: "Commitment",
  charter: "Charter",
};

function ConsentDetails({
  yourPart,
  cost,
  consequenceOfNo,
}: {
  yourPart?: string;
  cost?: string;
  consequenceOfNo?: string;
}) {
  return (
    <div className="g3" style={{ gap: 8 }}>
      {yourPart && (
        <div className="col" style={{ gap: 2 }}>
          <span className="st">You do</span>
          <span className="small" style={{ color: "var(--ink)" }}>
            {yourPart}
          </span>
        </div>
      )}
      {cost && (
        <div className="col" style={{ gap: 2 }}>
          <span className="st">You pay</span>
          <span className="small" style={{ color: "var(--ink)" }}>
            {cost}
          </span>
        </div>
      )}
      {consequenceOfNo && (
        <div className="col" style={{ gap: 2 }}>
          <span className="st">If you say no</span>
          <span className="small" style={{ color: "var(--ink)" }}>
            {consequenceOfNo}
          </span>
        </div>
      )}
    </div>
  );
}

export function ConsentCard({
  subject,
  title,
  yourPart,
  cost,
  consequenceOfNo,
  deadline,
  state = "open",
  answer,
  currentRevision,
  yesLabel = "Accept",
  noLabel = "Not this one",
  busy,
  onDecide,
  onCompare,
  onReview,
}: {
  subject: Subject;
  title: string;
  yourPart?: string;
  cost?: string;
  consequenceOfNo?: string;
  deadline?: string;
  state?: ConsentState;
  answer?: boolean;
  currentRevision?: number;
  yesLabel?: string;
  noLabel?: string;
  busy?: boolean;
  onDecide?: (consent: boolean, subject: Subject) => void;
  onCompare?: () => void;
  onReview?: () => void;
}) {
  const open = state === "open";
  const word = KIND_WORD[subject.kind] ?? subject.kind;
  return (
    <section
      className={cx("card", open && "card-ask")}
      style={{ gap: 10, opacity: state === "expired" ? 0.7 : 1 }}
      aria-label={`${word} to decide: ${title}`}
      data-state={state}
    >
      <div className="row">
        <span className="eyebrow" style={{ color: "var(--warn-fg)" }}>
          Decide {"·"} {word} {"·"} revision {subject.revision}
        </span>
        {deadline && open && (
          <span className="h-right num small" style={{ color: "var(--warn-fg)" }}>
            {deadline}
          </span>
        )}
        {state === "answered" && (
          <span className="h-right">
            <Tag
              kind={answer ? "agreed" : "blocked"}
              label={answer ? "You said yes" : "You said no"}
            />
          </span>
        )}
        {state === "expired" && (
          <span className="h-right">
            <Badge kind="estimate" label="deadline passed" />
          </span>
        )}
      </div>
      <b style={{ fontSize: 15 }}>{title}</b>
      <ConsentDetails yourPart={yourPart} cost={cost} consequenceOfNo={consequenceOfNo} />
      {state === "stale" && (
        <Banner
          tone="ask"
          title={`This changed to revision ${currentRevision ?? subject.revision + 1} while you read.`}
          body="Your answer was not sent."
          action="Review"
          onAction={onReview}
        />
      )}
      {open && (
        <div className="row">
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            aria-busy={busy || undefined}
            onClick={() => onDecide?.(true, subject)}
          >
            {busy && <span className="spinner" aria-hidden="true" />}
            {yesLabel}
          </button>
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() => onDecide?.(false, subject)}
          >
            {noLabel}
          </button>
          <button type="button" className="btn btn-ghost" onClick={onCompare}>
            Compare
          </button>
          <span className="h-right small">signed with your owner key</span>
        </div>
      )}
    </section>
  );
}

/* ---------- VoteTally: counts while open, names after the decision closes ---------- */

export type Decider = Participant & { answered: boolean; answer?: boolean };
export type Outcome = "decided" | "refused" | "split" | "expired";

export function VoteTally({
  title,
  rule,
  deciders,
  closed,
  outcome,
}: {
  title: string;
  rule?: string;
  deciders: Decider[];
  closed?: boolean;
  outcome?: Outcome;
}) {
  const answered = deciders.filter((d) => d.answered).length;
  const waiting = deciders.length - answered;
  if (closed) {
    return (
      <section className="card" style={{ gap: 4 }} aria-label={`${title}, closed ${outcome ?? ""}`}>
        <div className="row">
          <b style={{ fontSize: 12.5 }}>
            Closed {"·"} {outcome}
          </b>
          {outcome === "split" && (
            <span className="h-right">
              <Badge kind="estimate" label="re-planning" />
            </span>
          )}
        </div>
        <div className="row small">
          {deciders.map((d) => {
            const none = !d.answered;
            const style = none
              ? { background: "var(--surface-3)", color: "var(--ink-2)" }
              : d.answer
                ? { background: "var(--ok-bg)", color: "var(--ok-fg)" }
                : { background: "var(--bad-bg)", color: "var(--bad-fg)" };
            return (
              <span key={d.label} className="badge" style={style}>
                {d.label} {none ? "no answer" : d.answer ? "yes" : "no"}
              </span>
            );
          })}
        </div>
      </section>
    );
  }
  return (
    <section className="card" aria-label={`${title}, ${answered} answered, ${waiting} waiting`}>
      <div className="row">
        <b style={{ fontSize: 13 }}>{title}</b>
        {rule && <span className="h-right small">rule: {rule}</span>}
      </div>
      <div className="row" style={{ gap: 6 }}>
        {deciders.map((d) => (
          <span key={d.label} style={{ display: "inline-flex" }}>
            <span
              style={{
                borderRadius: 999,
                boxShadow: `0 0 0 2px var(--surface), 0 0 0 4px ${d.answered ? "var(--ok-fg)" : "var(--line-strong)"}`,
                display: "inline-flex",
              }}
            >
              <Avatar seat={d.seat} label={d.label} size="lg" />
            </span>
            <span className="sr-only">{d.answered ? "answered" : "waiting"}</span>
          </span>
        ))}
      </div>
      <div className="row small">
        <span className="num">
          <b>{answered}</b> answered {"·"} <b>{waiting}</b> waiting
        </span>
      </div>
      <div className="bar" aria-hidden="true">
        <span
          style={{
            width: `${deciders.length ? (answered / deciders.length) * 100 : 0}%`,
            background: "var(--ok-fg)",
          }}
        />
      </div>
      <span className="st">how each decider answered is shown when the decision closes</span>
    </section>
  );
}
