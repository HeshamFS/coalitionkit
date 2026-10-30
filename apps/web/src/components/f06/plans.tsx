// SPDX-License-Identifier: Apache-2.0
import { useId, useState } from "react";
import { Avatar, AvatarStack, Badge, type BadgeKind, cx, Tag } from "../primitives";
import { Bound, type BoundNumber, type Participant } from "./work";

/* ---------- PlanCompare ---------- */

export type Objective = {
  name: string;
  value: BoundNumber;
  unit?: string;
  /** Which way is better, so a short bar is never read as worse by accident. */
  better?: "lower" | "higher";
};
export type Plan = {
  id: string;
  label: string;
  /** Short name for the accept button, e.g. "A". */
  short?: string;
  objectives: Objective[];
  tag?: { label: string; kind: BadgeKind };
  people?: Participant[];
  note?: string;
  highlight?: boolean;
  canDecide?: boolean;
};
export type RejectedPlan = { plan: Plan; reason: string };
export type PlanSetState = "proposed" | "decided" | "superseded";

function barWidth(plan: Plan, index: number, all: Plan[]): number {
  const mine = plan.objectives[index]?.value.value ?? 0;
  const max = Math.max(...all.map((p) => p.objectives[index]?.value.value ?? 0), 1);
  return Math.max(4, Math.round((mine / max) * 100));
}

function PlanBars({ plan, all, muted }: { plan: Plan; all: Plan[]; muted?: boolean }) {
  return (
    <div className="col" style={{ gap: 5 }}>
      {plan.objectives.map((o, i) => (
        <div className="row small" key={o.name}>
          <span style={{ width: 88 }}>{o.name}</span>
          <div className="bar grow" aria-hidden="true">
            <span
              style={{
                width: `${barWidth(plan, i, all)}%`,
                background: muted ? "var(--line-strong)" : undefined,
              }}
            />
          </div>
          <span className="num" style={{ width: 52, textAlign: "right" }}>
            <Bound n={o.value} unit={o.unit} />
          </span>
        </div>
      ))}
    </div>
  );
}

export function PlanCompare({
  plans,
  rejected = [],
  state = "proposed",
  deadline,
  decidedId,
  onDecide,
  onDetails,
}: {
  plans: Plan[];
  rejected?: RejectedPlan[];
  state?: PlanSetState;
  deadline?: string;
  decidedId?: string;
  onDecide?: (id: string) => void;
  onDetails?: (id: string) => void;
}) {
  const everyone = [...plans, ...rejected.map((r) => r.plan)];
  const locked = state !== "proposed";
  return (
    <section
      className="col"
      aria-label="Plans side by side"
      data-state={state}
      style={{ opacity: state === "superseded" ? 0.7 : 1 }}
    >
      <div className="row sp">
        <span className="row">
          <Badge kind="model" label="Gardener" />
          <Badge kind="signed" label="Steward passed" />
        </span>
        <span className="row small">
          {state === "decided" && <Tag kind="agreed" />}
          {state === "superseded" && <Badge kind="estimate" label="superseded" />}
          {deadline && state === "proposed" && <span className="num">decide by {deadline}</span>}
        </span>
      </div>
      <div className="g3" style={{ gap: 10 }}>
        {plans.map((plan) => (
          <article
            key={plan.id}
            className={cx("card", plan.highlight && "card-live")}
            style={{ gap: 8 }}
            aria-label={plan.label}
          >
            <div className="head">
              <b style={{ fontSize: 13.5 }}>{plan.label}</b>
              {plan.tag && (
                <span className="h-right">
                  <Badge kind={plan.tag.kind} label={plan.tag.label} />
                </span>
              )}
            </div>
            <PlanBars plan={plan} all={everyone} />
            <div className="row">
              {plan.people && <AvatarStack people={plan.people} size="xs" />}
              {plan.note && <span className="small">{plan.note}</span>}
            </div>
            <div className="row">
              <button
                type="button"
                className={cx("btn btn-sm", plan.highlight && "btn-primary")}
                disabled={locked || plan.canDecide === false}
                onClick={() => onDecide?.(plan.id)}
              >
                {decidedId === plan.id ? "Accepted" : `Accept ${plan.short ?? plan.label}`}
              </button>
              <button type="button" className="btn btn-sm" onClick={() => onDetails?.(plan.id)}>
                Details
              </button>
            </div>
          </article>
        ))}
        {rejected.map(({ plan, reason }) => (
          <article
            key={plan.id}
            className="card card-dashed"
            style={{ gap: 8 }}
            aria-label={`${plan.label}, not proposed`}
          >
            <div className="head">
              <b style={{ fontSize: 13.5, color: "var(--ink-2)" }}>{plan.label}</b>
              <span
                className="h-right badge"
                style={{ background: "var(--bad-bg)", color: "var(--bad-fg)" }}
              >
                not proposed
              </span>
            </div>
            <PlanBars plan={plan} all={everyone} muted />
            <span className="small">{reason}</span>
            <span className="st">shown so you see why it was not proposed</span>
          </article>
        ))}
      </div>
    </section>
  );
}

/* ---------- TensionCard ---------- */

export type TensionOption = { id: string; label: string; tradeoffs: string[] };
export type TensionState = "open" | "decided" | "split" | "expired";

export function TensionCard({
  title,
  options,
  deciders = [],
  answered = 0,
  deadline,
  state = "open",
  chosenId,
  onChoose,
  onAsk,
}: {
  title: string;
  options: TensionOption[];
  /** Left out when the host state does not say who decides. */
  deciders?: (Participant & { answered?: boolean })[];
  answered?: number;
  deadline?: string;
  state?: TensionState;
  chosenId?: string;
  onChoose?: (optionId: string) => void;
  onAsk?: () => void;
}) {
  const group = useId();
  const [picked, setPicked] = useState(chosenId ?? options[0]?.id ?? "");
  const open = state === "open";
  const current = options.find((o) => o.id === picked);
  return (
    <section
      className={cx("card", open && "card-ask")}
      style={{ gap: 8 }}
      aria-label={title}
      data-state={state}
    >
      <div className="row sp">
        <b style={{ fontSize: 14 }}>{title}</b>
        {open && <Tag kind="needs" />}
        {state === "decided" && <Tag kind="agreed" />}
        {state === "split" && <Badge kind="estimate" label="split, re-planning" />}
        {state === "expired" && <Badge kind="estimate" label="expired" />}
      </div>
      <div role="radiogroup" aria-label="Options" className="g2" style={{ gap: 8 }}>
        {options.map((o) => {
          const on = picked === o.id;
          return (
            <label
              key={o.id}
              className="card"
              style={{
                gap: 4,
                cursor: open ? "pointer" : "default",
                outline: on && !open ? "1px solid var(--blue)" : undefined,
              }}
            >
              <input
                className="sr-only"
                type="radio"
                name={group}
                value={o.id}
                checked={on}
                disabled={!open}
                onChange={() => setPicked(o.id)}
              />
              <span className="row">
                <span className={cx("radio", on && "radio-on")} aria-hidden="true" />
                <b style={{ fontSize: 12.5 }}>{o.label}</b>
              </span>
              {o.tradeoffs.map((t) => (
                <span className="small" key={t}>
                  {t}
                </span>
              ))}
            </label>
          );
        })}
      </div>
      <div className="row">
        {deciders.length > 0 && <span className="small">Deciders</span>}
        <div className="stack">
          {deciders.map((d) => (
            <Avatar key={d.label} seat={d.seat} label={d.label} size="xs" ring={d.answered} />
          ))}
        </div>
        {deciders.length > 0 && (
          <span className="small">
            {answered} of {deciders.length} answered
          </span>
        )}
        {deadline && open && (
          <span className="h-right num small" style={{ color: "var(--warn-fg)" }}>
            decide by {deadline}
          </span>
        )}
      </div>
      {open && (
        <div className="row">
          <button
            type="button"
            className="btn btn-sm btn-primary"
            disabled={!current}
            onClick={() => current && onChoose?.(current.id)}
          >
            Choose {current?.label ?? ""}
          </button>
          {onAsk && (
            <button type="button" className="btn btn-sm" onClick={onAsk}>
              Ask why
            </button>
          )}
        </div>
      )}
    </section>
  );
}
