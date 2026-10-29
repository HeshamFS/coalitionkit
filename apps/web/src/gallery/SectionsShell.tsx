// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { useMemo, useState } from "react";
import { Banner } from "../components/feedback";
import { Button, Card, Row, Tag } from "../components/primitives";
import { SurfaceBook } from "../feed/surfaces";
import { Deck, type DeckGroup, type PresenceEntry, STAGES, StageBar } from "../shell/bars";
import { AgentDock, type ConsentRequest, ConsentTray, WiringDrawer } from "../shell/dock";
import { PhoneShell, type PhoneTab, RoomShell } from "../shell/RoomShell";
import { Cell, Family, State } from "./Cell";
import { m1, m2, m3, wireMessage } from "./fixtures";

const presence: PresenceEntry[] = [
  { seat: 1, label: "Member 1", presence: "live" },
  { seat: 2, label: "Member 2", presence: "live" },
  { seat: 3, label: "Member 3", presence: "away" },
];
const groups: DeckGroup[] = [
  {
    heading: "This coalition",
    items: [
      { id: "canvas", label: "Canvas", icon: "canvas" },
      { id: "charter", label: "Charter", icon: "shield", count: "r3" },
      { id: "people", label: "People", icon: "people", count: 3 },
      { id: "needs", label: "Needs", icon: "clock", count: 2, tone: "blue" },
      { id: "offers", label: "Offers", icon: "plus", count: 7 },
      { id: "plans", label: "Plans", icon: "list", count: 2 },
      { id: "tasks", label: "Tasks", icon: "check" },
      { id: "log", label: "Log", icon: "tray", count: 42 },
    ],
  },
  {
    heading: "Yours",
    items: [
      { id: "vault", label: "Vault", icon: "lock" },
      { id: "consents", label: "Consents", icon: "shieldCheck", count: 1, tone: "blue" },
    ],
  },
];
const one: ConsentRequest[] = [
  { id: "r1", kind: "plan", title: "Plan A", deadline: "decide by 22:40" },
];
const three: ConsentRequest[] = [
  { id: "r1", kind: "plan", title: "Plan A", deadline: "18 min", urgent: true },
  { id: "r2", kind: "commitment", title: "Your commitment 1", deadline: "today" },
  { id: "r3", kind: "charter", title: "Revision 3 of the charter", deadline: "no deadline" },
];

const canvasBody = (
  <div style={{ position: "relative", height: 330 }}>
    <div className="float card" style={{ left: 0, top: 0, width: 250, boxShadow: "var(--shadow)" }}>
      <div className="head">
        <span className="h-title">Plan A</span>
        <span className="h-right">
          <Tag kind="needs" />
        </span>
      </div>
      <span className="small">Together, 3 seats</span>
    </div>
    <div className="float card card-live" style={{ left: 270, top: 30, width: 230 }}>
      <div className="head">
        <span className="h-title">Step 2</span>
        <span className="h-right">
          <Tag kind="changed" />
        </span>
      </div>
      <span className="small">
        starts <span className="flash">17:00</span>
      </span>
    </div>
    <div
      className="float card card-dashed"
      style={{ left: 0, top: 110, width: 220, background: "transparent" }}
    >
      <span className="small">
        <span
          className="spinner"
          style={{
            color: "var(--blue)",
            width: 10,
            height: 10,
            display: "inline-block",
            verticalAlign: -1,
          }}
        />{" "}
        The planner is weighing a third plan
      </span>
    </div>
  </div>
);

const dockMessages = [
  {
    id: "1",
    from: "agent" as const,
    text: "Two plans passed the steward. A keeps everyone together; B is cheaper.",
  },
  { id: "2", from: "me" as const, text: "Which one is earlier?" },
  { id: "3", from: "tool" as const, text: "vault.answer(q7) -> yes" },
  { id: "4", from: "agent" as const, text: "Both are. A is earlier by a little." },
];

function Phone() {
  const [tab, setTab] = useState<PhoneTab>("Now");
  return (
    <div
      style={{
        height: 420,
        border: "1px solid var(--line-strong)",
        borderRadius: 20,
        overflow: "hidden",
      }}
    >
      <PhoneShell
        title="Room 1"
        stage="Decide"
        people={[m1, m2, m3]}
        tab={tab}
        onTab={setTab}
        height={420}
        tray={undefined}
      >
        <Card tone="ask" title="Decide: Plan A">
          <span className="small">Together, 3 seats</span>
          <Row>
            <Button label="Accept" variant="primary" size="sm" fill />
            <Button label="Not this" size="sm" fill />
          </Row>
        </Card>
        <Card title="Step 2">
          <Tag kind="changed" />
        </Card>
        <Card title="Your offers">
          <span className="small">Offer 1, Offer 2</span>
        </Card>
      </PhoneShell>
    </div>
  );
}

/** A real tree, pushed through the A2UI processor and the registered catalog. */
function CatalogDemo() {
  const book = useMemo(() => {
    const b = new SurfaceBook(() => {});
    b.apply("demo", [
      { version: "v0.9", createSurface: { surfaceId: "demo", catalogId: "coalitionkit/v0_9" } },
      {
        version: "v0.9",
        updateComponents: {
          surfaceId: "demo",
          components: [
            { id: "root", component: "Column", children: ["h", "t", "row"] },
            { id: "h", component: "Heading", text: { path: "/title" }, variant: "h2" },
            {
              id: "t",
              component: "Text",
              text: "Bound by path, drawn by the catalog.",
              tone: "muted",
            },
            { id: "row", component: "Row", children: ["task", "btn"] },
            {
              id: "task",
              component: "TaskCard",
              task_id: "t1",
              title: "Task 1",
              status: "proposed",
              assignee: { seat: "1", label: "Member 1" },
            },
            {
              id: "btn",
              component: "Button",
              label: "Open",
              variant: "primary",
              action: { event: { name: "task.open", context: { task_id: "t1" } } },
            },
          ],
        },
      },
      {
        version: "v0.9",
        updateDataModel: { surfaceId: "demo", path: "/", value: { title: "Surface 1" } },
      },
    ]);
    return b;
  }, []);
  const surfaces = book.list();
  return (
    <>
      {surfaces.map((s) => (
        <A2uiSurface key={s.id} surface={s.model} />
      ))}
    </>
  );
}

export function Shell() {
  return (
    <>
      <Family n="02a" title="RoomShell, the wide door">
        <Cell
          name="RoomShell"
          span={4}
          doors={["wide"]}
          props="coalition · stage · presence · deck[{id,label,count}] · canvas: A2UI root · dock: AgentDock · tray: ConsentTray · WiringDrawer toggle"
          events="deck.select(id) · invite.open · search.open"
        >
          <div style={{ height: 560, display: "flex" }} data-shell="live">
            <RoomShell
              style={{
                height: 560,
                minHeight: 0,
                flex: 1,
                border: "1px solid var(--line-strong)",
                borderRadius: 12,
              }}
              title="Room 1"
              meta="3 people, 4 agents"
              stage="Decide"
              presence={presence}
              me={m1}
              groups={groups}
              selected="canvas"
              tray={<ConsentTray requests={one} />}
              dock={<AgentDock messages={dockMessages} state="idle" />}
            >
              {canvasBody}
            </RoomShell>
          </div>
        </Cell>
        <Cell
          name="RoomShell · reconnecting"
          span={2}
          doors={["wide"]}
          props="state: reconnecting (the dock says so; the last good surface stays)"
        >
          <div style={{ height: 300, display: "flex" }}>
            <RoomShell
              style={{
                height: 300,
                minHeight: 0,
                flex: 1,
                border: "1px solid var(--line-strong)",
                borderRadius: 12,
              }}
              title="Room 1"
              stage="Act"
              presence={presence}
              groups={groups.slice(0, 1)}
              selected="canvas"
              connection="reconnecting"
              dock={<AgentDock messages={dockMessages.slice(0, 2)} state="offline" />}
            >
              {canvasBody}
            </RoomShell>
          </div>
        </Cell>
        <Cell
          name="RoomShell · read-only (watcher)"
          span={2}
          doors={["wide"]}
          props="state: watcher (no dock, no tray, banner says so)"
        >
          <div style={{ height: 300, display: "flex" }}>
            <RoomShell
              style={{
                height: 300,
                minHeight: 0,
                flex: 1,
                border: "1px solid var(--line-strong)",
                borderRadius: 12,
              }}
              title="Room 1"
              stage="Live"
              presence={presence}
              groups={groups.slice(0, 1)}
              selected="canvas"
              connection="watcher"
            >
              {canvasBody}
            </RoomShell>
          </div>
        </Cell>
      </Family>

      <Family n="02b" title="Shell parts">
        <Cell
          name="TopBar · StageBar"
          span={2}
          doors={["wide", "compact", "lens"]}
          props="stages: Germinate | Gather | Negotiate | Decide | Act | Live | Dissolve · current: path · states: done, now, next"
        >
          {STAGES.map((s) => (
            <State key={s} label={`current = ${s}`}>
              <StageBar current={s} />
            </State>
          ))}
        </Cell>
        <Cell
          name="Deck"
          doors={["wide"]}
          props="sections: [{id,label,icon,count,tone}] · selected: id"
          events="deck.select(id)"
        >
          <div style={{ display: "flex", gap: 10 }}>
            <State label="default">
              <div
                style={{
                  width: 188,
                  border: "1px solid var(--line)",
                  borderRadius: 8,
                  overflow: "hidden",
                }}
              >
                <Deck groups={groups} selected="needs" />
              </div>
            </State>
            <State label="collapsed">
              <div
                style={{
                  width: 52,
                  border: "1px solid var(--line)",
                  borderRadius: 8,
                  overflow: "hidden",
                }}
              >
                <Deck groups={groups} selected="needs" collapsed />
              </div>
            </State>
          </div>
        </Cell>
        <Cell
          name="PhoneShell"
          doors={["compact"]}
          props="header: TopBar · stack: cards · tabs: Now | Plans | People | Agent · 44 px targets"
          events="tab.select"
        >
          <Phone />
        </Cell>
        <Cell
          name="ConsentTray"
          span={2}
          doors={["wide", "compact"]}
          props="requests[] {kind: plan | tension | commitment | charter, subject, revision, deadline} · states: empty, pending, urgent"
          events="consent.open(subject)"
        >
          <State label="empty">
            <ConsentTray requests={[]} />
          </State>
          <State label="pending, one">
            <ConsentTray requests={one} onOpen={() => {}} />
          </State>
          <State label="urgent, three">
            <ConsentTray requests={three} onOpen={() => {}} />
          </State>
        </Cell>
        <Cell
          name="AgentDock"
          span={2}
          doors={["wide", "compact"]}
          props="agent: participant · messages: agent session · composer: text | voice · states: idle, streaming, tool-call, offline"
          events="agent.say(text)"
        >
          <div className="g2" style={{ gap: 8 }}>
            {(["idle", "streaming", "tool-call", "offline"] as const).map((s) => (
              <State key={s} label={s}>
                <div
                  style={{
                    height: 300,
                    border: "1px solid var(--line)",
                    borderRadius: 8,
                    overflow: "hidden",
                    display: "flex",
                  }}
                >
                  <AgentDock
                    messages={dockMessages.slice(0, s === "idle" ? 4 : 2)}
                    state={s}
                    composer={s === "idle" ? "text" : "voice"}
                  />
                </div>
              </State>
            ))}
          </div>
        </Cell>
        <Cell
          name="WiringDrawer"
          span={4}
          doors={["wide"]}
          props="event_ref · projection: viewer's own · states: closed, inspecting, verified, broken"
          events="wiring.verify · wiring.copy"
        >
          <div className="g4" style={{ gap: 8 }}>
            {(["closed", "inspecting", "verified", "broken"] as const).map((s) => (
              <State key={s} label={s}>
                {s === "closed" ? (
                  <span className="small">Nothing drawn: the drawer is shut.</span>
                ) : (
                  <WiringDrawer
                    state={s}
                    header="#43 · seq 43"
                    message={wireMessage}
                    footnote="prev_hash 9c1e…a07"
                    onVerify={() => {}}
                    onCopy={() => {}}
                  />
                )}
              </State>
            ))}
          </div>
        </Cell>
      </Family>

      <Family n="A2UI" title="Rendered through the registered catalog" cols={3}>
        <Cell
          name="A2uiSurface (coalitionkit/v0_9)"
          span={2}
          props="createSurface · updateComponents · updateDataModel → MessageProcessor → React"
          events="task.open(task_id)"
        >
          <CatalogDemo />
        </Cell>
        <Cell
          name="Fixed fallback layout"
          props="a missing or invalid tree is replaced by Card { title: Standard view, fields: /fields }"
        >
          <Card title="Standard view">
            <dl className="kv">
              <dt>Coalition</dt>
              <dd>Room 1</dd>
              <dt>Stage</dt>
              <dd>Decide</dd>
              <dt>Members</dt>
              <dd>3</dd>
            </dl>
          </Card>
          <Banner
            tone="ask"
            title="This view is the standard layout."
            body="The composed one could not be drawn."
          />
        </Cell>
      </Family>
    </>
  );
}
