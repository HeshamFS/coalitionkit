// SPDX-License-Identifier: Apache-2.0
import { createContext, type ReactNode, useContext, useId, useState } from "react";
import { Avatar, AvatarStack, Badge, type BadgeKind, cx, Tag } from "../primitives";
import { ObjectiveBars } from "./charts";
import type { BoundNumber, Participant } from "./work";

/* ---------- PlanCompare ---------- */

export type Objective = {
  name: string;
  value: BoundNumber;
  scale?: BoundNumber;
  display?: string;
  tone?: string;
  unit?: string;
  /** Which way is better, so a short bar is never read as worse by accident. */
  better?: "lower" | "higher";
};
export type Plan = {
  id: string;
  label: string;
  description?: string;
  /** Short name for the accept button, e.g. "A". */
  short?: string;
  objectives: Objective[];
  tag?: { label: string; kind: BadgeKind };
  people?: Participant[];
  note?: string;
  /** What this plan is best at compared with the others, in words. */
  strength?: string;
  highlight?: boolean;
  canDecide?: boolean;
};
/** Hosts can route the shared objective view through their catalog renderer. */
export const ObjectiveBarsRenderer = createContext<
  ((plan: Plan, muted?: boolean) => ReactNode) | null
>(null);
export type RejectedPlan = { plan: Plan; reason: string };
export type PlanSetState = "proposed" | "decided" | "superseded";

function PlanBars({ plan, muted }: { plan: Plan; muted?: boolean }) {
  return (
    <ObjectiveBars
      p={{ objectives: plan.objectives.map((o) => ({ ...o, muted })) }}
      send={() => {}}
    />
  );
}

export function PlanCompare({
  plans,
  rejected = [],
  state = "proposed",
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
  const renderObjectives = useContext(ObjectiveBarsRenderer);
  const locked = state !== "proposed";
  return (
    <section
      className="col"
      aria-label="Plans side by side"
      data-state={state}
      style={{ opacity: state === "superseded" ? 0.7 : 1 }}
    >
      {state !== "proposed" && (
        <span className="small">{state === "decided" ? "Agreed" : "superseded"}</span>
      )}
      <div className="g3" style={{ gap: 10 }}>
        {plans.map((plan) => (
          <article
            key={plan.id}
            className={cx("card", plan.highlight && "card-live")}
            style={{ gap: 8 }}
            aria-label={plan.label}
          >
            <div className="head">
              <b style={{ fontSize: 13.5 }}>{plan.description ?? plan.label}</b>
              {plan.tag && (
                <span className="h-right">
                  <Badge kind={plan.tag.kind} label={plan.tag.label} />
                </span>
              )}
            </div>
            {renderObjectives?.(plan) ?? <PlanBars plan={plan} />}
            <div className="row">
              {plan.people && <AvatarStack people={plan.people} size="xs" />}
              {plan.note && <span className="small">{plan.note}</span>}
            </div>
            <div className="row">
              <button
                type="button"
                className={cx("btn btn-sm", plan.highlight && "btn-primary")}
                aria-label={
                  decidedId === plan.id ? "Accepted" : `Accept ${plan.short ?? plan.label}`
                }
                disabled={locked || plan.canDecide === false}
                onClick={() => onDecide?.(plan.id)}
              >
                {decidedId === plan.id
                  ? "Accepted"
                  : `Accept ${plan.short ?? plan.label.replace(/^Plan /, "")}`}
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
              <b style={{ fontSize: 13.5, color: "var(--ink-2)" }}>
                {plan.description ?? plan.label}
              </b>
              <span
                className="h-right badge"
                style={{ background: "var(--bad-bg)", color: "var(--bad-fg)" }}
              >
                {plan.tag?.label ?? "not proposed"}
              </span>
            </div>
            {renderObjectives?.(plan, true) ?? <PlanBars plan={plan} muted />}
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

function TensionOptions({
  options,
  group,
  picked,
  open,
  setPicked,
}: {
  options: TensionOption[];
  group: string;
  picked: string;
  open: boolean;
  setPicked: (id: string) => void;
}) {
  return (
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
  );
}
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
  const [explaining, setExplaining] = useState(false);
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
        {state === "decided" && <Tag kind="agreed" />}
        {state === "split" && <Badge kind="estimate" label="split, re-planning" />}
        {state === "expired" && <Badge kind="estimate" label="expired" />}
      </div>
      <TensionOptions
        options={options}
        group={group}
        picked={picked}
        open={open}
        setPicked={setPicked}
      />
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
            decide by{" "}
            {/* An ISO timestamp is shown with its day; friendly text is shown as given. */}
            <time dateTime={deadline}>
              {/^\d{4}-\d{2}-\d{2}T/.test(deadline) && !Number.isNaN(Date.parse(deadline))
                ? new Date(deadline).toLocaleString(undefined, {
                    weekday: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : deadline}
            </time>
          </span>
        )}
      </div>
      {explaining && (
        <div className="small" role="status">
          {options.map((o) => (
            <p key={o.id}>
              <b>{o.label}:</b> {o.tradeoffs.join("; ")}
            </p>
          ))}
        </div>
      )}
      {open && (
        <div className="row">
          <button
            type="button"
            className="btn btn-sm btn-primary"
            aria-label={`Choose ${current?.label ?? ""}`}
            disabled={!current}
            onClick={() => current && onChoose?.(current.id)}
          >
            Choose {current?.label.replace(/^Results /, "") ?? ""}
          </button>
          <button
            type="button"
            className="btn btn-sm"
            aria-expanded={explaining}
            onClick={() => {
              setExplaining(!explaining);
              onAsk?.();
            }}
          >
            Ask Gardener why
          </button>
        </div>
      )}
    </section>
  );
}
