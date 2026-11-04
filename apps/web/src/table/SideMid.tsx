// SPDX-License-Identifier: Apache-2.0
// Your side while agents work, while plans are on the table, and while commitments are asked.

import { useState } from "react";
import type { Plan } from "../components/f06/plans";
import { TrustedConsentSeal } from "../components/f08/ConsentSeal";
import { askForPlan, requestLabel, visibleRequests } from "../feed/derive";
import { AskCard, Asks, summaryOf } from "./Asks";
import { answerAll, partRequests } from "./commit";
import { useTable } from "./context";
import { PlanCards } from "./PlanCards";

export function SideWork() {
  const { room } = useTable();
  const feed = room.mine.feed.slice(-8);
  return (
    <>
      <h2>Your agent, live</h2>
      {feed.length === 0 ? (
        <p role="status">Your agent has not written anything yet.</p>
      ) : (
        <div className="tb-feed" role="log" aria-label="Your agent's private feed">
          {feed.map((f) => (
            <div key={`${f.at}:${f.text}`}>{f.text}</div>
          ))}
        </div>
      )}
      <Asks />
      <p className="tb-note">You can leave. It asks only when the call is yours.</p>
    </>
  );
}

export function SideDecide({
  plans,
  selected,
  onPick,
  phone,
}: {
  plans: Plan[];
  selected: string | null;
  onPick: (id: string) => void;
  phone: boolean;
}) {
  const { room, state, requests } = useTable();
  const plan = plans.find((p) => p.id === selected);
  const ask = plan ? askForPlan(state, requests, plan.id) : undefined;
  const mine = plan ? room.mine.for_you[plan.id] : undefined;
  const title = plan ? room.plan_notes[plan.id]?.name || plan.label : "Pick a plan";
  return (
    <>
      {phone && (
        <PlanCards
          plans={plans}
          room={room}
          selected={selected}
          signed={new Set()}
          onPick={onPick}
          placement="side"
        />
      )}
      <h2>{title}</h2>
      <p>
        {plan
          ? mine
            ? `If you say yes: ${mine}. Nothing else commits you.`
            : "If you say yes, this plan is chosen for you. Nothing else commits you."
          : "Each card shows what the plan means for you. This is your call, not your agent's."}
      </p>
      {plan && ask && <AskCard request={ask} />}
      {plan && !ask && <p role="status">Nothing is waiting for your yes on this plan.</p>}
      {!plan && <Asks kinds={["plan", "tension_option"]} />}
      <div className="tb-card">
        <span className="tb-tag">Still private</span>
        <p>Your other free times, your limits and your reasons. A plan never shows them.</p>
      </div>
    </>
  );
}

export function SideCommit() {
  const { requests, state, outcome, room } = useTable();
  // A task that an open commitment covers is closed by that commitment's yes, so it is not a
  // second thing waiting: count and answer what is shown.
  const mine = visibleRequests(state, partRequests(requests));
  const key = mine.map((r) => r.id).join("|");
  const [note, setNote] = useState("");
  return (
    <>
      <h2>Start my part</h2>
      {mine.length === 0 ? (
        <p role="status">
          {room.phase === "commit"
            ? "Nothing is waiting for your yes. The others are still signing."
            : "Nothing is waiting for your yes."}
        </p>
      ) : (
        <>
          <p>
            {mine.length} {mine.length === 1 ? "thing waits" : "things wait"} for your yes. One hold
            answers {mine.length === 1 ? "it" : "each, one after the other"}.
          </p>
          <ul className="tb-list" aria-label="What you would say yes to">
            {mine.map((r) => (
              <li key={r.id}>{summaryOf(room, r) ?? requestLabel(state, r)}</li>
            ))}
          </ul>
          <div className="tb-seal">
            <TrustedConsentSeal
              key={key}
              onApprove={async () => {
                const done = await answerAll(mine, outcome);
                setNote(
                  done.handled > 0
                    ? `${done.answered + done.handled} answered. ${done.handled} was already closed by an earlier yes.`
                    : "",
                );
                return done.last;
              }}
            />
          </div>
          {note && <p role="status">{note}</p>}
          <p className="tb-note">
            Each yes is its own record, signed for you by the host after your yes. Your agent never
            answers for you.
          </p>
        </>
      )}
      <Asks kinds={["charter", "plan", "tension_option"]} />
    </>
  );
}
