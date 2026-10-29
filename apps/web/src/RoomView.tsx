// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { useMemo, useState, useSyncExternalStore } from "react";
import { EmptyState, Skeleton } from "./components/feedback";
import { Card } from "./components/primitives";
import { deriveRoom, eventsOf, fixedFields } from "./feed/derive";
import { useAgentSnapshot, useFeedApi, useFeedSnapshot } from "./feed/useFeed";
import type { DeckGroup, PresenceEntry } from "./shell/bars";
import { AgentDock, type ConsentRequest, ConsentTray, WiringDrawer } from "./shell/dock";
import { PhoneShell, type PhoneTab, RoomShell } from "./shell/RoomShell";
import { TrustedRequest } from "./TrustedRequest";

const SEATS = [1, 2, 3, 4, 5] as const;

function useMedia(query: string): boolean {
  const mq = useMemo(() => window.matchMedia(query), [query]);
  return useSyncExternalStore(
    (fn) => {
      mq.addEventListener("change", fn);
      return () => mq.removeEventListener("change", fn);
    },
    () => mq.matches,
  );
}

/** The fixed layout, drawn when no composed tree is usable. */
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
  const phone = useMedia("(max-width: 720px)");
  const [selected, setSelected] = useState("canvas");
  const [tab, setTab] = useState<PhoneTab>("Now");
  const [wiring, setWiring] = useState(false);
  const focus = agent.focus;
  const setFocus = (id: string | null) => agentStore.setFocus(id);

  const room = deriveRoom(feed.state);
  const events = eventsOf(feed.state);
  const latest = events.at(-1);
  const presence: PresenceEntry[] = Array.from({ length: Math.min(room.members, 5) }, (_, i) => ({
    seat: SEATS[i % 5] as 1 | 2 | 3 | 4 | 5,
    label: `Member ${i + 1}`,
    presence: "live" as const,
  }));

  const groups: DeckGroup[] = [
    {
      heading: "This coalition",
      items: [
        { id: "canvas", label: "Canvas", icon: "canvas" },
        { id: "charter", label: "Charter", icon: "shield" },
        { id: "people", label: "People", icon: "people", count: room.members },
        { id: "needs", label: "Needs", icon: "clock", count: room.counts.needs },
        { id: "offers", label: "Offers", icon: "plus", count: room.counts.offers },
        { id: "plans", label: "Plans", icon: "list", count: room.counts.plans },
        { id: "log", label: "Log", icon: "tray", count: room.counts.log },
      ],
    },
    {
      heading: "Yours",
      items: [
        {
          id: "consents",
          label: "Consents",
          icon: "shieldCheck",
          count: agent.requests.length,
          tone: "blue",
        },
      ],
    },
  ];

  const requests: ConsentRequest[] = agent.requests.map((r) => ({
    id: r.id,
    kind: r.kind === "tension_option" ? "tension" : (r.kind as ConsentRequest["kind"]),
    title: r.message,
    deadline: r.expiresAt,
    revision: r.revision,
  }));
  const open = agent.requests.find((r) => r.id === focus) ?? null;

  const canvas = (
    <div className="surface-host">
      {agent.refusal && (
        <Card tone="dashed">
          <span className="small" role="alert">
            The host did not take that answer: {agent.refusal}
          </span>
        </Card>
      )}
      {open && (
        <TrustedRequest request={open} state={feed.state} onAnswer={(a) => void answer(a)} />
      )}
      {selected !== "canvas" ? (
        <EmptyState
          title="Drawn by your agent"
          body="This section is built from the canvas when your agent composes it."
        />
      ) : feed.surfaces.length > 0 ? (
        feed.surfaces.map((s) => <A2uiSurface key={s.id} surface={s.model} />)
      ) : feed.status === "connecting" ? (
        <Skeleton shape="card" label="Loading your view" />
      ) : (
        <FixedView fields={fixedFields(feed.state)} />
      )}
    </div>
  );

  const tray = (
    <ConsentTray
      requests={requests}
      onOpen={(id) => {
        setFocus(id);
        setSelected("canvas");
        setTab("Now");
      }}
    />
  );

  const dock = (
    <AgentDock
      messages={agent.lines.map((l) => ({ id: l.id, from: "agent" as const, text: l.text }))}
      state="idle"
      composerDisabledReason="Typing to your agent is not connected to the host yet."
    />
  );

  if (phone) {
    const people = presence.map((p) => ({ seat: p.seat, label: p.label }));
    return (
      <PhoneShell
        title={room.title}
        stage={room.stage}
        people={people}
        tab={tab}
        onTab={setTab}
        tray={tray}
        onSignOut={signOut}
      >
        {tab === "Agent" ? dock : canvas}
      </PhoneShell>
    );
  }
  return (
    <RoomShell
      title={room.title}
      meta={`${room.members} ${room.members === 1 ? "member" : "members"}`}
      stage={room.stage}
      presence={presence}
      groups={groups}
      selected={selected}
      onSelect={(id) =>
        id === "consents" ? agent.requests[0] && setFocus(agent.requests[0].id) : setSelected(id)
      }
      connection={feed.status === "reconnecting" ? "reconnecting" : "live"}
      tray={tray}
      dock={dock}
      onSignOut={signOut}
      wiringOpen={wiring}
      onToggleWiring={() => setWiring((v) => !v)}
      wiring={
        <WiringDrawer
          state={latest ? "inspecting" : "closed"}
          header={latest ? `#${latest.seq}` : undefined}
          message={latest ? { type: latest.type, payload: latest.payload } : undefined}
          footnote="your projection of this event"
          onClose={() => setWiring(false)}
        />
      }
    >
      {canvas}
    </RoomShell>
  );
}
