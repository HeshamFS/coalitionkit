// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation } from "@a2ui/react/v0_9";
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { ConsentCard, VoteTally } from "../components/consent";
import { LensCard } from "../components/lens";
import { ActivityStream, ChangedValue, LogStream, RippleBanner } from "../components/live";
import { PlanCompare, TensionCard } from "../components/plans";
import { ScopeBadge, type Seat } from "../components/primitives";
import { NeedCard, OfferCard, TaskCard, Timeline } from "../components/work";
import { apis } from "./schemas";

/** Named events go back to the host as data; the catalog never carries code. */
export function emit(context: ComponentContext, name: string, data: Record<string, unknown> = {}) {
  void context.dispatchAction({ event: { name, context: data } });
}

const seatOf = (s: string): Seat => (s === "host" || s === "steward" ? s : (Number(s) as Seat));
const person = <P extends { seat: string; label: string }>(p: P) => ({
  ...p,
  seat: seatOf(p.seat),
});

const bv = (n: { value: number } | undefined) => n?.value;

export const implementations = [
  createComponentImplementation(apis.ScopeBadge, ({ props }) => (
    <ScopeBadge
      audience={props.audience}
      redact={props.redact as unknown as string[] | undefined}
    />
  )),
  createComponentImplementation(apis.TaskCard, ({ props, context }) => (
    <TaskCard
      taskId={props.task_id}
      title={props.title ?? ""}
      assignee={props.assignee ? person(props.assignee) : undefined}
      window={props.window}
      status={props.status}
      waitsFor={props.deps?.waitsFor}
      unblocks={props.deps?.unblocks}
      evidence={props.evidence}
      onOpen={() => emit(context, "task.open", { task_id: props.task_id })}
      onDone={() => emit(context, "task.done", { task_id: props.task_id })}
    />
  )),
  createComponentImplementation(apis.NeedCard, ({ props, context }) => (
    <NeedCard
      needId={props.need_id}
      owner={person(props.owner)}
      text={props.text ?? ""}
      state={props.state}
      offers={bv(props.offers)}
      meta={props.meta}
      onOpen={() => emit(context, "need.open", { need_id: props.need_id })}
      onWithdraw={() => emit(context, "need.withdraw", { need_id: props.need_id })}
    />
  )),
  createComponentImplementation(apis.OfferCard, ({ props, context }) => (
    <OfferCard
      offerId={props.offer_id}
      what={props.what ?? ""}
      from={props.from}
      target={props.target}
      cost={props.cost}
      expires={props.expires}
      state={props.state}
      needsYou={props.needsYou}
      scope={props.scope}
      onAccept={() => emit(context, "offer.accept", { offer_id: props.offer_id })}
      onAsk={() => emit(context, "offer.ask", { offer_id: props.offer_id })}
      onWithdraw={() => emit(context, "offer.withdraw", { offer_id: props.offer_id })}
    />
  )),
  createComponentImplementation(apis.Timeline, ({ props }) => (
    <Timeline items={Array.isArray(props.items) ? props.items : []} />
  )),
  createComponentImplementation(apis.PlanCompare, ({ props, context }) => (
    <PlanCompare
      plans={props.plans.map((p) => ({ ...p, people: p.people?.map(person) }))}
      rejected={props.rejected?.map((r) => ({
        ...r,
        plan: { ...r.plan, people: r.plan.people?.map(person) },
      }))}
      state={props.state}
      deadline={props.decision_deadline}
      decidedId={props.decidedId}
      onDecide={(id) =>
        emit(context, "plan.decide", {
          proposal_set_id: props.proposal_set_id,
          subject: { kind: "plan", id },
        })
      }
      onDetails={(id) => emit(context, "plan.details", { id })}
    />
  )),
  createComponentImplementation(apis.TensionCard, ({ props, context }) => (
    <TensionCard
      title={props.title ?? ""}
      options={props.options}
      deciders={props.deciders.map(person)}
      answered={props.answered.value}
      deadline={props.decision_deadline}
      state={props.state}
      chosenId={props.chosenId}
      onChoose={(option) =>
        emit(context, "tension.choose", {
          subject: { kind: "tension_option", id: props.tension_id },
          option,
        })
      }
      onAsk={() => emit(context, "tension.ask", { tension_id: props.tension_id })}
    />
  )),
  createComponentImplementation(apis.ConsentCard, ({ props, context }) => (
    <ConsentCard
      subject={{
        kind: props.subject.kind,
        id: props.subject.id,
        revision: props.subject.revision.value,
      }}
      title={props.summary ?? ""}
      yourPart={props.yourPart}
      cost={props.cost}
      consequenceOfNo={props.consequenceOfNo}
      deadline={props.decision_deadline}
      state={props.state}
      answer={props.answer}
      currentRevision={bv(props.currentRevision)}
      yesLabel={props.yesLabel}
      noLabel={props.noLabel}
      onDecide={(consent) => emit(context, "decide", { subject: props.subject, consent })}
      onCompare={() => emit(context, "compare", { subject: props.subject })}
      onReview={() => emit(context, "open", { subject: props.subject })}
    />
  )),
  createComponentImplementation(apis.VoteTally, ({ props }) => (
    <VoteTally
      title={props.title ?? ""}
      rule={props.rule}
      deciders={props.deciders.map(person)}
      outcome={props.outcome}
      closed={props.closed}
    />
  )),
  createComponentImplementation(apis.RippleBanner, ({ props, context }) => (
    <RippleBanner ripple={props.ripple} onOpen={() => emit(context, "ripple.open")} />
  )),
  createComponentImplementation(apis.LensCard, ({ props }) => {
    const count = props.gestures === undefined ? 2 : Number(props.gestures);
    const hints = [
      { gesture: "Tap" as const, does: "confirm" },
      { gesture: "Swipe" as const, does: "next", tone: "muted" as const },
    ].slice(0, count);
    return (
      <LensCard eyebrow={props.eyebrow} title={props.title ?? ""} body={props.body} hints={hints} />
    );
  }),
  createComponentImplementation(apis.ChangedValue, ({ props }) => (
    <ChangedValue before={props.before} after={props.after ?? ""} state={props.state} />
  )),
  createComponentImplementation(apis.ActivityStream, ({ props, context }) => (
    <ActivityStream
      items={(Array.isArray(props.items) ? props.items : []).map((i, n) => ({
        ...i,
        seq: bv(i.seq) ?? n,
        actor: person(i.actor),
      }))}
      onOpen={(seq) => emit(context, "item.open", { seq })}
    />
  )),
  createComponentImplementation(apis.LogStream, ({ props, context }) => (
    <LogStream
      entries={(Array.isArray(props.entries) ? props.entries : []).map((e, n) => ({
        ...e,
        seq: bv(e.seq) ?? n,
      }))}
      selected={bv(props.selected)}
      onOpen={(seq) => emit(context, "entry.open", { seq })}
    />
  )),
];
