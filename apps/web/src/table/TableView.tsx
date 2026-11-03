// SPDX-License-Identifier: Apache-2.0
// The Table, from data it is handed: the room, the viewer state, the open requests and the ways
// to talk to the host. The live screen (Table.tsx) hands it the real ones; the gallery hands it a
// scripted room and local stand-ins, so what you see there is this same screen.
import { useEffect, useRef, useState } from "react";
import type { ConsentAcknowledgement } from "../components/f08/ConsentSeal";
import type { Answer } from "../feed/actions";
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import { derivePlans, visibleRequests } from "../feed/derive";
import { sheetFor } from "../room/consentSheet";
import { SignedNotice } from "../room/signed";
import type { RoomIo } from "./api";
import { Band } from "./Band";
import { TableContext, type TableCtx } from "./context";
import { COMPACT, WIDE } from "./geometry";
import { rememberResults } from "./keep";
import { PlanCards } from "./PlanCards";
import { layoutClass } from "./phase";
import { Moments, Say } from "./Rail";
import { ResultDialog, type Shown, shownFor } from "./ResultDialog";
import type { Room } from "./room";
import { Side } from "./Side";
import { Stage } from "./Stage";
import { Tray, trayVisible } from "./Tray";
import "./table.css";
import "./stage.css";
import "./beams.css";
import "./plans.css";
import "./side.css";
import "./tray.css";
import "../styles/room.css";

export type TableViewProps = {
  room: Room;
  state: ViewerState | null;
  requests: OpenRequest[];
  focus: string | null;
  setFocus: (id: string | null) => void;
  answer: (a: Answer) => Promise<ConsentAcknowledgement | undefined>;
  io: RoomIo;
  phone: boolean;
  owner: boolean;
  status: "connecting" | "live" | "reconnecting";
  refusal?: string | null;
  onSignOut?: () => void;
};

type Signed = { question: string; seq: number; signature: string };

function Panes({
  phone,
  waiting,
  side,
  table,
}: {
  phone: boolean;
  waiting: boolean;
  side: React.ReactNode;
  table: React.ReactNode;
}) {
  const track = useRef<HTMLDivElement>(null);
  const [at, setAt] = useState(0);
  if (!phone) {
    return (
      <div className="tb-grid">
        {table}
        {side}
      </div>
    );
  }
  const go = (i: number) => {
    const el = track.current;
    if (!el) return;
    el.scrollTo?.({ left: i * el.clientWidth, behavior: "smooth" });
    setAt(i);
  };
  return (
    <>
      <fieldset className="tb-switch">
        <legend className="tb-sr">Which part to show</legend>
        <button type="button" aria-pressed={at === 0} onClick={() => go(0)}>
          Your side{waiting && at !== 0 ? <i role="img" aria-label="waiting for your yes" /> : null}
        </button>
        <button type="button" aria-pressed={at === 1} onClick={() => go(1)}>
          The table
        </button>
      </fieldset>
      <div
        className="tb-panes"
        ref={track}
        onScroll={(e) => {
          const el = e.currentTarget;
          setAt(Math.round(el.scrollLeft / Math.max(1, el.clientWidth)));
        }}
      >
        <div className="tb-pane">{side}</div>
        <div className="tb-pane">{table}</div>
      </div>
    </>
  );
}

export function TableView(props: TableViewProps) {
  const { room, state, requests, answer, phone, status } = props;
  const [viewing, setViewing] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [opened, setOpened] = useState<string | null>(null);
  const [signed, setSigned] = useState<Signed>();
  const asks = visibleRequests(state, requests);
  const plans = derivePlans(state);
  const looking = room.seats.find((s) => s.seat === viewing) ?? null;
  const shown: Shown | null = (() => {
    const r = room.results.find((x) => x.id === opened);
    return r ? shownFor(room, state, r) : null;
  })();

  // What the agents made outlives the room: keep it in this tab for the closing screen.
  const resultsKey = JSON.stringify(room.results.map((r) => [r.id, r.replaced_by]));
  // biome-ignore lint/correctness/useExhaustiveDependencies: the key stands for the results
  useEffect(() => {
    rememberResults(room.results.map((r) => shownFor(room, state, r)));
  }, [resultsKey]);
  useEffect(() => {
    if (room.phase !== "decide") setPicked(null);
  }, [room.phase]);

  const record = async (a: Answer) => {
    const ack = await answer(a);
    const req = requests.find((r) => r.id === a.interrupt_id);
    if (ack && a.consent) {
      setSigned({ question: req ? sheetFor(req, state).question : "Your yes", ...ack });
    }
    return ack;
  };
  const ctx: TableCtx = {
    room,
    state,
    requests,
    asks,
    focus: props.focus,
    setFocus: props.setFocus,
    answer: record,
    io: props.io,
    phone,
    owner: props.owner,
    viewing,
    openResult: setOpened,
  };
  const pick = (id: string) => setPicked(id);
  const cards = (
    <PlanCards
      plans={plans}
      room={room}
      selected={picked}
      signed={new Set()}
      onPick={pick}
      placement="stage"
    />
  );
  const stage = (
    <Stage
      room={room}
      layout={phone ? COMPACT : WIDE}
      viewing={viewing}
      onSeat={(seat) => {
        const s = room.seats.find((x) => x.seat === seat);
        setViewing(s && !s.you && viewing !== seat ? seat : null);
      }}
      plans={cards}
      plansCount={plans.length}
      tray={trayVisible(room) ? <Tray room={room} onOpen={setOpened} /> : null}
    />
  );
  return (
    <TableContext.Provider value={ctx}>
      <div className={`tb ${layoutClass(phone)}`} data-lights={room.lights}>
        <Band room={room} state={state} onSignOut={props.onSignOut} />
        {status === "reconnecting" && (
          <p className="tb-conn" role="status">
            The connection to the host dropped. This is the last state it sent; it updates when the
            host is back.
          </p>
        )}
        {props.refusal && (
          <p className="tb-conn" role="alert" data-bad="true">
            The host did not take that answer: {props.refusal}
          </p>
        )}
        <Panes
          phone={phone}
          waiting={asks.length > 0}
          side={
            <div className="tb-sidecol">
              {signed && (
                <SignedNotice
                  question={signed.question}
                  seq={signed.seq}
                  signature={signed.signature}
                  onClose={() => setSigned(undefined)}
                />
              )}
              <Side
                looking={looking}
                onBack={() => setViewing(null)}
                plans={plans}
                selected={picked}
                onPick={pick}
              />
            </div>
          }
          table={stage}
        />
        <footer className="tb-rail">
          <Moments />
          <Say />
        </footer>
        {shown && <ResultDialog shown={shown} onClose={() => setOpened(null)} />}
      </div>
    </TableContext.Provider>
  );
}
