// SPDX-License-Identifier: Apache-2.0
// The panels of the Stage board. Each one is a single card that germinates on its own.
import type { ReactNode } from "react";
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import {
  deriveDecisions,
  deriveParticipants,
  derivePlans,
  derivePrivateNotes,
  deriveSchedule,
  eventsOf,
  humanTime,
  requestLabel,
} from "../feed/derive";
import { Germ } from "./germ";
import { deriveStrip } from "./measured";
import { agentLine, initialsOf, PILL_CLASS, type Pill, pillFor } from "./status";

type Ready = { ready: boolean; index?: number };

export function Empty({ title, body }: { title: string; body?: string }) {
  return (
    <div className="room-empty">
      <b>{title}</b>
      {body && <span>{body}</span>}
    </div>
  );
}

export function PillTag({ pill }: { pill: Pill | null }) {
  return pill ? <span className={`tag ${PILL_CLASS[pill.tone]}`}>{pill.word}</span> : null;
}

export function SeatAvatar({ seat, label }: { seat: number; label: string }) {
  return (
    <span className="room-avatar" style={{ background: `var(--seat-${seat})` }} aria-hidden="true">
      {initialsOf(label)}
    </span>
  );
}

export function RoomPanel({
  title,
  note,
  children,
  className,
}: {
  title: string;
  note?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={["room-panel", className].filter(Boolean).join(" ")} aria-label={title}>
      <div className="room-panel-head">
        <h2>{title}</h2>
        {note && <span className="room-note">{note}</span>}
      </div>
      {children}
    </section>
  );
}

/** One card per member, in join order, each in its seat colour. */
export function Participants({ state, ready, index = 0 }: { state: ViewerState | null } & Ready) {
  const people = deriveParticipants(state);
  if (!people.length) {
    return (
      <section className="room-participants" aria-label="Participants' screens">
        <Germ index={index} ready={ready} label="ParticipantCard">
          <Empty title="No participants yet" body="Members appear here as they join." />
        </Germ>
      </section>
    );
  }
  return (
    <section className="room-participants" aria-label="Participants' screens">
      {people.map((p, i) => {
        const own = p.id === state?.viewer;
        const pill = pillFor(p.status, { own, hasItem: Boolean(p.item) });
        const line = agentLine(p.agent, p.vendor);
        return (
          <Germ key={p.id} index={index + i} ready={ready} label="ParticipantCard">
            <article
              className="room-participant"
              data-status={pill?.tone ?? "none"}
              data-own={own || undefined}
              aria-label={p.label}
            >
              <div className="room-participant-head">
                <SeatAvatar seat={p.seat} label={p.label} />
                <span className="room-participant-name">{p.label}</span>
                {own && <span className="room-you">you</span>}
                {line && <span className="room-participant-line">{line}</span>}
              </div>
              {p.item ? (
                <p className="room-current-item">{p.item}</p>
              ) : (
                <p className="room-current-item room-quiet">
                  {own ? "Your part appears here" : "Nothing shared with you yet"}
                </p>
              )}
              <p className="room-item-detail">
                {p.detail ||
                  (p.item
                    ? ""
                    : own
                      ? "Only you see it. Others learn what you agree to share."
                      : "What this member holds stays private to them.")}
              </p>
              <PillTag pill={pill} />
            </article>
          </Germ>
        );
      })}
    </section>
  );
}

export function Plans({
  state,
  ready,
  index = 0,
  requests = [],
  onOpen,
}: {
  state: ViewerState | null;
  requests?: OpenRequest[];
  onOpen?: (id: string) => void;
} & Ready) {
  const plans = derivePlans(state);
  return (
    <Germ index={index} ready={ready} label="PlanCompare">
      <RoomPanel
        title="Plan options"
        note={plans.length > 1 ? "none better on every goal; they choose" : undefined}
      >
        {plans.length ? (
          <ul className="room-plan-options">
            {plans.map((plan) => {
              const ask = requests.find((r) => r.subjectId === plan.id);
              return (
                <li key={plan.id} className="room-plan" data-chosen={plan.highlight || undefined}>
                  <b>{plan.label}</b>
                  <span>{plan.note || "No trade-offs listed"}</span>
                  {ask && onOpen && (
                    <button type="button" className="btn btn-sm" onClick={() => onOpen(ask.id)}>
                      Review plan {plan.short}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <Empty title="No plans yet" body="Proposed options appear here, side by side." />
        )}
      </RoomPanel>
    </Germ>
  );
}

/** Agents, vendors, calendars shared, time, seq and spend. Unknown numbers stay `[MEASURED]`. */
export function MeasuredStrip({ state, ready, index = 0 }: { state: ViewerState | null } & Ready) {
  const s = deriveStrip(state);
  return (
    <Germ index={index} ready={ready} label="MetricStrip" className="room-strip-cell">
      <section className="room-strip" aria-label="Measured">
        <span className="room-chip">
          <b>{s.agents}</b> agents · <b>{s.vendors}</b> vendors
        </span>
        <span className="room-chip">
          calendars shared <b>{s.calendars}</b>
        </span>
        <span className="room-chip">
          time to first commitment <b>{s.elapsed}</b>
        </span>
        <span className="room-chip room-chip-mono">
          seq {s.seq} · spent {s.spent}
        </span>
      </section>
    </Germ>
  );
}

const summaryOf = (e: ReturnType<typeof eventsOf>[number]): string => {
  const hit = ["description", "content", "goal"]
    .map((k) => e.payload[k])
    .find((v) => typeof v === "string");
  return typeof hit === "string" ? hit : "";
};

export function Wiring({ state, ready, index = 0 }: { state: ViewerState | null } & Ready) {
  const events = eventsOf(state).slice(-40);
  return (
    <Germ index={index} ready={ready} label="EventLog">
      <section className="room-panel room-wiring" aria-label="Wiring · live">
        <h2>Wiring · live</h2>
        {events.length ? (
          <ol className="room-log">
            {events.map((e, i) => (
              <li key={e.seq} data-last={i === events.length - 1 || undefined}>
                <span className="room-log-seq">{e.seq}</span>
                <span>
                  {e.type.replace("coalition.", "")}
                  {summaryOf(e) && <span className="room-log-sum"> · {summaryOf(e)}</span>}
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <Empty title="No events yet" body="Each message appears here with its seq." />
        )}
      </section>
    </Germ>
  );
}

export function Decisions({
  state,
  requests,
  onOpen,
  ready,
  index = 0,
}: {
  state: ViewerState | null;
  requests: OpenRequest[];
  onOpen: (id: string) => void;
} & Ready) {
  const plans = derivePlans(state);
  const names = new Map(deriveParticipants(state).map((p) => [p.id, p.label]));
  const entries = deriveDecisions(state);
  return (
    <Germ index={index} ready={ready} label="DecisionLog">
      <RoomPanel title="Decisions">
        {entries.map((e) => (
          <div className="room-decision" key={e.seq} data-tone={e.answer === "no" ? "bad" : "ok"}>
            <span className="room-dot" aria-hidden="true" />
            <span>
              {names.get(e.participant) ?? "A member"} said {e.answer || "something"} to{" "}
              {plans.find((p) => p.id === e.subject)?.label ?? "an item"}
            </span>
            <span className="room-decision-time">{humanTime(e.time)}</span>
          </div>
        ))}
        {requests.map((r) => (
          <button
            type="button"
            className="room-decision room-request"
            key={r.id}
            onClick={() => onOpen(r.id)}
          >
            <span className="room-dot" data-tone="warn" aria-hidden="true" />
            <span>{requestLabel(state, r)}</span>
            <span className="tag t-needs">Needs you</span>
          </button>
        ))}
        {!entries.length && !requests.length && (
          <Empty title="No decisions yet" body="Answers are recorded here as members decide." />
        )}
      </RoomPanel>
    </Germ>
  );
}

/** Stage aside: "What stayed private". My part: "What others know about you". */
export function Privacy({
  state,
  ready,
  index = 0,
  own = false,
}: { state: ViewerState | null; own?: boolean } & Ready) {
  const rows = derivePrivateNotes(state);
  const names = new Map(deriveParticipants(state).map((p) => [p.id, p.label]));
  return (
    <Germ index={index} ready={ready} label="WhatOthersKnow">
      <RoomPanel title={own ? "What others know about you" : "What stayed private"}>
        {own && <PillTag pill={{ tone: "private", word: "Private" }} />}
        {rows.length ? (
          <ul className="room-notes">
            {rows.map((r) => (
              <li key={`${r.participant}:${r.knows}`}>
                <b>{names.get(r.participant) ?? "A member"}</b> knows <b>{r.knows}</b>
                {r.notKnows && (
                  <>
                    , not <b>{r.notKnows}</b>
                  </>
                )}
                {r.because && <span className="room-because"> · {r.because}</span>}
              </li>
            ))}
          </ul>
        ) : (
          <Empty
            title="Nothing shared yet"
            body="What each member reveals, and what stays with them, is listed here."
          />
        )}
      </RoomPanel>
    </Germ>
  );
}

export function Schedule({ state, ready, index = 0 }: { state: ViewerState | null } & Ready) {
  const items = deriveSchedule(state);
  return (
    <Germ index={index} ready={ready} label="Timeline">
      <RoomPanel title="Timeline">
        {items.length ? (
          <dl className="room-schedule">
            {items.map((item, i) => (
              <div key={item.id || i}>
                <dt>{humanTime(item.time)}</dt>
                <dd>{item.title}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <Empty title="Nothing scheduled yet" body="Times appear once the plan is committed." />
        )}
      </RoomPanel>
    </Germ>
  );
}
