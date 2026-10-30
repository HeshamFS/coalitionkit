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
      <small>{str(p.now)}</small>
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
        title={`Choose for ${str(p.tension_id)}`}
        options={rows(p.options).map((r) => ({
          id: str(r.id),
          label: str(r.label),
          tradeoffs: list(r.tradeoffs).map(str),
        }))}
        deciders={list(p.deciders).map(person)}
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
  return (
    <Frame name="Checklist" className="card">
      {rows(p.items).map((r, i) => (
        <label className="row" key={str(r.text)}>
          <input
            type="checkbox"
            checked={r.done === true}
            disabled={r.by !== "self"}
            onChange={() => send("item.toggle", { item: i, done: !r.done })}
          />
          <span className={r.done ? "f06-done" : ""}>{str(r.text)}</span>
          <small>{str(r.evidence)}</small>
        </label>
      ))}
    </Frame>
  );
}
export function AssignmentRow({ p }: Props) {
  return (
    <Frame name="AssignmentRow" className="card">
      <b>Your part</b>
      {list(p.assignments).map((r) => (
        <div key={str(obj(r).task ?? r)}>
          {str(obj(r).task ?? r)} · {str(obj(r).window)}
        </div>
      ))}
      <div className="row">
        <b>
          {str(p.hours)} h · {str(p.share)}%
        </b>
        <span className="badge b-vault">{str(p.fit)}</span>
      </div>
    </Frame>
  );
}
export function CostSplit({ p }: Props) {
  return (
    <Frame name="CostSplit">
      <table className="tbl">
        <thead>
          <tr>
            <th>Item</th>
            <th>Payer</th>
            <th>Amount</th>
            <th>Kind</th>
          </tr>
        </thead>
        <tbody>
          {rows(p.items).map((r) => (
            <tr key={str(r.label)}>
              <td>{str(r.label)}</td>
              <td>{str(r.payer)}</td>
              <td>{str(r.amount)}</td>
              <td>{str(r.kind)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <small>Split {str(p.rule)} · settlements are display only</small>
      {list(p.settlements).map((r) => (
        <p key={str(r)}>{str(r)}</p>
      ))}
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
          {str(p.need)}
        </text>
        <text x="14" y={middle + 12} fill="var(--ink-3)" fontSize="9.5">
          need
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
            <foreignObject x="176" y={14 + i * 70} width="120" height="44">
              <button
                type="button"
                aria-label={str(offer.offer)}
                className={`f06-match-offer ${offer.offer === p.chosen ? "chosen" : ""} ${offer.blockedBy ? "blocked" : ""}`}
                onClick={() => send("match.inspect", { offer: offer.offer })}
              >
                <b>{str(offer.offer)}</b>
                <small>
                  {offer.blockedBy ? `fails: ${str(offer.blockedBy)}` : texts(offer.reasons)}
                </small>
              </button>
            </foreignObject>
          </g>
        ))}
      </svg>
      <div className="row small">
        <span className="badge b-model">Gardener</span>best fit:{" "}
        {texts(offers.find((offer) => offer.offer === p.chosen)?.reasons)}
      </div>
    </Frame>
  );
}
export { DependencyGraph, FairnessMeter, Gantt, ObjectiveBars } from "./charts";
