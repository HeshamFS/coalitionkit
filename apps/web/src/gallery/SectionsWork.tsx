// SPDX-License-Identifier: Apache-2.0
import { ConsentCard, VoteTally } from "../components/consent";
import { ActivityStream, ChangedValue, LogStream, RippleBanner } from "../components/live";
import { PlanCompare, TensionCard } from "../components/plans";
import { Row } from "../components/primitives";
import { NeedCard, OfferCard, TaskCard, type TaskStatus, Timeline } from "../components/work";
import { Cell, Family, State } from "./Cell";
import { activity, bound, logEntries, m1, m2, m3, planA, planB, planC } from "./fixtures";

const STATUSES: TaskStatus[] = [
  "open",
  "negotiating",
  "proposed",
  "decided",
  "committed",
  "done",
  "withdrawn",
];
const subject = { kind: "plan", id: "p1", revision: 2 };
const deciders = [
  { ...m1, answered: true },
  { ...m2, answered: false },
  { ...m3, answered: false },
];

export function Work() {
  return (
    <>
      <Family n="06a" title="Needs, offers and tasks">
        <Cell
          name="NeedCard"
          doors={["wide", "compact", "message", "voice"]}
          props="need_id · owner · text · constraints[] · by · state: open | matched | fulfilled | withdrawn · offers: bound"
          events="need.open · need.withdraw"
        >
          <NeedCard
            needId="n1"
            owner={m1}
            text="Need 1"
            state="open"
            offers={0}
            meta="3 h old"
            onOpen={() => {}}
            onWithdraw={() => {}}
          />
          <NeedCard
            needId="n2"
            owner={m2}
            text="Need 2"
            state="matched"
            offers={2}
            meta="planner working"
          />
          <NeedCard needId="n3" owner={m3} text="Need 3" state="fulfilled" meta="by Member 2" />
          <NeedCard needId="n4" owner={m1} text="Need 4" state="withdrawn" />
        </Cell>
        <Cell
          name="OfferCard"
          doors={["wide", "compact", "message", "voice"]}
          props="offer_id · target: need | task · what · cost {amount: bound, kind} · conditions[] · expires · state: open | accepted | expired | withdrawn · scope"
          events="offer.accept · offer.ask · offer.withdraw"
        >
          <OfferCard
            offerId="o1"
            what="Offer 1"
            from="Member 2"
            target="Need 1"
            cost={{ amount: bound(38), unit: "units" }}
            expires="18:00"
            state="open"
          />
          <OfferCard
            offerId="o2"
            what="Offer 2"
            from="Member 3"
            cost={{ amount: bound(12), unit: "min" }}
            state="open"
            needsYou
            onAccept={() => {}}
            onAsk={() => {}}
          />
          <OfferCard offerId="o3" what="Offer 3" state="open" scope="private" />
          <OfferCard
            offerId="o4"
            what="Offer 4"
            state="accepted"
            cost={{ amount: bound(20), unit: "units" }}
          />
          <OfferCard offerId="o5" what="Offer 5" state="expired" expires="09:00" />
          <OfferCard offerId="o6" what="Offer 6" state="withdrawn" />
        </Cell>
        <Cell
          name="TaskCard"
          doors={["wide", "compact", "lens", "message"]}
          span={2}
          props="task_id · title · assignee · window · status (6 + withdrawn) · deps {waitsFor[], unblocks[]} · evidence?"
          events="task.open · task.done"
        >
          <div className="g2" style={{ gap: 8 }}>
            {STATUSES.map((s, i) => (
              <State key={s} label={s}>
                <TaskCard
                  taskId={`t${i + 1}`}
                  title={`Task ${i + 1}`}
                  assignee={i % 2 ? m2 : m1}
                  window="window 1"
                  status={s}
                  waitsFor={i === 3 ? ["t2"] : undefined}
                  unblocks={i === 3 ? ["t4", "t5"] : undefined}
                  evidence={s === "done" ? "photo + mass" : undefined}
                  onOpen={() => {}}
                  onDone={() => {}}
                />
              </State>
            ))}
          </div>
        </Cell>
        <Cell
          name="Timeline"
          doors={["wide", "compact", "message"]}
          props="items[] {start, end?, title, assignee, state} · now marker"
        >
          <Timeline
            items={[
              { when: "Day 1 · 17:20", title: "Step 1", assignee: "Member 1", state: "done" },
              { when: "Day 2 · 16:00", title: "Step 2", assignee: "Member 2", state: "done" },
              { when: "Day 3", title: "Step 3", assignee: "Member 1", state: "now" },
              { when: "Day 4 · 14:00", title: "Step 4", assignee: "Member 2", state: "next" },
              { when: "Day 5 · 12:00", title: "Step 5", assignee: "Member 3", state: "next" },
            ]}
          />
        </Cell>
      </Family>

      <Family n="06b" title="Plans and trade-offs" cols={3}>
        <Cell
          name="PlanCompare · proposed"
          span={3}
          doors={["wide", "compact"]}
          props="plans[] {id, label, objectives{}, assignments[], tags[]} · rejected[] {plan, reason} · proposal_set_id · decision_deadline"
          events="plan.decide(id) → consent · plan.details(id)"
        >
          <PlanCompare
            plans={[planA, planB]}
            rejected={[{ plan: planC, reason: "No run, breaks rule 3 (load over half)" }]}
            deadline="22:40"
            onDecide={() => {}}
            onDetails={() => {}}
          />
        </Cell>
        <Cell
          name="PlanCompare · decided"
          span={3}
          doors={["wide", "compact"]}
          props="state: decided · decidedId"
        >
          <PlanCompare plans={[planA, planB]} state="decided" decidedId="p1" />
        </Cell>
        <Cell
          name="PlanCompare · superseded"
          span={3}
          doors={["wide", "compact"]}
          props="state: superseded (a newer proposal set replaced it)"
        >
          <PlanCompare plans={[planA, planB]} state="superseded" />
        </Cell>
        <Cell
          name="TensionCard"
          span={3}
          doors={["wide", "compact", "message", "voice"]}
          props="tension_id · task_ids[] · options[] {id, label, tradeoffs[]} · deciders[] · answered · decision_deadline"
          events="tension.choose(option) → consent"
        >
          <div className="g2" style={{ gap: 8 }}>
            {(["open", "decided", "split", "expired"] as const).map((s) => (
              <State key={s} label={s}>
                <TensionCard
                  title="Option 1 or option 2? The plans differ."
                  state={s}
                  chosenId={s === "decided" ? "o1" : undefined}
                  options={[
                    { id: "o1", label: "Option 1", tradeoffs: ["faster", "costs more"] },
                    { id: "o2", label: "Option 2", tradeoffs: ["cheaper", "slower"] },
                  ]}
                  deciders={deciders}
                  answered={1}
                  deadline="16:00"
                  onChoose={() => {}}
                  onAsk={() => {}}
                />
              </State>
            ))}
          </div>
        </Cell>
      </Family>

      <Family n="08" title="Decisions and consent" cols={3}>
        <Cell
          name="ConsentCard"
          span={3}
          doors={["wide", "compact", "message", "voice"]}
          props="subject {kind, id, revision} · summary · yourPart · cost · consequenceOfNo · decision_deadline"
          events="decide(yes|no) owner-signed · compare"
        >
          <div className="g2" style={{ gap: 8 }}>
            <State label="open">
              <ConsentCard
                subject={subject}
                title="Plan A, ship early"
                yourPart="t2, t4, t5"
                cost="about 52 after the split"
                consequenceOfNo="the planner re-plans"
                deadline="2 h 14 min left"
                yesLabel="Accept Plan A"
                noLabel="Not this plan"
                onDecide={() => {}}
                onCompare={() => {}}
              />
            </State>
            <State label="busy (sending)">
              <ConsentCard
                subject={subject}
                title="Plan A, ship early"
                yourPart="t2, t4, t5"
                cost="about 52 after the split"
                consequenceOfNo="the planner re-plans"
                deadline="2 h 14 min left"
                yesLabel="Accept Plan A"
                busy
              />
            </State>
            <State label="answered, yes">
              <ConsentCard
                subject={subject}
                title="Plan A, ship early"
                state="answered"
                answer
                yourPart="t2, t4, t5"
              />
            </State>
            <State label="answered, no">
              <ConsentCard
                subject={subject}
                title="Plan A, ship early"
                state="answered"
                answer={false}
              />
            </State>
            <State label="stale">
              <ConsentCard
                subject={subject}
                title="Plan A, ship early"
                state="stale"
                currentRevision={3}
                onReview={() => {}}
              />
            </State>
            <State label="expired">
              <ConsentCard subject={subject} title="Plan A, ship early" state="expired" />
            </State>
          </div>
        </Cell>
        <Cell
          name="VoteTally"
          doors={["wide", "compact"]}
          span={3}
          props="deciders[] · answered (count while open) · answers (after close) · rule · outcome: decided | refused | split | expired"
        >
          <div className="g3" style={{ gap: 8 }}>
            <State label="open">
              <VoteTally title="Plan A" rule="every decider" deciders={deciders} />
            </State>
            <State label="closed, split">
              <VoteTally
                title="Plan A"
                closed
                outcome="split"
                deciders={[
                  { ...m1, answered: true, answer: true },
                  { ...m2, answered: true, answer: true },
                  { ...m3, answered: true, answer: false },
                ]}
              />
            </State>
            <State label="closed, decided">
              <VoteTally
                title="Plan A"
                closed
                outcome="decided"
                deciders={[
                  { ...m1, answered: true, answer: true },
                  { ...m2, answered: true, answer: true },
                ]}
              />
            </State>
          </div>
        </Cell>
      </Family>

      <Family n="09" title="Live and ripple" cols={3}>
        <Cell
          name="RippleBanner · ChangedValue"
          span={2}
          doors={["wide", "compact", "lens"]}
          props="ripple {by, change, invalidated[], untouched[]} · ChangedValue {path, before, after}"
          events="ripple.open"
        >
          <RippleBanner
            ripple={{
              by: "Member 2",
              change: "moved step 2",
              invalidated: ["t2", "t3", "t4", "t5"],
              untouched: ["t1", "t6"],
            }}
            onOpen={() => {}}
            onDismiss={() => {}}
          />
          <div className="g3" style={{ gap: 8 }}>
            <State label="flash (900 ms, once)">
              <Row>
                <span className="small">
                  starts <ChangedValue before="16:00" after="17:00" state="flash" />
                </span>
              </Row>
            </State>
            <State label="tinted until seen">
              <Row>
                <span className="small">
                  starts <ChangedValue before="16:00" after="17:00" state="tinted" />
                </span>
              </Row>
            </State>
            <State label="seen">
              <Row>
                <span className="small">
                  starts <ChangedValue before="16:00" after="17:00" state="seen" />
                </span>
              </Row>
            </State>
          </div>
          <span className="st">reduced motion: tint only</span>
        </Cell>
        <Cell
          name="ActivityStream"
          doors={["wide", "compact"]}
          props="items[] {actor, verb, object, time, seq} · filter: all | about me | decisions"
          events="item.open(seq)"
        >
          <ActivityStream items={activity} onOpen={() => {}} />
        </Cell>
        <Cell
          name="LogStream"
          span={3}
          doors={["wide"]}
          props="entries[] {seq, ts, type, actor, summary, hash, form: original | projection | receipt-only} · gaps never hidden"
          events="entry.open(seq) → WiringDrawer"
        >
          <LogStream entries={logEntries} selected={53} onOpen={() => {}} />
          <State label="chain broken">
            <LogStream entries={logEntries.slice(0, 2)} chainOk={false} />
          </State>
        </Cell>
      </Family>
    </>
  );
}
