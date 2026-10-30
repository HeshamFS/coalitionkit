// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";
import { ParticipantCard } from "../components/f05/views";
import { DecisionLog } from "../components/f08/DecisionLog";
import { WhatOthersKnow } from "../components/f08/WhatOthersKnow";
import { EventRow } from "../components/f09/EventRow";
import { MetricTile } from "../components/f11/MetricTile";
import { EmptyState } from "../components/feedback";
import { PlanCompare } from "../components/plans";
import { Card } from "../components/primitives";
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import {
  deriveDecisions,
  deriveMetrics,
  deriveParticipants,
  derivePlans,
  derivePrivateNotes,
  deriveSchedule,
  eventsOf,
} from "../feed/derive";
import "../styles/f08.css";

const readOnly = () => {};
export function RoomPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="room-panel" aria-label={title}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}
export function Participants({ state, own = false }: { state: ViewerState | null; own?: boolean }) {
  const people = deriveParticipants(state).filter((p) => !own || p.id === state?.viewer);
  if (!people.length)
    return (
      <EmptyState
        title={own ? "Your part" : "No participants yet"}
        body={
          own ? "Your part is not in this projection yet." : "Members appear here when they join."
        }
      />
    );
  return (
    <div className="room-participants">
      {people.map((p) => (
        <div className="room-participant" key={p.id}>
          <ParticipantCard
            p={{
              participant: p.label,
              seat: p.seat,
              roles: [p.agent, p.vendor].filter(Boolean),
              state: p.status,
              capabilities: [],
            }}
            send={readOnly}
          />
          {p.item ? (
            <p className="room-current-item">{p.item}</p>
          ) : (
            <p className="small">No current item in your projection.</p>
          )}
        </div>
      ))}
    </div>
  );
}
export function Plans({ state }: { state: ViewerState | null }) {
  const plans = derivePlans(state);
  return (
    <RoomPanel title="Plan options">
      {plans.length ? (
        <PlanCompare plans={plans} />
      ) : (
        <EmptyState title="No plans yet" body="Proposed options will appear here." />
      )}
    </RoomPanel>
  );
}
export function Metrics({ state }: { state: ViewerState | null }) {
  return (
    <section className="room-metrics" aria-label="Metrics">
      {deriveMetrics(state).map((m) => (
        <MetricTile key={m.label} p={m} send={readOnly} />
      ))}
    </section>
  );
}
export function Wiring({ state }: { state: ViewerState | null }) {
  const events = eventsOf(state);
  return (
    <RoomPanel title="Wiring">
      {events.length ? (
        <div className="room-log">
          {events.map((e) => (
            <EventRow
              key={e.seq}
              p={{
                seq: e.seq,
                type: e.type.replace("coalition.", ""),
                summary:
                  typeof e.payload.description === "string"
                    ? e.payload.description
                    : typeof e.payload.content === "string"
                      ? e.payload.content
                      : "",
              }}
              send={readOnly}
            />
          ))}
        </div>
      ) : (
        <EmptyState title="No events yet" body="" />
      )}
    </RoomPanel>
  );
}
export function Decisions({
  state,
  requests,
  onOpen,
}: {
  state: ViewerState | null;
  requests: OpenRequest[];
  onOpen: (id: string) => void;
}) {
  const entries = deriveDecisions(state);
  return (
    <RoomPanel title="Decisions">
      {entries.length > 0 && <DecisionLog p={{ entries }} send={readOnly} />}
      {requests.map((r) => (
        <button type="button" className="room-request" key={r.id} onClick={() => onOpen(r.id)}>
          <span>{r.message}</span>
          <span className="tag t-needs">Needs you</span>
        </button>
      ))}
      {!entries.length && !requests.length && <EmptyState title="No decisions yet" body="" />}
    </RoomPanel>
  );
}
export function Privacy({ state, own = false }: { state: ViewerState | null; own?: boolean }) {
  const rows = derivePrivateNotes(state);
  return (
    <RoomPanel title={own ? "What others know about you" : "What stayed private"}>
      {rows.length ? (
        <WhatOthersKnow p={{ rows }} send={readOnly} />
      ) : (
        <EmptyState title="No disclosure notes in your projection" body="" />
      )}
    </RoomPanel>
  );
}
export function Schedule({ state }: { state: ViewerState | null }) {
  const items = deriveSchedule(state);
  return (
    <Card title="Schedule">
      {items.length ? (
        <dl className="room-schedule">
          {items.map((item, i) => (
            <div key={item.id || i}>
              <dt>{item.time}</dt>
              <dd>{item.title}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <EmptyState title="No scheduled items yet" body="" />
      )}
    </Card>
  );
}
