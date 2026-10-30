// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";
import { ParticipantCard } from "../components/f05/views";
import { DecisionLog } from "../components/f08/DecisionLog";
import { WhatOthersKnow } from "../components/f08/WhatOthersKnow";
import { EventRow } from "../components/f09/EventRow";
import { MetricTile } from "../components/f11/MetricTile";
import { EmptyState } from "../components/feedback";
import { ObjectiveBarsRenderer, PlanCompare } from "../components/plans";
import { Card } from "../components/primitives";
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import {
  deriveDecisions,
  deriveMetrics,
  deriveParticipants,
  derivePlans,
  derivePrivateNotes,
  deriveRoom,
  deriveSchedule,
  eventsOf,
  humanTime,
  requestLabel,
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
        <div
          className="room-participant"
          key={p.id}
          data-initials={p.label
            .split(/\s+/)
            .map((word) => word[0])
            .slice(0, 2)
            .join("")}
          data-status={p.status}
        >
          <ParticipantCard
            p={{
              participant: p.label,
              seat: p.seat,
              roles: p.agent ? [`${p.agent}${p.vendor ? ` on ${p.vendor}` : ""}`] : [],
              state: "",
              capabilities: [],
            }}
            send={readOnly}
          />
          {own && <span className="eyebrow">Your part</span>}
          {p.item ? (
            <p className="room-current-item">{p.item}</p>
          ) : (
            <p className="small">No current item in your projection.</p>
          )}
          {p.detail && <p className="room-item-detail">{p.detail}</p>}
          {p.status && (
            <span
              className={`tag ${p.status === "Agreed" ? "t-agreed" : p.status === "Changed · ripple" ? "t-changed" : "t-needs"}`}
            >
              {p.status}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
export function Plans({ state }: { state: ViewerState | null }) {
  const plans = derivePlans(state);
  return (
    <RoomPanel title={`Plan options for ${deriveRoom(state).title}`}>
      {plans.length ? (
        <div className="room-plan-options">
          {plans.length > 1 && <p className="small">none better on every goal; they choose</p>}
          <ObjectiveBarsRenderer.Provider value={() => <></>}>
            <PlanCompare plans={plans} />
          </ObjectiveBarsRenderer.Provider>
        </div>
      ) : (
        <EmptyState title="No plans yet" body="Proposed options will appear here." />
      )}
    </RoomPanel>
  );
}
export function Metrics({ state }: { state: ViewerState | null }) {
  if (!deriveMetrics(state).length) return null;
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
    <RoomPanel title="Wiring · live">
      {events.length ? (
        <div className="room-log">
          {events.map((e) => (
            <EventRow
              key={e.seq}
              p={{
                seq: e.seq,
                selected: e === events.at(-1),
                type: e.type.replace("coalition.", ""),
                summary:
                  typeof e.payload.description === "string"
                    ? e.payload.description
                    : typeof e.payload.content === "string"
                      ? e.payload.content
                      : typeof e.payload.goal === "string"
                        ? e.payload.goal
                        : (e.on_behalf_of ?? ""),
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
  const plans = derivePlans(state);
  const entries = deriveDecisions(state).map((entry) => ({
    ...entry,
    subject:
      plans.find((p) => p.id === entry.subject)?.label ??
      entry.subject.replace(/[0-9A-HJKMNP-TV-Z]{26}/gi, "item"),
    time: humanTime(entry.time),
  }));
  return (
    <RoomPanel title="Decisions">
      {entries.length > 0 && <DecisionLog p={{ entries }} send={readOnly} />}
      {requests.map((r) => (
        <button type="button" className="room-request" key={r.id} onClick={() => onOpen(r.id)}>
          <span>{requestLabel(state, r)}</span>
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
              <dt>{humanTime(item.time)}</dt>
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
