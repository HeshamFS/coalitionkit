// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { useState } from "react";
import { EmptyState, Skeleton } from "./components/feedback";
import { Card } from "./components/primitives";
import { deriveRoom, humanTime, requestLabel } from "./feed/derive";
import { useAgentSnapshot, useFeedApi, useFeedSnapshot } from "./feed/useFeed";
import { RoomLens } from "./room/lens";
import { usePhoneRoom } from "./room/media";
import { RoomNavigation } from "./room/navigation";
import { Decisions, Metrics, Participants, Plans, Privacy, Schedule, Wiring } from "./room/parts";
import { type ConsentRequest, ConsentTray } from "./shell/dock";
import { RoomShell } from "./shell/RoomShell";
import { TrustedRequest } from "./TrustedRequest";
import "./styles/room.css";
import "./room/refinements.css";

/** Fixed fallback remains available to callers and refused composed trees. */
export function FixedView({ fields }: { fields: { label: string; value: string }[] }) {
  return (
    <Card title="Standard view">
      <dl className="kv">
        {fields.map((f) => (
          <div key={f.label} style={{ display: "contents" }}>
            <dt>{f.label}</dt>
            <dd>{f.value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
export function RoomView() {
  const feed = useFeedSnapshot();
  const agent = useAgentSnapshot();
  const { answer, agent: agentStore, signOut } = useFeedApi();
  const [selected, setSelected] = useState("Stage");
  const phone = usePhoneRoom();
  const room = deriveRoom(feed.state);
  const open =
    agent.requests.find((r) => r.id === agent.focus) ?? (phone ? agent.requests[0] : undefined);
  const section = agent.focus ? "My part" : phone && selected === "Stage" ? "My part" : selected;
  const select = (tab: string) => {
    agentStore.setFocus(null);
    setSelected(tab);
  };
  const onOpen = (id: string) => {
    agentStore.setFocus(id);
    setSelected("My part");
  };
  const consent = open ? (
    <TrustedRequest
      key={`${open.id}:${open.revision}`}
      request={{
        ...open,
        message: requestLabel(feed.state, open),
        expiresAt: humanTime(open.expiresAt) || undefined,
      }}
      state={feed.state}
      onAnswer={(a) => answer(a)}
    />
  ) : (
    <EmptyState
      title={agent.requests.length ? "Choose a request to review" : "Nothing needs your answer"}
      body=""
    />
  );
  return (
    <RoomShell
      layout="stage"
      title={room.title}
      stage={room.stage}
      meta={`${room.members} members`}
      presence={[]}
      groups={[]}
      selected={selected}
      onSelect={select}
      connection={feed.status === "live" ? "live" : "reconnecting"}
      onSignOut={signOut}
      navigation={<RoomNavigation selected={section} onSelect={select} />}
      aside={
        <>
          <Wiring state={feed.state} />
          <Decisions state={feed.state} requests={agent.requests} onOpen={onOpen} />
          <Privacy state={feed.state} />
        </>
      }
    >
      <div className="room-content" data-section={section}>
        {agent.refusal && (
          <Card tone="dashed">
            <span role="alert">The host did not take that answer: {agent.refusal}</span>
          </Card>
        )}
        {feed.status === "connecting" && <Skeleton shape="card" label="Loading your view" />}
        <div className="room-stage-content">
          <div className="room-goal">
            <span>
              <b>Goal</b> · {room.title}
            </span>
            <span className="room-connection">
              <span className="live-dot" />
              {feed.status}
            </span>
          </div>
          <Participants state={feed.state} />
          <Plans state={feed.state} />
          <Metrics state={feed.state} />
        </div>
        <div className="room-own-content">
          <Participants state={feed.state} own />
          {consent}
          <Schedule state={feed.state} />
          <Privacy state={feed.state} own />
        </div>
        <div className="room-plans-content">
          <Plans state={feed.state} />
        </div>
        <div className="room-wiring-content">
          <Wiring state={feed.state} />
          <Decisions state={feed.state} requests={agent.requests} onOpen={onOpen} />
        </div>
        <div className="room-lens-content">
          <RoomLens state={feed.state} />
        </div>
        <ConsentTray
          requests={agent.requests.map((r) => ({
            id: r.id,
            kind: (r.kind === "tension_option" ? "tension" : r.kind) as ConsentRequest["kind"],
            title: requestLabel(feed.state, r),
            revision: r.revision,
            deadline: r.expiresAt ? `decide by ${humanTime(r.expiresAt)}` : undefined,
          }))}
          onOpen={onOpen}
        />
        <div className="surface-host">
          {feed.surfaces.map((s) => (
            <A2uiSurface key={s.id} surface={s.model} />
          ))}
        </div>
      </div>
    </RoomShell>
  );
}
