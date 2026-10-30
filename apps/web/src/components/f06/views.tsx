// SPDX-License-Identifier: Apache-2.0
import { Frame, list, num, obj, type Props, rows, str, texts } from "../f05/shared";
import * as Plans from "./plans";
import * as Work from "./work";
import "../../styles/f06.css";

const person = (name: unknown) => ({
  label: str(name),
  seat: (str(name).endsWith("A") ? 3 : str(name).endsWith("C") ? 5 : 1) as 1 | 3 | 5,
});
export function NeedCard({ p, send }: Props) {
  return (
    <Frame name="NeedCard">
      <Work.NeedCard
        needId={str(p.need_id)}
        owner={person(p.owner)}
        text={str(p.text)}
        state={(p.state ?? "open") as Work.NeedState}
        offers={num(p.offers)}
        meta={texts(p.constraints) || str(p.by)}
        onOpen={() => send("need.open", { need_id: p.need_id })}
        onWithdraw={() => send("need.withdraw", { need_id: p.need_id })}
      />
    </Frame>
  );
}
export function OfferCard({ p, send }: Props) {
  const cost = obj(p.cost);
  return (
    <Frame name="OfferCard">
      <Work.OfferCard
        offerId={str(p.offer_id)}
        what={str(p.what)}
        from={texts(p.conditions)}
        cost={
          cost.amount
            ? {
                amount: cost.amount as Work.BoundNumber,
                kind: str(cost.kind),
                unit: str(cost.unit),
              }
            : undefined
        }
        expires={str(p.expires)}
        state={(p.state ?? "open") as Work.OfferState}
        needsYou={p.state === "open" && p.target === "task" && p.scope !== "private"}
        scope={str(p.scope)}
        onAccept={() => send("offer.accept", { offer_id: p.offer_id })}
        onAsk={() => send("offer.ask", { offer_id: p.offer_id })}
        onWithdraw={() => send("offer.withdraw", { offer_id: p.offer_id })}
      />
    </Frame>
  );
}
export function TaskCard({ p, send }: Props) {
  const deps = obj(p.deps),
    window = obj(p.window);
  return (
    <Frame name="TaskCard">
      <Work.TaskCard
        taskId={str(p.task_id)}
        title={str(p.title)}
        assignee={p.assignee ? person(p.assignee) : undefined}
        window={`${str(window.start)} – ${str(window.end)}`}
        status={(p.status ?? "open") as Work.TaskStatus}
        waitsFor={list(deps.waitsFor).map(str)}
        unblocks={list(deps.unblocks).map(str)}
        evidence={str(p.evidence)}
        onOpen={() => send("task.open", { task_id: p.task_id })}
        onDone={() => send("task.done", { task_id: p.task_id })}
      />
    </Frame>
  );
}
export function Timeline({ p }: Props) {
  return (
    <Frame name="Timeline">
      <Work.Timeline
        items={rows(p.items).map((r) => ({
          when: str(r.start),
          title: str(r.title),
          assignee: str(r.assignee),
          state: (r.state ?? "next") as Work.TimelineItem["state"],
        }))}
      />
    </Frame>
  );
}
export function PlanCompare({ p, send }: Props) {
  const plans = rows(p.plans),
    expired = !!p.decision_deadline && Date.parse(str(p.decision_deadline)) <= Date.now();
  return (
    <Frame name="PlanCompare">
      <Plans.PlanCompare
        plans={plans.map((r) => ({
          ...r,
          id: str(r.id),
          label: str(r.label),
          canDecide: Boolean(obj(r.subject).kind && obj(r.subject).id && obj(r.subject).revision),
          objectives: list(r.objectives) as Plans.Objective[],
          people: list(r.assignments).map((a) => person(obj(a).participant)),
        }))}
        rejected={list(p.rejected) as Plans.RejectedPlan[]}
        state={expired ? "superseded" : "proposed"}
        deadline={str(p.decision_deadline)}
        onDetails={(id) => send("plan.details", { id })}
        onDecide={(id) => {
          const subject = obj(plans.find((r) => r.id === id)?.subject);
          if (subject.kind && subject.id && subject.revision && !expired)
            send("plan.decide", { proposal_set_id: p.proposal_set_id, subject });
        }}
      />
    </Frame>
  );
}
export function TensionCard({ p, send }: Props) {
  const expired = Date.parse(str(p.decision_deadline)) <= Date.now();
  return (
    <Frame name="TensionCard">
      <Plans.TensionCard
        title={str(rows(p.options)[0]?.summary) || `Choose for ${str(p.tension_id)}`}
        options={rows(p.options).map((r) => ({
          id: str(r.id),
          label: str(r.label),
          tradeoffs: list(r.tradeoffs).map(str),
        }))}
        deciders={list(p.deciders).map((value, i) => ({
          ...person(value),
          answered: i < num(p.answered),
        }))}
        answered={num(p.answered)}
        deadline={str(p.decision_deadline)}
        state={expired ? "expired" : "open"}
        onChoose={(option) => {
          if (!expired) send("tension.choose", { subject: p.subject, option });
        }}
      />
    </Frame>
  );
}
export { AnswerCard } from "./answers";
export function Checklist({ p, send }: Props) {
  const items = rows(p.items),
    task = obj(items[0]?.task);
  return (
    <Frame name="Checklist" className="card f06-checklist">
      {!!task.id && (
        <div className="head">
          <span className="mono st">{str(task.id)}</span>
          <span className="h-title">{str(task.title)}</span>
          <span className="h-right num small">
            {items.filter((r) => r.done).length} / {items.length}
          </span>
        </div>
      )}
      {items.map((r, i) => (
        <label className="row" key={str(r.text)}>
          <input
            type="checkbox"
            className="f06-checkbox"
            aria-label={str(r.text)}
            checked={r.done === true}
            disabled={r.by !== "self"}
            data-live={!!r.evidence && !r.done}
            onChange={() => send("item.toggle", { item: i, done: !r.done })}
          />
          <span className={`small ${r.done ? "f06-done" : "f06-step"}`}>
            {r.evidence && !r.done ? <b>{str(r.text)}</b> : str(r.text)}
          </span>
          {!!r.evidence && <span className="h-right badge b-measured">{str(r.evidence)}</span>}
        </label>
      ))}
    </Frame>
  );
}
export function AssignmentRow({ p }: Props) {
  const assignments = rows(p.assignments),
    first = assignments[0];
  return (
    <Frame name="AssignmentRow" className="card f06-assignment">
      <span className="eyebrow">{first?.plan ? `In ${str(first.plan)} you do` : "Your part"}</span>
      {assignments.map((r) => (
        <div className="row f06-assignment-row" key={str(r.task)}>
          <span className="mono st">{str(r.task)}</span>
          <span className="small grow">{str(r.title)}</span>
          <span className="num small">{str(r.window)}</span>
        </div>
      ))}
      <div className="row small">
        <span>
          {str(p.hours)} h{first?.total ? ` of ${str(first.total)}` : ""} · {str(p.share)} %
        </span>
        <span className="h-right badge b-vault">{str(p.fit)}</span>
      </div>
    </Frame>
  );
}
export function CostSplit({ p }: Props) {
  const items = rows(p.items),
    total = items.reduce((sum, r) => sum + num(r.amount), 0);
  return (
    <Frame name="CostSplit" className="f06-cost">
      <div className="row f06-cost-stack" aria-hidden="true">
        {items.map((r) => (
          <span
            key={str(r.label)}
            style={{
              width: `${total ? (100 * num(r.amount)) / total : 0}%`,
              background: `var(--seat-${person(r.payer).seat})`,
            }}
          />
        ))}
      </div>
      <table className="tbl">
        <thead>
          <tr>
            <th>Item</th>
            <th>Paid by</th>
            <th className="r">Cost</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={str(r.label)}>
              <td>{str(r.label)}</td>
              <td>{str(r.payer)}</td>
              <td className="r num" title={`${str(r.kind)} · ${str(obj(r.amount).event_ref)}`}>
                €{str(r.amount)}
              </td>
            </tr>
          ))}
          <tr>
            <td>
              <b>Total</b>
            </td>
            <td />
            <td className="r num">
              <b>€{total}</b>
            </td>
          </tr>
        </tbody>
      </table>
      <div className="row small">
        {list(p.settlements).map((r, i) => (
          <span key={str(r)} className={i ? "h-right blue" : undefined}>
            {str(r)}
          </span>
        ))}
      </div>
    </Frame>
  );
}
export function MatchView({ p, send }: Props) {
  const offers = rows(p.offers),
    height = Math.max(210, offers.length * 70),
    middle = height / 2 - 1;
  return (
    <Frame name="MatchView">
      <svg
        viewBox={`0 0 300 ${height}`}
        className="f06-match-diagram"
        role="img"
        aria-label="Need and matching offers"
      >
        <rect
          x="4"
          y={middle - 24}
          width="112"
          height="48"
          rx="9"
          fill="var(--surface)"
          stroke="var(--line-strong)"
        />
        <text x="14" y={middle - 4} fill="var(--ink)" fontSize="10.5" fontWeight="600">
          {str(p.need).split(" · ")[0]}
        </text>
        <text x="14" y={middle + 12} fill="var(--ink-3)" fontSize="9.5">
          need
          {str(p.need).includes(" · ") ? ` · ${str(p.need).split(" · ").slice(1).join(" · ")}` : ""}
        </text>
        {offers.map((offer, i) => (
          <g key={str(offer.offer)}>
            <path
              d={`M116 ${middle} C150 ${middle},145 ${34 + i * 70},176 ${34 + i * 70}`}
              fill="none"
              stroke={
                offer.offer === p.chosen
                  ? "var(--blue)"
                  : offer.blockedBy
                    ? "var(--bad-line)"
                    : "var(--line-strong)"
              }
              strokeWidth={offer.offer === p.chosen ? 2 : 1.5}
              strokeDasharray={offer.blockedBy ? "3 4" : undefined}
            />
            <rect
              x="176"
              y={14 + i * 70}
              width="120"
              height="40"
              rx="8"
              fill={
                offer.offer === p.chosen
                  ? "var(--blue-tint)"
                  : offer.blockedBy
                    ? "var(--surface-2)"
                    : "var(--surface)"
              }
              stroke={offer.offer === p.chosen ? "var(--blue)" : "var(--line)"}
              strokeWidth={offer.offer === p.chosen ? 1.5 : 1}
              strokeDasharray={offer.blockedBy ? "3 3" : undefined}
            />
            <text
              x="186"
              y={31 + i * 70}
              fontSize="10.5"
              fontWeight={offer.blockedBy ? 400 : 600}
              fill={
                offer.offer === p.chosen
                  ? "var(--blue-text)"
                  : offer.blockedBy
                    ? "var(--ink-3)"
                    : "var(--ink)"
              }
            >
              {str(offer.offer)}
            </text>
            <text
              x="186"
              y={45 + i * 70}
              fontSize="9.5"
              fill={
                offer.offer === p.chosen
                  ? "var(--blue-text)"
                  : offer.blockedBy
                    ? "var(--bad-fg)"
                    : "var(--ink-3)"
              }
            >
              {offer.blockedBy
                ? `fails: ${str(offer.blockedBy)}`
                : str(offer.description) || texts(offer.reasons)}
            </text>
            <foreignObject x="176" y={14 + i * 70} width="120" height="40">
              <button
                type="button"
                aria-label={str(offer.offer)}
                className="f06-diagram-target"
                onClick={() => send("match.inspect", { offer: offer.offer })}
              />
            </foreignObject>
          </g>
        ))}
      </svg>
      <div className="row small">
        <span className="badge b-model">Gardener</span>best fit:{" "}
        {list(offers.find((offer) => offer.offer === p.chosen)?.reasons)
          .map(str)
          .join(", ")}
      </div>
    </Frame>
  );
}
export { DependencyGraph, FairnessMeter, Gantt, ObjectiveBars } from "./charts";
