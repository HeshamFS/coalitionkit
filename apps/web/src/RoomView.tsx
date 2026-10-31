// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { useState } from "react";
import { Card } from "./components/primitives";
import { deriveParticipants, deriveRoom, humanTime, requestLabel } from "./feed/derive";
import { useAgentSnapshot, useFeedApi, useFeedSnapshot } from "./feed/useFeed";
import { sheetFor } from "./room/consentSheet";
import { RoomLens } from "./room/lens";
import { usePhoneRoom } from "./room/media";
import {
  AgentsMoment,
  ChainMoment,
  DissolveMoment,
  dissolvedEvent,
  OverlapMoment,
  RippleMoment,
} from "./room/moments";
import { MyPart } from "./room/mypart";
import { PhoneNav, RoomNavigation } from "./room/navigation";
import { Decisions, MeasuredStrip, Participants, Plans, Privacy, Wiring } from "./room/parts";
import { usePrism } from "./room/prism";
import { SignedNotice } from "./room/signed";
import { ViewAsMenu, ViewAsPanel } from "./room/viewAsPanel";
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
  const [signed, setSigned] = useState<{ question: string; seq: number; signature: string }>();
  const phone = usePhoneRoom();
  const prism = usePrism();
  const room = deriveRoom(feed.state);
  const ready = feed.state !== null;
  const n = Math.max(deriveParticipants(feed.state).length, 1);
  const open = agent.requests.find((r) => r.id === agent.focus);
  const section = agent.focus ? "My part" : phone && selected === "Stage" ? "My part" : selected;
  const ended = dissolvedEvent(feed.state) !== null && section !== "Wiring";
  const select = (tab: string) => {
    agentStore.setFocus(null);
    if (tab !== "Stage") prism.reset();
    setSelected(tab);
  };
  const onOpen = (id: string) => {
    agentStore.setFocus(id);
    setSelected("My part");
  };
  const viewAs = (id: string | null) => {
    agentStore.setFocus(null);
    setSelected("Stage");
    prism.go(id);
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
      onAnswer={async (a) => {
        const ack = await answer(a);
        if (ack && a.consent) setSigned({ question: sheetFor(open, feed.state).question, ...ack });
        return ack;
      }}
      onSeePlans={() => {
        agentStore.setFocus(null);
        setSelected(phone ? "Plans" : "Stage");
      }}
    />
  ) : null;
  const wiring = (
    <>
      <Wiring state={feed.state} ready={ready} index={n + 2} />
      <Decisions
        state={feed.state}
        ready={ready}
        index={n + 3}
        requests={agent.requests}
        onOpen={onOpen}
      />
    </>
  );
  const stage = (
    <div className="room-prism" data-prism={prism.phase}>
      <div className="room-goal">
        <span className="room-goal-chip">
          <b>Goal</b> · {room.title}
        </span>
      </div>
      {prism.target ? (
        <ViewAsPanel
          state={feed.state}
          target={prism.target}
          ready={ready}
          onBack={() => prism.go(null)}
        />
      ) : (
        <>
          <Participants state={feed.state} ready={ready} />
          <Plans
            state={feed.state}
            ready={ready}
            index={n}
            requests={agent.requests}
            onOpen={onOpen}
          />
        </>
      )}
      <MeasuredStrip key={prism.target ?? "me"} state={feed.state} ready={ready} index={n + 1} />
    </div>
  );
  const myPart = (
    <MyPart
      state={feed.state}
      ready={ready}
      requests={agent.requests}
      consent={consent}
      onApprove={onOpen}
      onSeePlans={() => select(phone ? "Plans" : "Stage")}
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
      selected={section}
      onSelect={select}
      connection={feed.status === "live" ? "live" : "reconnecting"}
      onSignOut={signOut}
      navigation={
        phone ? undefined : (
          <RoomNavigation selected={section} onSelect={select}>
            <ViewAsMenu
              state={feed.state}
              active={prism.target}
              onPick={viewAs}
              onLens={() => select("Lens")}
            />
          </RoomNavigation>
        )
      }
      bottomNav={phone ? <PhoneNav selected={section} onSelect={select} /> : undefined}
      aside={
        phone || (section !== "Stage" && section !== "My part") ? undefined : (
          <>
            {wiring}
            <Privacy state={feed.state} ready={ready} index={n + 4} />
          </>
        )
      }
    >
      <div className="room-content" data-section={section}>
        {agent.refusal && (
          <Card tone="dashed">
            <span role="alert">The host did not take that answer: {agent.refusal}</span>
          </Card>
        )}
        {ended ? (
          <DissolveMoment state={feed.state} />
        ) : (
          <>
            {section === "Stage" && stage}
            {section === "My part" && (
              <div className="room-stack">
                {signed && (
                  <SignedNotice
                    question={signed.question}
                    seq={signed.seq}
                    signature={signed.signature}
                    onClose={() => setSigned(undefined)}
                  />
                )}
                {myPart}
                <OverlapMoment state={feed.state} />
              </div>
            )}
            {section === "Agents" && <AgentsMoment state={feed.state} />}
            {section === "Plans" && (
              <div className="room-stack">
                <Plans state={feed.state} ready={ready} requests={agent.requests} onOpen={onOpen} />
                <RippleMoment state={feed.state} />
              </div>
            )}
          </>
        )}
        {section === "Wiring" && (
          <div className="room-stack">
            <ChainMoment state={feed.state} />
            {wiring}
          </div>
        )}
        {section === "Lens" && <RoomLens state={feed.state} />}
        {!phone && (
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
        )}
        <div className="surface-host">
          {feed.surfaces.map((s) => (
            <A2uiSurface key={s.id} surface={s.model} />
          ))}
        </div>
      </div>
    </RoomShell>
  );
}
